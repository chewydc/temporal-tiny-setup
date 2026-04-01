"""
DAG simple para probar failover de MariaDB + MaxScale.
"""
from datetime import datetime, timedelta
import socket
import mysql.connector

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.operators.bash import BashOperator
from airflow.hooks.base import BaseHook


def simple_db_test(**context):
    """Test simple de conexión a la DB usando MaxScale."""
    try:
        # Conectar directamente a MaxScale
        connection = mysql.connector.connect(
            host='maxscale-hornos',
            port=4006,
            user='airflow',
            password='airflow_pass',
            database='airflow'
        )
        
        cursor = connection.cursor()
        cursor.execute("SELECT 1 as test, @@hostname as db_host, NOW() as timestamp")
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        hostname = socket.gethostname()
        print(f"[DB-TEST] SUCCESS from worker {hostname}")
        print(f"[DB-TEST] Connected to DB host: {result[1]}")
        print(f"[DB-TEST] Query result: {result[0]}, Timestamp: {result[2]}")
        
        return {
            "status": "success", 
            "worker_host": hostname, 
            "db_host": result[1],
            "test_result": result[0],
            "timestamp": str(result[2])
        }
        
    except Exception as e:
        hostname = socket.gethostname()
        print(f"[DB-TEST] ERROR from worker {hostname}: {e}")
        return {"status": "error", "worker_host": hostname, "error": str(e)}


def maxscale_status_test(**context):
    """Test de estado de MaxScale via API."""
    try:
        import requests
        
        # Probar ambos MaxScale
        results = {}
        
        for name, port in [("hornos", 8989), ("sanlorenzo", 8990)]:
            try:
                response = requests.get(f"http://maxscale-{name}:{port}/v1/servers", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    servers = [(s["id"], s["attributes"]["state"]) for s in data["data"]]
                    results[name] = {"status": "success", "servers": servers}
                    print(f"[MAXSCALE-{name.upper()}] SUCCESS: {servers}")
                else:
                    results[name] = {"status": "error", "error": f"HTTP {response.status_code}"}
                    print(f"[MAXSCALE-{name.upper()}] ERROR: HTTP {response.status_code}")
            except Exception as e:
                results[name] = {"status": "error", "error": str(e)}
                print(f"[MAXSCALE-{name.upper()}] ERROR: {e}")
        
        hostname = socket.gethostname()
        return {"worker_host": hostname, "maxscale_results": results}
        
    except Exception as e:
        hostname = socket.gethostname()
        print(f"[MAXSCALE-TEST] ERROR from worker {hostname}: {e}")
        return {"status": "error", "worker_host": hostname, "error": str(e)}


def simple_host_check(**context):
    """Verifica el host que ejecuta la tarea."""
    hostname = socket.gethostname()
    task_id = context["task_instance"].task_id
    print(f"[HOST-TEST] Task {task_id} running on worker {hostname}")
    return {"worker_host": hostname, "task": task_id}


with DAG(
    dag_id="ha_validation_env",
    description="Validacion del entorno HA con MaxScale",
    schedule=None,  # Solo ejecución manual
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["ha", "test", "maxscale", "mariadb"],
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

    # Test de DB via MaxScale
    db_task = PythonOperator(
        task_id="test_database",
        python_callable=simple_db_test,
    )

    # Test de MaxScale API
    maxscale_task = PythonOperator(
        task_id="test_maxscale_api",
        python_callable=maxscale_status_test,
    )

    # Comando bash con info del sistema
    bash_task = BashOperator(
        task_id="system_info",
        bash_command='echo "[SYSTEM] Worker: $(hostname) | Date: $(date) | MaxScale Hornos: $(nslookup maxscale-hornos | grep Address | tail -1)"',
    )

    # Ejecutar en paralelo para probar distribución de workers
    [host_task, db_task, maxscale_task, bash_task]