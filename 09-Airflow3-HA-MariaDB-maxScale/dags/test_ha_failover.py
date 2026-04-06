from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.mysql.operators.mysql import MySqlOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook

default_args = {
    'owner': 'admin',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def test_database_connection():
    """Test database connection and show current server info"""
    hook = MySqlHook(mysql_conn_id='mysql_default')
    
    # Test connection
    connection = hook.get_conn()
    cursor = connection.cursor()
    
    # Get server info
    cursor.execute("SELECT @@hostname, @@server_id, @@read_only")
    result = cursor.fetchone()
    
    print(f"Connected to server: {result[0]}")
    print(f"Server ID: {result[1]}")
    print(f"Read Only: {result[2]}")
    
    # Test write operation
    cursor.execute("CREATE TABLE IF NOT EXISTS test_failover (id INT AUTO_INCREMENT PRIMARY KEY, timestamp DATETIME, message VARCHAR(255))")
    cursor.execute("INSERT INTO test_failover (timestamp, message) VALUES (NOW(), 'Test from Airflow')")
    connection.commit()
    
    # Read back
    cursor.execute("SELECT COUNT(*) FROM test_failover")
    count = cursor.fetchone()[0]
    print(f"Total records in test_failover: {count}")
    
    cursor.close()
    connection.close()

dag = DAG(
    'test_ha_failover',
    default_args=default_args,
    description='Test HA failover functionality',
    schedule_interval=timedelta(minutes=5),
    catchup=False,
    tags=['ha', 'test', 'failover'],
)

# Test database connection
test_connection = PythonOperator(
    task_id='test_database_connection',
    python_callable=test_database_connection,
    dag=dag,
)

# Create test table
create_table = MySqlOperator(
    task_id='create_test_table',
    mysql_conn_id='mysql_default',
    sql="""
    CREATE TABLE IF NOT EXISTS failover_test (
        id INT AUTO_INCREMENT PRIMARY KEY,
        execution_date DATETIME,
        task_id VARCHAR(255),
        status VARCHAR(50),
        server_info VARCHAR(255)
    )
    """,
    dag=dag,
)

# Insert test data
insert_data = MySqlOperator(
    task_id='insert_test_data',
    mysql_conn_id='mysql_default',
    sql="""
    INSERT INTO failover_test (execution_date, task_id, status, server_info) 
    VALUES (NOW(), 'insert_test_data', 'success', @@hostname)
    """,
    dag=dag,
)

test_connection >> create_table >> insert_data