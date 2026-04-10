# Workflow Despertar TR - Migración de Airflow a Temporal

## Descripción

Migración del DAG `chogar_despertar_tr` de Airflow a Temporal. Este workflow reinicia agentes TR en equipos que no están reportando información, excluyendo casos por reproceso y escribiendo logs en BigQuery y MongoDB.

## Arquitectura

### Componentes

1. **Activities** (`despertar_tr_activities.py`)
   - `nombrar_csv_activity`: Genera nombre de archivo CSV con numeración incremental
   - `obtener_equipos_bigquery_activity`: Consulta equipos desde BigQuery
   - `verificar_reproceso_mongodb_activity`: Verifica si el equipo ya fue procesado
   - `reiniciar_tr_haas_activity`: Reinicia el agente TR mediante HaaS
   - `verificar_status_haas_activity`: Verifica status del equipo
   - `escribir_log_csv_activity`: Escribe logs en CSV
   - `cargar_logs_mongodb_activity`: Carga logs a MongoDB
   - `cargar_logs_bigquery_activity`: Carga logs a BigQuery
   - `enviar_email_activity`: Envía email con resultados

2. **Workflow** (`despertar_tr_workflow.py`)
   - `DespertarTRWorkflow`: Orquesta todas las activities
   - Procesa equipos en paralelo con control de concurrencia
   - Maneja reintentos y errores
   - Genera resumen de ejecución

3. **Worker** (`despertar_tr_worker.py`)
   - Registra el workflow y todas las activities
   - Configura concurrencia y políticas de ejecución
   - Se conecta al clúster de Temporal

4. **Ejecutor** (`ejecutar_despertar_tr.py`)
   - Script para iniciar el workflow desde el Control Plane
   - Funciones para consultar estado y cancelar workflows

## Flujo de Ejecución

```
1. Nombrar archivo CSV
   ↓
2. Obtener equipos desde BigQuery
   ↓
3. Procesar equipos en paralelo (lotes de 10)
   │
   ├─→ Para cada equipo:
   │   ├─ Verificar reproceso en MongoDB
   │   ├─ Si no procesado: Reiniciar TR via HaaS
   │   ├─ Si falla: Verificar status
   │   └─ Escribir log en CSV
   ↓
4. Enviar email con resultados
   ↓
5. Cargar logs a MongoDB
   ↓
6. Cargar logs a BigQuery
```

## Configuración

### Variables de Entorno

```bash
TEMPORAL_HOST=localhost:7233
TEMPORAL_NAMESPACE=default
```

### Configuración del Workflow

```python
config = {
    'path': '/io/cel_chogar/per/confiabilidad/despertar_tr',
    'project_id': 'teco-dev-cdh-e926',
    'dataset_id': 'scripts_tambo',
    'table_id': 'despertar_tr',
    'mongo_uri': 'mongodb://localhost:27017',
    'mongo_database': 'chogar_prod',
    'mongo_collection': 'logs_despertar_tr',
    'destinatarios_email': ['yairfernandez@teco.com.ar'],
    'max_workers': 10,
    'max_results': 1000
}
```

## Instalación

### Dependencias

```bash
pip install temporalio pandas pymongo google-cloud-bigquery pytz
```

### Dependencias adicionales (del proyecto original)

```bash
# Librería HaaS de Chogar
pip install cel_chogar
```

## Uso

### 1. Iniciar el Worker

```bash
python despertar_tr_worker.py
```

El worker quedará escuchando en la task queue `despertar-tr-queue`.

### 2. Ejecutar el Workflow

```bash
python ejecutar_despertar_tr.py
```

### 3. Consultar Estado de un Workflow

```python
from ejecutar_despertar_tr import consultar_estado_workflow
import asyncio

asyncio.run(consultar_estado_workflow('despertar-tr-20240827-105000'))
```

### 4. Cancelar un Workflow

```python
from ejecutar_despertar_tr import cancelar_workflow
import asyncio

asyncio.run(cancelar_workflow('despertar-tr-20240827-105000'))
```

## Ejecución Programada (Cron)

Para ejecutar el workflow de forma programada (equivalente al `schedule_interval` de Airflow):

```python
handle = await client.start_workflow(
    'DespertarTRWorkflow',
    config,
    id='despertar-tr-scheduled',
    task_queue='despertar-tr-queue',
    cron_schedule='50 * * * *'  # Cada hora en el minuto 50
)
```

## Ventajas sobre Airflow

1. **Durabilidad**: El estado del workflow se persiste automáticamente
2. **Reintentos**: Políticas de retry configurables por activity
3. **Concurrencia**: Control fino de paralelismo (max_workers)
4. **Visibilidad**: Trazabilidad completa en Temporal UI
5. **Cancelación**: Cancelación limpia con compensación
6. **Idempotencia**: Workflow ID único previene duplicados
7. **Multi-región**: Soporte nativo para alta disponibilidad

## Diferencias con el DAG Original

| Aspecto | Airflow | Temporal |
|---------|---------|----------|
| Paralelismo | ThreadPoolExecutor | asyncio.gather con lotes |
| Estado | XCom | Variables de workflow |
| Reintentos | Configuración global | RetryPolicy por activity |
| Logs | Archivos + BigQuery | Temporal + BigQuery |
| Cancelación | Manual | API nativa |
| Visibilidad | Airflow UI | Temporal UI + Elasticsearch |

## Integración con Control Plane

El Control Plane puede iniciar este workflow mediante:

```python
# API REST del Control Plane
POST /api/v1/executions
{
    "automation_id": "despertar_tr",
    "tipo": "native_temporal",
    "workflow_name": "DespertarTRWorkflow",
    "config": { ... }
}
```

El backend del Control Plane:
1. Valida autenticación y autorización
2. Genera execution_id único
3. Inicia el workflow en Temporal
4. Retorna execution_id al usuario
5. Usuario puede consultar estado vía API

## Monitoreo

- **Temporal UI**: http://localhost:8080
- **Métricas**: Prometheus + Grafana
- **Logs**: Elasticsearch (indexados por Temporal)
- **Alertas**: Configurar en base a estados de workflow

## Troubleshooting

### Worker no se conecta a Temporal

```bash
# Verificar que Temporal esté corriendo
docker ps | grep temporal

# Verificar conectividad
telnet localhost 7233
```

### Activities fallan por timeout

Ajustar `start_to_close_timeout` en el workflow:

```python
await workflow.execute_activity(
    activity_name,
    start_to_close_timeout=timedelta(minutes=10)  # Aumentar timeout
)
```

### Error de importación de HaaS

Verificar que la librería esté instalada:

```bash
pip show cel_chogar
```

## Próximos Pasos

1. Implementar SDK público para reutilización
2. Agregar métricas personalizadas
3. Configurar alertas en Grafana
4. Implementar compensación en caso de cancelación
5. Agregar tests unitarios y de integración
