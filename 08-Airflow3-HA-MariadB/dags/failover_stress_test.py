"""
DAG complejo para probar failover de MariaDB + MaxScale.
Incluye tasks que escriben y leen de la DB para validar el comportamiento.
"""
from datetime import datetime, timedelta
import socket
import random
import time

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator


def write_to_db(**context):
    """Escribe datos de prueba en la DB para validar escrituras durante failover."""
    from airflow.settings import Session
    from airflow.models import Connection
    
    hostname = socket.gethostname()
    task_id = context["task_instance"].task_id
    run_id = context["run_id"]
    timestamp = datetime.now().isoformat()
    
    session = Session()
    try:
        # Crear una conexión de prueba (esto escribe en la DB)
        test_conn_id = f"test_conn_{run_id}_{task_id}"
        
        # Verificar si ya existe
        existing = session.query(Connection).filter(Connection.conn_id == test_conn_id).first()
        if not existing:
            conn = Connection(
                conn_id=test_conn_id,
                conn_type="http",
                host=hostname,
                description=f"Test connection from {hostname} at {timestamp}"
            )
            session.add(conn)
            session.commit()
            print(f"[WRITE-TEST] Created connection {test_conn_id} from {hostname}")
        else:
            print(f"[WRITE-TEST] Connection {test_conn_id} already exists")
            
    except Exception as e:
        session.rollback()
        print(f"[WRITE-TEST] ERROR: {e}")
        raise
    finally:
        session.close()
    
    return {"host": hostname, "conn_id": test_conn_id, "timestamp": timestamp}


def read_from_db(**context):
    """Lee datos de la DB para validar lecturas durante failover."""
    from airflow.settings import Session
    from airflow.models import Connection
    
    hostname = socket.gethostname()
    session = Session()
    
    try:
        # Contar conexiones de prueba
        test_connections = session.query(Connection).filter(
            Connection.conn_id.like("test_conn_%")
        ).count()
        
        # Leer algunas conexiones recientes
        recent_connections = session.query(Connection).filter(
            Connection.conn_id.like("test_conn_%")
        ).order_by(Connection.id.desc()).limit(5).all()
        
        conn_info = [{
            "conn_id": conn.conn_id,
            "host": conn.host,
            "description": conn.description
        } for conn in recent_connections]
        
        print(f"[READ-TEST] Found {test_connections} test connections from {hostname}")
        print(f"[READ-TEST] Recent connections: {conn_info}")
        
    except Exception as e:
        print(f"[READ-TEST] ERROR: {e}")
        raise
    finally:
        session.close()
    
    return {"host": hostname, "total_connections": test_connections}


def stress_db(**context):
    """Genera carga en la DB para observar comportamiento durante failover."""
    from airflow.settings import Session
    
    hostname = socket.gethostname()
    session = Session()
    
    try:
        # Ejecutar varias queries para generar carga
        for i in range(10):
            result = session.execute("SELECT COUNT(*) FROM connection").fetchone()
            time.sleep(0.5)  # Pausa entre queries
            print(f"[STRESS-TEST] Query {i+1}/10: {result[0]} connections")
            
    except Exception as e:
        print(f"[STRESS-TEST] ERROR during query {i+1}: {e}")
        # No hacer raise para que el DAG continúe
    finally:
        session.close()
    
    return {"host": hostname, "queries_completed": i+1}


def check_scheduler_distribution(**context):
    """Verifica qué scheduler está procesando las tasks."""
    hostname = socket.gethostname()
    run_id = context["run_id"]
    task_id = context["task_instance"].task_id
    
    # Simular trabajo variable
    work_time = random.uniform(1, 5)
    time.sleep(work_time)
    
    print(f"[SCHEDULER-TEST] Task {task_id} processed by {hostname} (worked {work_time:.2f}s)")
    return {"scheduler_host": hostname, "work_time": work_time}


with DAG(
    dag_id="failover_stress_test",
    description="DAG para probar failover con carga de DB y múltiples schedulers",
    schedule=None,  # Solo ejecución manual
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=2,
    tags=["ha", "failover", "stress", "poc"],
    default_args={
        "retries": 2,
        "retry_delay": timedelta(seconds=10),
    },
) as dag:

    # Tasks paralelas para generar carga
    write_tasks = []
    for i in range(3):
        write_task = PythonOperator(
            task_id=f"write_db_{i+1}",
            python_callable=write_to_db,
        )
        write_tasks.append(write_task)
    
    # Task de lectura que depende de las escrituras
    read_task = PythonOperator(
        task_id="read_db_summary",
        python_callable=read_from_db,
    )
    
    # Task de stress
    stress_task = PythonOperator(
        task_id="stress_db",
        python_callable=stress_db,
    )
    
    # Tasks para verificar distribución de schedulers
    scheduler_tasks = []
    for i in range(4):
        sched_task = PythonOperator(
            task_id=f"check_scheduler_{i+1}",
            python_callable=check_scheduler_distribution,
        )
        scheduler_tasks.append(sched_task)
    
    # Task final de reporte
    report_task = BashOperator(
        task_id="final_report",
        bash_command="""
        echo "[FINAL-REPORT] Failover test completed"
        echo "[FINAL-REPORT] Host: $(hostname)"
        echo "[FINAL-REPORT] Time: $(date)"
        echo "[FINAL-REPORT] All tasks completed successfully"
        """,
    )
    
    # Definir dependencias
    write_tasks >> read_task
    scheduler_tasks >> stress_task
    [read_task, stress_task] >> report_task