# Arquitectura e Integración

## Contexto

Este MCP implementa el modelo **Co-Living** de la "Arquitectura Plataforma de Automatización v0.1", donde:

- **Temporal** = Orquestador único (Orchestration Plane)
- **Airflow** = Confinado al Execution Plane durante transición
- **Migración gradual** sin "big bang"

## Modelo de Co-Living

### Estado Actual (Legacy)
```
Frontend → Backend → Airflow API → DAG
```
**Problemas:**
- Airflow como orquestador
- Sin durabilidad de estado
- Difícil observabilidad

### Estado de Transición (Co-Living)
```
Frontend → Control Plane → Temporal → Airflow Adapter → DAG
```
**Beneficios:**
- Temporal como orquestador único
- Estado durable en Cassandra
- Idempotencia con execution_id
- Airflow solo ejecutor

### Estado Objetivo (Native)
```
Frontend → Control Plane → Temporal → Native Activities
```
**Resultado:**
- 100% Temporal
- Airflow deprecado
- Máxima durabilidad

## Integración con Planos Arquitectónicos

### 1. Software Delivery Plane

El MCP genera código que se integra en repositorios:

```
platform-automation/
├── subgroup-network/
│   ├── workflows/
│   │   └── router_config/
│   │       ├── workflows.py      ← Generado por MCP
│   │       ├── activities.py     ← Generado por MCP
│   │       └── run_worker.py     ← Generado por MCP
│   ├── sdk/
│   │   └── network_sdk/          ← Activities centralizadas
│   └── workers/
│       └── network-worker/
```

### 2. Control Plane

**Frontend**: Formularios dinámicos (Form.io) siguen igual

**Backend**: Cambia de disparar Airflow a iniciar Workflow:

```python
# Antes
airflow_client.trigger_dag(dag_id, conf)

# Después
temporal_client.start_workflow(
    RouterConfigWorkflow,
    args=request_data,
    id=execution_id,  # Idempotencia
    task_queue=f"{tenant}-router-config"
)
```

### 3. Orchestration Plane

Workflow generado se ejecuta en Temporal:

```python
@workflow.defn
class RouterConfigWorkflow:
    @workflow.run
    async def run(self, request: dict) -> dict:
        # Fase Wrapper: Ejecuta DAG en Airflow
        result = await workflow.execute_activity(
            "trigger_airflow_dag",
            {"dag_id": "router_config", "conf": request},
            start_to_close_timeout=timedelta(minutes=30)
        )
        return result
```

**Características:**
- Estado en Cassandra multi-región
- Durabilidad ante fallas
- Reintentos automáticos

### 4. Execution Plane

Worker registra Activities:

```python
worker = Worker(
    client,
    task_queue="network-team-router-config",
    workflows=[RouterConfigWorkflow],
    activities=[
        trigger_airflow_dag,      # Adapter (transición)
        deploy_router,            # SDK centralizado
        configure_firewall,       # SDK centralizado
    ]
)
```

**Co-Living:**
- `trigger_airflow_dag`: Adapter temporal
- Activities centralizadas: Del SDK
- Activities personalizadas: Del subgrupo

### 5. Administration Plane

Observabilidad integrada:

```python
from opentelemetry import trace

@activity.defn
async def deploy_router(params: dict) -> str:
    with tracer.start_as_current_span("deploy_router"):
        # Lógica
        ...
```

## Flujo Completo de Migración

### 1. Análisis del DAG

```
Usuario en Kiro: "Analiza este DAG"
[Adjunta router_config.py]

MCP:
  - Parsea con AST
  - Identifica tasks y dependencias
  - Busca Activities centralizadas
  - Genera recomendación

Resultado:
{
  "tasks": 4,
  "centralized": 3,
  "recommendation": "Fase HYBRID"
}
```

### 2. Generación de Código

```
Usuario: "Genera código en fase wrapper"

MCP:
  - Genera workflows.py
  - Genera activities.py (imports + adapter)
  - Genera run_worker.py
  - Genera README.md

Resultado: 4 archivos listos para usar
```

### 3. Integración en Repositorio

```bash
mkdir -p subgroup-network/workflows/router_config
cd subgroup-network/workflows/router_config

# Copiar archivos generados
# workflows.py, activities.py, run_worker.py

git add .
git commit -m "feat: migrate router_config (wrapper phase)"
git push
```

