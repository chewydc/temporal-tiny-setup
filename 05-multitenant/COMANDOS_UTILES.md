# Comandos Útiles - Temporal Multitenant

## 🚀 Setup Inicial

```bash
# Iniciar Temporal Server
docker-compose up -d

# Verificar que esté corriendo
docker-compose ps

# Ver logs
docker-compose logs -f temporal
```

## 👷 Workers

```bash
# Iniciar workers multitenant
python multitenant_worker.py

# Ver qué task queues está escuchando
# (Se muestra en la salida del worker)
```

## 🎬 Ejecutar Demos

```bash
# Demo simple (1 tenant, 1 deployment)
python simple_demo.py

# Demo completo (3 tenants, 6 deployments)
python multitenant_demo.py
```

## 🔍 Consultar Workflows

```bash
# Listar todos los workflows
temporal workflow list

# Listar workflows de un tenant específico
temporal workflow list --query 'CustomStringField = "chogar"'

# Ver detalles de un workflow
temporal workflow describe --workflow-id chogar-deployment-123456

# Ver historial completo
temporal workflow show --workflow-id chogar-deployment-123456
```

## 📨 Enviar Signals

```bash
# Aprobar un deployment (continuar después de la pausa)
temporal workflow signal --workflow-id chogar-deployment-123456 --name approve_deployment

# Sintaxis general
temporal workflow signal --workflow-id <WORKFLOW_ID> --name <SIGNAL_NAME>
```

## 🔎 Queries

```bash
# Query personalizado (si implementas queries en el workflow)
temporal workflow query --workflow-id chogar-deployment-123456 --name getStatus
```

## ⏹️ Cancelar/Terminar Workflows

```bash
# Cancelar un workflow (graceful)
temporal workflow cancel --workflow-id chogar-deployment-123456

# Terminar un workflow (forzado)
temporal workflow terminate --workflow-id chogar-deployment-123456 --reason "Testing"
```

## 📊 Monitoreo

```bash
# Ver workflows en ejecución
temporal workflow list --query 'ExecutionStatus = "Running"'

# Ver workflows fallidos
temporal workflow list --query 'ExecutionStatus = "Failed"'

# Ver workflows completados
temporal workflow list --query 'ExecutionStatus = "Completed"'

# Filtrar por tenant Y estado
temporal workflow list --query 'CustomStringField = "chogar" AND ExecutionStatus = "Running"'
```

## 🧹 Limpieza

```bash
# Detener Temporal Server
docker-compose down

# Limpiar todo (incluyendo volúmenes)
docker-compose down -v

# Limpiar Docker completamente
docker system prune -f
```

## 🐛 Debugging

```bash
# Ver logs del worker en tiempo real
# (Los workers imprimen en stdout)

# Ver logs de Temporal Server
docker-compose logs -f temporal

# Ver logs de PostgreSQL (si usas)
docker-compose logs -f postgresql

# Verificar conectividad a Temporal
temporal operator cluster health
```

## 📈 Métricas (Avanzado)

```bash
# Si tienes Prometheus configurado
curl http://localhost:9090/metrics

# Ver métricas de workers
# (Requiere configuración adicional de Prometheus)
```

## 🔧 Configuración

```bash
# Ver configuración de Temporal CLI
temporal config get

# Configurar namespace por defecto
temporal config set namespace default

# Configurar dirección del servidor
temporal config set address localhost:7233
```

## 💡 Tips Útiles

### Buscar workflows por patrón de ID
```bash
# Todos los workflows de chogar
temporal workflow list --query 'WorkflowId STARTS_WITH "chogar"'

# Workflows de hoy
temporal workflow list --query 'StartTime > "2024-01-01T00:00:00Z"'
```

### Ejecutar workflow y esperar resultado
```python
# En Python
result = await client.execute_workflow(
    "NetworkDeploymentWorkflow",
    request,
    id=workflow_id,
    task_queue=task_queue
)
# Bloquea hasta que el workflow complete
```

### Ejecutar workflow sin esperar
```python
# En Python
handle = await client.start_workflow(
    "NetworkDeploymentWorkflow",
    request,
    id=workflow_id,
    task_queue=task_queue
)
# Retorna inmediatamente
```

### Obtener resultado después
```python
# En Python
handle = client.get_workflow_handle(workflow_id)
result = await handle.result()
```

## 🌐 Temporal UI

```bash
# Abrir en navegador
start http://localhost:8233

# O manualmente:
# http://localhost:8233
```

### Filtros útiles en UI:
- `CustomStringField = "chogar"` - Workflows de un tenant
- `ExecutionStatus = "Running"` - Workflows en ejecución
- `WorkflowType = "NetworkDeploymentWorkflow"` - Por tipo de workflow

## 🔄 Reiniciar Todo

```bash
# Script completo para reiniciar desde cero
docker-compose down -v
docker-compose up -d
sleep 5
python multitenant_worker.py &
sleep 2
python multitenant_demo.py
```

## 📝 Notas

- Los workflow IDs deben ser únicos globalmente
- Los signals son idempotentes (puedes enviarlos múltiples veces)
- Los workflows pueden ejecutarse por días/meses (durable execution)
- Temporal UI es tu mejor amigo para debugging

## 🆘 Troubleshooting Común

```bash
# Error: "connection refused"
# → Verificar que Temporal esté corriendo
docker-compose ps

# Error: "no workers available"
# → Iniciar workers
python multitenant_worker.py

# Error: "workflow already started"
# → Usar un workflow ID diferente o terminar el existente
temporal workflow terminate --workflow-id <ID>

# Workflows no aparecen en UI
# → Verificar que estés en el namespace correcto (default)
```
