"""
DAG simple para probar failover de MariaDB + MaxScale.
"""
from datetime import datetime, timedelta
import socket

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.operators.bash import BashOperator


def simple_db_test(**context):
    """Test simple de conexión a la DB usando subprocess."""
    import subprocess
    try:
        # Usar mysql client desde el sistema
        result = subprocess.run([
            'mysql', 
            '-h', 'maxscale-hornos', 
            '-P', '4006',
            '-u', 'airflow',
            '-pairflow_pass',
            '-e', 'SELECT 1 as test, @@hostname as db_host, NOW() as timestamp;'
        ], capture_output=True, text=True, timeout=10)
        
        hostname = socket.gethostname()
        if result.returncode == 0:
            print(f"[DB-TEST] SUCCESS from worker {hostname}")
            print(f"[DB-TEST] Query output: {result.stdout}")
            return {
                "status": "success", 
                "worker_host": hostname, 
                "output": result.stdout.strip()
            }
        else:
            print(f"[DB-TEST] ERROR from worker {hostname}: {result.stderr}")
            return {"status": "error", "worker_host": hostname, "error": result.stderr}
        
    except Exception as e:
        hostname = socket.gethostname()
        print(f"[DB-TEST] ERROR from worker {hostname}: {e}")
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

    # Test de DB via MaxScale usando mysql client
    db_task = PythonOperator(
        task_id="test_database",
        python_callable=simple_db_test,
    )

    # Test de conectividad con curl
    maxscale_test = BashOperator(
        task_id="test_maxscale_api",
        bash_command='''
        echo "[MAXSCALE-TEST] Testing APIs from $(hostname)"
        echo "=== MaxScale Hornos ==="
        curl -s http://maxscale-hornos:8989/v1/servers | head -20 || echo "ERROR: Cannot reach MaxScale Hornos"
        echo "=== MaxScale San Lorenzo ==="
        curl -s http://maxscale-sanlorenzo:8990/v1/servers | head -20 || echo "ERROR: Cannot reach MaxScale San Lorenzo"
        ''',
    )

    # Comando bash con info del sistema
    bash_task = BashOperator(
        task_id="system_info",
        bash_command='''
        echo "[SYSTEM] Worker: $(hostname) | Date: $(date)"
        echo "[NETWORK] MaxScale Hornos IP: $(nslookup maxscale-hornos | grep Address | tail -1 | cut -d: -f2)"
        echo "[NETWORK] MaxScale San Lorenzo IP: $(nslookup maxscale-sanlorenzo | grep Address | tail -1 | cut -d: -f2)"
        ''',
    )

    # Ejecutar en paralelo para probar distribución de workers
    [host_task, db_task, maxscale_test, bash_task]