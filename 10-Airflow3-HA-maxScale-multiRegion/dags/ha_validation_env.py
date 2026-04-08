"""
DAG simple para probar failover de MariaDB + MaxScale.
"""
from datetime import datetime, timedelta
import socket

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator


def simple_db_test(**context):
    """Test simple de conexión a la DB."""
    try:
        from airflow.settings import Session
        session = Session()
        result = session.execute("SELECT 1 as test").fetchone()
        session.close()
        
        hostname = socket.gethostname()
        print(f"[DB-TEST] SUCCESS from {hostname}: {result}")
        return {"status": "success", "host": hostname, "result": str(result)}
        
    except Exception as e:
        print(f"[DB-TEST] ERROR: {e}")
        return {"status": "error", "error": str(e)}


def simple_host_check(**context):
    """Verifica el host que ejecuta la tarea."""
    hostname = socket.gethostname()
    task_id = context["task_instance"].task_id
    print(f"[HOST-TEST] Task {task_id} running on {hostname}")
    return {"host": hostname, "task": task_id}


with DAG(
    dag_id="ha_validation_env",
    description="Validacion del entorno HA",
    schedule=None,  # Solo ejecución manual
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["ha", "test", "smoke"],
    default_args={
        "retries": 1,
        "retry_delay": timedelta(seconds=5),
    },
) as dag:

    # Test de host
    host_task = PythonOperator(
        task_id="check_host",
        python_callable=simple_host_check,
    )

    # Test de DB
    db_task = PythonOperator(
        task_id="test_database",
        python_callable=simple_db_test,
    )

    # Comando bash simple
    bash_task = BashOperator(
        task_id="system_info",
        bash_command='echo "[SYSTEM] Host: $(hostname) | Date: $(date)"',
    )

    # Ejecutar en paralelo (sin dependencias)
    [host_task, db_task, bash_task]