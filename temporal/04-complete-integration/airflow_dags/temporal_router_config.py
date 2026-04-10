from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

default_args = {
    'owner': 'temporal-integration',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'temporal_router_config',
    default_args=default_args,
    description='Configuración de router virtual para conectividad cliente-servidor',
    schedule_interval=None,  # Triggered manually by Temporal
    catchup=False,
    tags=['temporal', 'networking', 'router'],
)

def log_router_config(**context):
    """Log de configuración del router"""
    conf = context['dag_run'].conf
    router_id = conf.get('router_id', 'unknown')
    router_ip = conf.get('router_ip', 'unknown')
    software_version = conf.get('software_version', 'unknown')
    
    print(f"=== AIRFLOW: Configurando Router ===")
    print(f"Router ID: {router_id}")
    print(f"Router IP: {router_ip}")
    print(f"Software Version: {software_version}")
    print("=====================================")
    
    return f"Router {router_id} configuration started"

# Task 1: Log inicial
log_config = PythonOperator(
    task_id='log_router_configuration',
    python_callable=log_router_config,
    dag=dag,
)

# Task 2: Configurar firewall para habilitar HTTP
configure_firewall_http = BashOperator(
    task_id='configure_firewall_http',
    bash_command='''
    echo "=== Configurando firewall para habilitar HTTP ==="
    
    # Obtener router_id del contexto
    ROUTER_ID="{{ dag_run.conf.router_id }}"
    
    # DEMO: Simular tarea larga para poder interrumpir
    echo "🕐 Iniciando configuración lenta para demo..."
    sleep 15  # 15 segundos para poder interrumpir
    
    # Verificar que el router existe
    if docker ps --filter "name=$ROUTER_ID" --format "{{ '{{' }}.Names{{ '}}' }}" | grep -q "$ROUTER_ID"; then
        echo "✅ Router $ROUTER_ID encontrado"
        
        # Mostrar reglas actuales
        echo "🔍 Reglas de firewall ANTES:"
        docker exec $ROUTER_ID iptables -L FORWARD -n
        
        # Eliminar regla que bloquea HTTP (puerto 80)
        echo "🚫 Eliminando regla que bloquea HTTP..."
        docker exec $ROUTER_ID iptables -D FORWARD 2 2>/dev/null || echo "Regla ya eliminada"
        
        # Agregar regla que permite HTTP
        echo "✅ Agregando regla que permite HTTP..."
        docker exec $ROUTER_ID iptables -I FORWARD 2 -p tcp --dport 80 -j ACCEPT
        
        # Mostrar reglas finales
        echo "🔍 Reglas de firewall DESPUÉS:"
        docker exec $ROUTER_ID iptables -L FORWARD -n
        
        echo "✅ Firewall configurado: PING + HTTP permitidos"
    else
        echo "❌ Router $ROUTER_ID no encontrado"
        exit 1
    fi
    ''',
    dag=dag,
)

# Task 3: Validar conectividad
validate_connectivity = BashOperator(
    task_id='validate_connectivity',
    bash_command='''
    echo "=== Validando conectividad ==="
    
    # Test ping desde cliente a servidor
    echo "🏓 Test ping cliente -> servidor..."
    if docker exec test-client ping -c 2 -W 3 192.168.200.10; then
        echo "✅ Ping exitoso"
    else
        echo "❌ Ping falló"
    fi
    
    # Test HTTP desde cliente a servidor
    echo "🌐 Test HTTP cliente -> servidor..."
    if docker exec test-client wget -q -O - http://192.168.200.10 --timeout=5; then
        echo "✅ HTTP exitoso"
    else
        echo "❌ HTTP falló"
    fi
    
    echo "=== Validación completada ==="
    ''',
    dag=dag,
)

def finalize_configuration(**context):
    """Finalizar configuración"""
    conf = context['dag_run'].conf
    router_id = conf.get('router_id', 'unknown')
    
    print(f"=== AIRFLOW: Configuración Finalizada ===")
    print(f"Router {router_id} configurado exitosamente")
    print(f"Conectividad cliente-servidor establecida")
    print("=========================================")
    
    return f"Router {router_id} configuration completed successfully"

# Task 4: Finalizar
finalize_config = PythonOperator(
    task_id='finalize_configuration',
    python_callable=finalize_configuration,
    dag=dag,
)

# Definir dependencias
log_config >> configure_firewall_http >> validate_connectivity >> finalize_config