### 4. CI/CD Pipeline

```yaml
# .gitlab-ci.yml
stages:
  - validate
  - build
  - deploy

validate:
  script:
    - pytest tests/
    - mypy workflows.py

build:
  script:
    - docker build -t network-worker:${CI_COMMIT_SHA} .

deploy:
  script:
    - kubectl apply -f k8s/worker-deployment.yaml
```

### 5. Despliegue del Worker

```yaml
# k8s/worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: network-worker
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: worker
        image: network-worker:latest
        env:
        - name: TEMPORAL_ADDRESS
          value: "temporal.svc:7233"
        - name: TASK_QUEUE
          value: "network-team-router-config"
```

### 6. Actualización del Control Plane

```python
# control_plane/catalog_service.py
AUTOMATION_CATALOG = {
    "router_configuration": {
        "type": "temporal_workflow",
        "workflow_class": "RouterConfigWorkflow",
        "task_queue": "network-team-router-config",
        "migration_phase": "wrapper",
        "legacy_dag_id": "router_config"
    }
}
```

### 7. Ejecución desde Frontend

```javascript
// Frontend
async function executeAutomation(formData) {
  const response = await fetch('/api/v1/automations/execute', {
    method: 'POST',
    body: JSON.stringify({
      automation_id: 'router_configuration',
      execution_id: generateIdempotencyKey(),
      params: formData
    })
  });
  return response.json();
}
```

```python
# Backend
@app.post("/api/v1/automations/execute")
async def execute_automation(request: ExecutionRequest):
    automation = AUTOMATION_CATALOG[request.automation_id]
    
    result = await temporal_client.start_workflow(
        automation["workflow_class"],
        args=request.params,
        id=request.execution_id,
        task_queue=automation["task_queue"]
    )
    
    return {"execution_id": request.execution_id, "status": "started"}
```

## Evolución de Fases

### Wrapper → Hybrid

```
Usuario: "Migra el task deploy_router a Activity nativa"

MCP actualiza activities.py:
  from platform_sdk.infrastructure import deploy_router

Workflow actualizado:
  result = await workflow.execute_activity(
      "deploy_router",  # Ya no va a Airflow
      {"router_id": "...", "router_ip": "..."}
  )
```

### Hybrid → Native

```
Usuario: "Genera versión nativa completa"

MCP:
  - Todas las Activities son nativas
  - Sin dependencia de Airflow
  - DAG puede ser deprecado
```

## Beneficios Arquitectónicos

### Separación de Responsabilidades

| Componente | Antes | Después |
|------------|-------|---------|
| Frontend | Captura datos | ✅ Captura datos |
| Control Plane | ❌ No existe | ✅ Gobierno y validación |
| Orchestration | ❌ Airflow | ✅ Temporal |
| Execution | ✅ Airflow | ✅ Workers |

### Durabilidad y Resiliencia

**Antes:**
- Estado en DB de Airflow
- Fallas requieren reinicio manual

**Después:**
- Estado en Cassandra multi-región
- Recuperación automática
- Idempotencia garantizada

### Observabilidad

**Antes:**
- Logs dispersos
- Métricas limitadas

**Después:**
- OpenTelemetry integrado
- Trazas end-to-end
- Métricas estandarizadas

### Multi-tenancy

**Antes:**
- Aislamiento débil

**Después:**
- Namespaces por tenant
- Task Queues dedicadas
- Límites de recursos

## Principios Implementados

| Principio | Implementación |
|-----------|----------------|
| **Durabilidad** | Workflows con estado persistente |
| **Desacoplamiento** | Separación Workflow ↔ Activities |
| **Platform vs User** | Activities centralizadas vs personalizadas |
| **Multi-tenancy** | Namespaces y Task Queues |
| **Extensibilidad** | Reglas configurables |
| **Observabilidad** | OpenTelemetry integrado |

## Conclusión

El MCP Server materializa los principios arquitectónicos definidos en el documento de arquitectura, facilitando:

1. **Migración gradual** sin "big bang"
2. **Aplicación automática** de estándares
3. **Reducción de riesgo** mediante co-living
4. **Velocidad de adopción** de Temporal

Esta herramienta es clave para la transición hacia un modelo más robusto, escalable y observable.
