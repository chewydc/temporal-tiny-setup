"""
Ejemplo de DAG de Airflow para migración

Este DAG configura un router de red usando Ansible y Airflow.
Es similar al ejemplo del repositorio temporal-tiny-setup/04-complete-integration
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

default_args = {
    'owner': 'network-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'router_configuration',
    default_args=default_args,
    description='Configura router virtual para conectividad cliente-servidor',
    schedule_interval=None,
    catchup=False,
    tags=['network', 'router', 'automation'],
)

def log_router_config(**context):
    """Log de configuración del router"""
    conf = context['dag_run'].conf
    router_id = conf.get('router_id', 'unknown')
    print(f"=== Configurando Router: {router_id} ===")
    return f"Router {router_id} configuration started"

# Task 1: Log inicial
log_config = PythonOperator(
    task_id='log_router_configuration',
    python_callable=log_router_config,
    dag=dag,
)

# Task 2: Desplegar router con Ansible
deploy_router = BashOperator(
    task_id='deploy_router',
    bash_command='''
    echo "Deploying router with Ansible..."
    ansible-playbook deploy_router.yml -i inventory.ini
    ''',
    dag=dag,
)

# Task 3: Configurar firewall
configure_firewall = BashOperator(
    task_id='configure_firewall',
    bash_command='''
    echo "Configuring firewall rules..."
    iptables -A FORWARD -p tcp --dport 80 -j ACCEPT
    iptables -A FORWARD -p icmp -j ACCEPT
    ''',
    dag=dag,
)

# Task 4: Validar conectividad
validate_connectivity = BashOperator(
    task_id='validate_connectivity',
    bash_command='''
    echo "Validating connectivity..."
    ping -c 2 192.168.200.10
    wget -q -O - http://192.168.200.10
    ''',
    dag=dag,
)

# Definir dependencias
log_config >> deploy_router >> configure_firewall >> validate_connectivity
