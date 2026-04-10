# Migración chogar_despertar_tr

## Información de Migración

- **DAG Original**: `chogar_despertar_tr`
- **Fase de Migración**: `hybrid`
- **Tenant**: `chogar`
- **Namespace**: `default`
- **Fecha de Migración**: Auto-generado por MCP

## Descripción

DAG Automatización Despertar TR

Trae equipos desde BigQuery que no están reportando información TR y reinicia el agente interno de CM. Excluye los casos por reproceso y escribe logs en BigQuery.

## Tasks Migrados

- `nombrar_csv` (PythonOperator) → Activity personalizada
- `tr_implementacion_task` (PythonOperator) → Activity personalizada (debe descomponerse)
- `tr_correo_finalizacion` (PythonOperator) → Activity personalizada
- `load_csv_to_db` (PythonOperator) → Activity personalizada (debe descomponerse)

## Activities Centralizadas del SDK Detectadas

El MCP detectó que este workflow puede usar las siguientes Activities centralizadas:

- `bigquery_get_data` - Para consultar datos de BigQuery
- `bigquery_execute_query` - Para ejecutar queries en BigQuery
- `mongodb_find` - Para buscar documentos en MongoDB
- `mongodb_insert_many` - Para insertar documentos en MongoDB
- `send_email` - Para enviar correos electrónicos

## Ejecución

### Iniciar Worker

```bash
python run_worker.py
```

### Ejecutar Workflow

```python
from temporalio.client import Client
from workflows import ChogarDespertarTrWorkflow

async def main():
    client = await Client.connect("localhost:7233", namespace="default")
    
    result = await client.execute_workflow(
        ChogarDespertarTrWorkflow.run,
        {},
        id="chogar-despertar-tr-001",
        task_queue="chogar-despertar-tr"
    )
    
    print(result)
```

## Fase de Migración: hybrid

### Estado Actual

El código generado está en fase HYBRID con Activities personalizadas que contienen la lógica original del DAG. 

### Próximos Pasos para Optimización

1. **Descomponer `tr_implementacion_task`** en Activities atómicas:
   - `bigquery_get_data` (SDK) - Obtener equipos desde BigQuery
   - `mongodb_find` (SDK) - Verificar equipos procesados
   - `haas_reset_tr` (custom) - Reiniciar agente TR
   - `haas_status` (custom) - Verificar status
   - `write_csv_log` (custom) - Escribir log

2. **Descomponer `load_csv_to_db`** en Activities del SDK:
   - `mongodb_insert_many` (SDK) - Cargar logs a MongoDB
   - `bigquery_execute_query` (SDK) - Cargar logs a BigQuery

3. **Reemplazar envío de email** con Activity centralizada:
   - Usar `send_email` del SDK en lugar de lógica custom

4. **Implementar manejo de estado**:
   - Reemplazar XCom de Airflow con variables de Workflow de Temporal
   - Pasar `nombre_archivo` entre Activities como parámetros

5. **Validar y testear** cada Activity independientemente

6. **Avanzar a fase native** una vez que todas las Activities estén optimizadas

## Arquitectura Propuesta

Ver `workflow_redesign.md` para el diseño detallado de cómo debe descomponerse este workflow en Activities atómicas y reutilizables.

## Notas Importantes

- Las Activities centralizadas del SDK están comentadas en `run_worker.py` hasta que el SDK esté disponible
- El código actual es funcional pero no está optimizado
- La descomposición en Activities atómicas mejorará la observabilidad, testabilidad y reutilización
