"""
DAG de prueba para validar Alta Disponibilidad.
Ejecuta tasks cada 30 segundos para observar comportamiento durante failover.
"""
from datetime import datetime, timedelta
import socket
import os

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator


def report_execution(**context):
    hostname = socket.gethostname()
    task_id = context["task_instance"].task_id
    run_id = context["run_id"]
    print(f"[HA-TEST] task={task_id} | host={hostname} | run={run_id} | ts={datetime.now().isoformat()}")
    return {"host": hostname, "task": task_id}


def check_db_connection(**context):
    from airflow.settings import Session
    session = Session()
    result = session.execute("SELECT 1").fetchone()
    session.close()
    print(f"[HA-TEST] DB connection OK: {result}")
    return "db_ok"


with DAG(
    dag_id="ha_validation_dag",
    description="DAG para validar HA - ejecuta tasks frecuentes para observar failover",
    schedule=None,  # Solo ejecución manual
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["ha", "test", "poc"],
    default_args={
        "retries": 3,
        "retry_delay": timedelta(seconds=5),
    },
) as dag:

    t1 = PythonOperator(
        task_id="report_worker",
        python_callable=report_execution,
    )

    t2 = BashOperator(
        task_id="check_scheduler_host",
        bash_command='echo "[HA-TEST] Scheduler host: $(hostname) | Date: $(date)"',
    )

    t3 = PythonOperator(
        task_id="check_db",
        python_callable=check_db_connection,
    )

    t1 >> t2 >> t3
