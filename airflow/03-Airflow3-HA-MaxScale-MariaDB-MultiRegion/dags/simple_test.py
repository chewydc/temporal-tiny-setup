"""
DAG simple para probar conectividad y funcionamiento básico.
Sin dependencias complejas, solo operaciones básicas.
"""
from datetime import datetime, timedelta
import logging
import socket

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

logger = logging.getLogger(__name__)


def test_basic_connectivity(**context):
    """Test básico de conectividad y variables."""
    hostname = socket.gethostname()
    timestamp = datetime.now().isoformat()
    
    print(f"=== BASIC CONNECTIVITY TEST ===")
    print(f"Hostname: {hostname}")
    print(f"Timestamp: {timestamp}")
    print(f"Task ID: {context['task_instance'].task_id}")
    print(f"DAG ID: {context['dag'].dag_id}")
    print(f"Execution Date: {context['ds']}")
    
    return {
        "hostname": hostname,
        "timestamp": timestamp,
        "status": "success"
    }


def test_db_simple(**context):
    """Test simple de base de datos usando Airflow Variables."""
    from airflow.models import Variable
    
    hostname = socket.gethostname()
    test_key = f"simple_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    test_value = f"test_from_{hostname}"
    
    try:
        # Escribir variable
        Variable.set(test_key, test_value)
        print(f"✓ Variable written: {test_key} = {test_value}")
        
        # Leer variable
        read_value = Variable.get(test_key)
        print(f"✓ Variable read: {test_key} = {read_value}")
        
        # Verificar
        assert read_value == test_value, f"Mismatch: {read_value} != {test_value}"
        print(f"✓ DB test successful from {hostname}")
        
        return {
            "hostname": hostname,
            "test_key": test_key,
            "test_value": test_value,
            "status": "success"
        }
        
    except Exception as e:
        print(f"✗ DB test failed: {e}")
        raise


with DAG(
    dag_id="simple_test",
    description="DAG simple para probar funcionamiento básico",
    schedule=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["test", "simple", "connectivity"],
    default_args={
        "retries": 1,
        "retry_delay": timedelta(seconds=10),
    },
) as dag:

    # Test básico sin dependencias externas
    basic_test = PythonOperator(
        task_id="basic_connectivity_test",
        python_callable=test_basic_connectivity,
    )
    
    # Test de sistema
    system_test = BashOperator(
        task_id="system_info_test",
        bash_command="""
        echo "=== SYSTEM INFO ==="
        echo "Hostname: $(hostname)"
        echo "Date: $(date)"
        echo "Python version: $(python --version)"
        echo "Disk space: $(df -h /tmp | tail -1)"
        echo "Memory: $(free -h | grep Mem)"
        echo "=== END SYSTEM INFO ==="
        """,
    )
    
    # Test de DB simple
    db_test = PythonOperator(
        task_id="db_simple_test",
        python_callable=test_db_simple,
    )
    
    # Secuencia
    basic_test >> system_test >> db_test