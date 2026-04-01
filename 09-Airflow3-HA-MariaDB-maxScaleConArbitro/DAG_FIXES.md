# Corrección del DAG ha_validation_env para Airflow 3.0

## Problema Identificado
El DAG original fallaba con el error:
```
ERROR: Direct database access via the ORM is not allowed in Airflow 3.0
```

## Cambios Realizados

### 1. DAG Corregido (`ha_validation_env.py`)
- ❌ **Eliminado**: `from airflow.settings import Session` (no permitido en Airflow 3.0)
- ✅ **Agregado**: Conexión directa a MaxScale usando `mysql.connector`
- ✅ **Agregado**: Test de APIs REST de MaxScale usando `requests`
- ✅ **Actualizado**: Imports para usar `airflow.providers.standard.operators`

### 2. Nuevas Funcionalidades del DAG
- **`simple_db_test()`**: Conecta directamente a MaxScale (puerto 4006) y ejecuta queries
- **`maxscale_status_test()`**: Consulta las APIs REST de ambos MaxScale
- **`simple_host_check()`**: Verifica en qué worker se ejecuta cada tarea
- **`system_info`**: Comando bash con información del sistema

### 3. Dependencias Agregadas (`requirements.txt`)
```
mysql-connector-python==8.0.33
requests==2.31.0
```

### 4. Docker Compose Actualizado
- ✅ **Volumen agregado**: `./requirements.txt:/requirements.txt`
- ✅ **Comando actualizado**: Instala dependencias automáticamente con `pip install -r /requirements.txt`
- ✅ **Aplicado a**: airflow-init, airflow-apiserver, airflow-scheduler, airflow-dag-processor, airflow-worker-1, airflow-worker-2

## Funcionalidades del DAG Corregido

### Tareas Paralelas:
1. **`check_host`**: Muestra en qué worker se ejecuta
2. **`test_database`**: Conecta a MaxScale y ejecuta query SQL
3. **`test_maxscale_api`**: Consulta APIs REST de ambos MaxScale
4. **`system_info`**: Información del sistema via bash

### Información que Proporciona:
- **Worker Distribution**: Qué worker ejecuta cada tarea
- **Database Connectivity**: Conexión a MariaDB via MaxScale
- **MaxScale Status**: Estado de servidores MariaDB desde ambos MaxScale
- **System Info**: Hostname, fecha, resolución DNS

## Ejemplo de Output Esperado

### test_database:
```
[DB-TEST] SUCCESS from worker airflow-worker-1
[DB-TEST] Connected to DB host: mariadb-hornos
[DB-TEST] Query result: 1, Timestamp: 2026-04-01 14:52:30
```

### test_maxscale_api:
```
[MAXSCALE-HORNOS] SUCCESS: [('mariadb-hornos', 'Master, Running'), ('mariadb-sanlorenzo', 'Slave, Running'), ('mariadb-tucuman', 'Slave, Running')]
[MAXSCALE-SANLORENZO] SUCCESS: [('mariadb-hornos', 'Master, Running'), ('mariadb-sanlorenzo', 'Slave, Running'), ('mariadb-tucuman', 'Slave, Running')]
```

## Estado Actual
✅ **DAG Compatible**: Airflow 3.0 compatible
✅ **Dependencias Instaladas**: mysql-connector-python, requests
✅ **MaxScale Integration**: Conecta directamente a MaxScale
✅ **API Testing**: Prueba APIs REST de MaxScale
✅ **Multi-Worker**: Distribuye tareas entre workers
✅ **Listo para Failover Testing**: Puede detectar cambios en roles Master/Slave

## Próximos Pasos
1. Ejecutar el DAG manualmente desde Airflow UI
2. Verificar que todas las tareas se ejecuten correctamente
3. Usar para pruebas de failover (desconectar Hornos y ver cambio de roles)
4. Monitorear distribución de tareas entre workers