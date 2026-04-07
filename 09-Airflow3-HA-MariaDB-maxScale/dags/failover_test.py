"""
DAG para probar failover en vivo.
Ejecuta tasks de 30 seg cada una, escribiendo y leyendo de la DB continuamente.
Mientras corre, matar mariadb-primary y verificar que completa sin errores.
"""
from datetime import datetime, timedelta
import logging
import socket
import time

from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)


def _db_op_with_retry(func, max_retries=5, delay=5):
    """Ejecuta una operación de DB con reintentos para sobrevivir failover."""
    log = logging.getLogger("airflow.task")
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            log.warning(f"[RETRY {attempt+1}/{max_retries}] {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
    raise Exception(f"Failed after {max_retries} retries")


def db_continuous_write(task_num, **context):
    """Escribe en la DB cada 5 segundos durante 30 seg."""
    from airflow.models import Variable
    hostname = socket.gethostname()

    for i in range(6):
        ts = datetime.now().isoformat()
        key = f"ft_{task_num}_{i}"
        _db_op_with_retry(lambda k=key, v=f"{hostname}|{ts}": Variable.set(k, v))
        print(f"[WRITE {i+1}/6] {key} = {hostname} @ {ts}")
        time.sleep(5)

    return {"host": hostname, "writes": 6}


def db_continuous_read(task_num, **context):
    """Lee de la DB cada 5 segundos durante 30 seg."""
    from airflow.models import Variable
    hostname = socket.gethostname()

    for i in range(6):
        val = _db_op_with_retry(lambda idx=i: Variable.get(f"ft_1_{idx}", default_var="NOT_FOUND"))
        print(f"[READ {i+1}/6] ft_1_{i} = {val} (from {hostname})")
        time.sleep(5)

    return {"host": hostname, "reads": 6}


def final_validation(**context):
    """Valida que todos los datos escritos sean legibles."""
    from airflow.models import Variable
    hostname = socket.gethostname()
    found = 0

    for t in range(1, 4):
        for i in range(6):
            key = f"ft_{t}_{i}"
            val = _db_op_with_retry(lambda k=key: Variable.get(k, default_var=None))
            if val:
                found += 1
                print(f"  OK {key} = {val}")
            else:
                print(f"  MISS {key}")

    print(f"[VALIDATION] {found}/18 variables encontradas desde {hostname}")
    assert found == 18, f"Expected 18 variables, found {found}"
    return {"total": found, "host": hostname}


with DAG(
    dag_id="failover_test",
    description="DAG largo para probar failover en vivo - 2 min de duracion",
    schedule=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["ha", "failover", "live"],
    default_args={
        "retries": 3,
        "retry_delay": timedelta(seconds=15),
    },
) as dag:

    writers = []
    for n in range(1, 4):
        t = PythonOperator(
            task_id=f"write_phase_{n}",
            python_callable=db_continuous_write,
            op_kwargs={"task_num": n},
        )
        writers.append(t)

    readers = []
    for n in range(1, 3):
        t = PythonOperator(
            task_id=f"read_phase_{n}",
            python_callable=db_continuous_read,
            op_kwargs={"task_num": n},
        )
        readers.append(t)

    validate = PythonOperator(
        task_id="final_validation",
        python_callable=final_validation,
    )

    for w in writers:
        for r in readers:
            w >> r
    for r in readers:
        r >> validate
