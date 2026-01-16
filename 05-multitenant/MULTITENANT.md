# Arquitectura Multitenant con Temporal

## 📋 Índice
1. [Conceptos Clave](#conceptos-clave)
2. [Arquitectura Implementada](#arquitectura-implementada)
3. [Componentes](#componentes)
4. [Estrategias de Escalabilidad](#estrategias-de-escalabilidad)
5. [Cómo Ejecutar](#cómo-ejecutar)
6. [Monitoreo y Observabilidad](#monitoreo-y-observabilidad)

---

## 🎯 Conceptos Clave

### ¿Qué es Multitenant?
Una arquitectura donde **múltiples clientes (tenants)** comparten la misma infraestructura pero mantienen **aislamiento lógico** de sus datos y operaciones.

### ¿Por qué Temporal para Multitenant?

| Característica | Beneficio |
|----------------|-----------|
| **Task Queues** | Aislamiento de workloads por tenant |
| **Namespaces** | Separación completa de entornos |
| **Search Attributes** | Filtrado y consultas por tenant |
| **Workflow IDs únicos** | Evita colisiones entre tenants |
| **Rate Limiting** | Control de recursos por tenant |

---

## 🏗️ Arquitectura Implementada

### Diagrama de Flujo

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Tenant A  │     │   Tenant B  │     │   Tenant C  │
│  (chogar)│     │   (amovil)  │     │  (afijo)  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │ Start Workflow    │                   │
       ▼                   ▼                   ▼
┌────────────────────────────────────────────────────┐
│           Temporal Server (localhost:7233)         │
│  ┌──────────────────────────────────────────────┐  │
│  │         Workflow Execution Engine            │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
       │                   │                   │
       │ Task Queue        │                   │
       ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│tenant-acme- │     │tenant-amovil│     │tenant-afijo│
│corp-deploy  │     │-deployments │     │-deployments │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┴───────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Worker Pool     │
                  │ (Shared/Dedicated)│
                  └─────────────────┘
```

### Componentes del Sistema

#### 1. **Modelo de Datos** (`models.py`)
```python
@dataclass
class NetworkDeploymentRequest:
    tenant_id: str  # ← Identificador del tenant
    router_id: str
    router_ip: str
    software_version: str
```

**Decisión de diseño**: `tenant_id` es parte del request para:
- Trazabilidad completa
- Logging contextual
- Routing de tareas

#### 2. **Workflow** (`workflows.py`)
```python
@workflow.defn
class NetworkDeploymentWorkflow:
    """Workflow multitenant con aislamiento por task queue"""
```

**Características multitenant**:
- ✅ Ejecuta en task queue específica del tenant
- ✅ Workflow ID incluye tenant_id
- ✅ Logging con contexto de tenant
- ✅ Retry policies independientes

#### 3. **Workers** (`multitenant_worker.py`)

**Estrategia implementada**: Worker compartido
```python
# Un worker escucha múltiples task queues
for tenant_id in ["chogar", "amovil", "afijo"]:
    task_queue = f"tenant-{tenant_id}-deployments"
    worker = Worker(client, task_queue=task_queue, ...)
```

**Ventajas**:
- ✅ Eficiente en recursos
- ✅ Fácil de escalar horizontalmente
- ✅ Menor overhead operacional

**Desventajas**:
- ⚠️ Menos aislamiento entre tenants
- ⚠️ Un tenant puede afectar performance de otros

---

## 🚀 Estrategias de Escalabilidad

### 1. Task Queues por Tenant (Implementado)

```python
task_queue = f"tenant-{tenant_id}-deployments"
```

**Cuándo usar**: 
- Tenants con workloads similares
- Necesitas aislamiento lógico básico
- Recursos compartidos son aceptables

**Escalabilidad**: ⭐⭐⭐⭐

---

### 2. Namespaces por Tenant (Avanzado)

```python
# Cada tenant tiene su propio namespace
client = await Client.connect(
    "localhost:7233",
    namespace=f"tenant-{tenant_id}"
)
```

**Cuándo usar**:
- Tenants enterprise con SLAs estrictos
- Necesitas aislamiento completo
- Diferentes políticas de retención por tenant

**Escalabilidad**: ⭐⭐⭐⭐⭐

**Trade-off**: Mayor complejidad operacional

---

### 3. Workers Dedicados por Tenant

```python
# Worker exclusivo para un tenant
worker = Worker(
    client,
    task_queue=f"tenant-{tenant_id}-deployments",
    max_concurrent_activities=10  # Control de recursos
)
```

**Cuándo usar**:
- Tenants con requisitos de performance específicos
- Necesitas garantías de recursos
- Compliance requiere aislamiento físico

**Escalabilidad**: ⭐⭐⭐⭐⭐

**Trade-off**: Mayor costo de infraestructura

---

### 4. Rate Limiting por Tenant

```python
# En el workflow
if await self._check_tenant_rate_limit(tenant_id):
    raise Exception(f"Rate limit exceeded for {tenant_id}")
```

**Implementación recomendada**:
- Redis para contadores distribuidos
- Sliding window algorithm
- Límites configurables por tier de tenant

---

## 📦 Componentes del Ejemplo

### Archivos Principales

```
05-example-with-temp-features/
├── models.py                  # Modelos con tenant_id
├── workflows.py               # Workflow multitenant
├── activities.py              # Activities (sin cambios)
├── multitenant_worker.py      # Worker que escucha múltiples queues
├── multitenant_demo.py        # Demo con 3 tenants
└── MULTITENANT.md            # Esta documentación
```

### Flujo de Ejecución

1. **Inicio**: `multitenant_demo.py` inicia workflows para 3 tenants
2. **Routing**: Cada workflow va a su task queue específica
3. **Procesamiento**: Workers procesan tareas de sus queues asignadas
4. **Monitoreo**: Temporal UI muestra workflows filtrados por tenant

---

## 🎮 Cómo Ejecutar

### Paso 1: Iniciar Temporal Server

```bash
cd 05-example-with-temp-features
docker-compose up -d
```

Verifica que esté corriendo:
```bash
docker-compose ps
```

### Paso 2: Iniciar Workers Multitenant

```bash
python multitenant_worker.py
```

Deberías ver:
```
🏢 Tenants configurados: chogar, amovil, afijo
   📋 Task Queue: tenant-chogar-deployments
   📋 Task Queue: tenant-amovil-deployments
   📋 Task Queue: tenant-afijo-deployments
```

### Paso 3: Ejecutar Demo Multitenant

En otra terminal:
```bash
python multitenant_demo.py
```

Esto iniciará:
- 2 deployments para `chogar`
- 1 deployment para `amovil`
- 3 deployments para `afijo`

### Paso 4: Monitorear en Temporal UI

Abre: http://localhost:8233

**Filtrar por tenant**:
```
CustomStringField = "chogar"
```

---

## 📊 Monitoreo y Observabilidad

### Métricas Clave por Tenant

| Métrica | Descripción | Cómo obtenerla |
|---------|-------------|----------------|
| **Workflows activos** | Workflows en ejecución | Temporal UI + filtro |
| **Tasa de éxito** | % workflows completados | Temporal metrics |
| **Latencia p95** | Tiempo de ejecución | Temporal metrics |
| **Rate limit hits** | Veces que se alcanzó el límite | Custom metrics |

### Queries Útiles en Temporal UI

```sql
-- Workflows de un tenant
CustomStringField = "chogar"

-- Workflows fallidos de un tenant
CustomStringField = "chogar" AND ExecutionStatus = "Failed"

-- Workflows en ejecución
CustomStringField = "chogar" AND ExecutionStatus = "Running"
```

### Logging Contextual

Todos los logs incluyen `tenant_id`:
```python
workflow.logger.info(f"🏢 Tenant: {tenant_id} | Router: {request.router_id}")
```

Esto permite:
- Filtrar logs por tenant en tu sistema de logging
- Debugging más rápido
- Auditoría por tenant

---

## 🔐 Consideraciones de Seguridad

### 1. Aislamiento de Datos
- ✅ Cada workflow solo accede a datos de su tenant
- ✅ Workflow IDs incluyen tenant_id para evitar colisiones
- ⚠️ Validar tenant_id en activities

### 2. Rate Limiting
```python
# Implementar en el workflow o en un interceptor
max_concurrent_workflows_per_tenant = 10
```

### 3. Autenticación y Autorización
- Validar que el usuario puede iniciar workflows para ese tenant
- Usar mTLS para comunicación Temporal Client ↔ Server
- Implementar RBAC en tu API gateway

---

## 📈 Roadmap de Implementación

### Fase 1: PoC (Actual) ✅
- [x] Task queues por tenant
- [x] Workflow IDs únicos
- [x] Worker compartido
- [x] Demo con 3 tenants

### Fase 2: Producción Básica
- [ ] Search attributes configurados
- [ ] Rate limiting por tenant
- [ ] Métricas por tenant
- [ ] Alertas por tenant

### Fase 3: Producción Avanzada
- [ ] Namespaces por tenant (enterprise)
- [ ] Workers dedicados (tenants premium)
- [ ] Auto-scaling de workers
- [ ] Multi-región

### Fase 4: Enterprise
- [ ] Tenant provisioning automático
- [ ] Self-service portal
- [ ] Billing por uso
- [ ] SLA monitoring

---

## 🤔 Preguntas Frecuentes

### ¿Cuántos tenants puede manejar esta arquitectura?

**Con task queues**: 100-1000 tenants por cluster
**Con namespaces**: 10-100 namespaces por cluster

**Limitante principal**: Número de workers y recursos del cluster

### ¿Cómo escalo horizontalmente?

```bash
# Iniciar más workers en diferentes máquinas
# Todos escuchan las mismas task queues
python multitenant_worker.py  # Máquina 1
python multitenant_worker.py  # Máquina 2
python multitenant_worker.py  # Máquina 3
```

Temporal distribuye automáticamente el trabajo.

### ¿Qué pasa si un tenant consume muchos recursos?

**Soluciones**:
1. Rate limiting a nivel de workflow
2. Worker dedicado para ese tenant
3. Namespace separado con recursos dedicados

### ¿Cómo migro de task queues a namespaces?

```python
# Antes
task_queue = f"tenant-{tenant_id}-deployments"

# Después
namespace = f"tenant-{tenant_id}"
client = await Client.connect("localhost:7233", namespace=namespace)
```

Requiere:
- Crear namespaces en Temporal
- Actualizar workers
- Migración gradual por tenant

---

## 📚 Referencias

- [Temporal Docs - Namespaces](https://docs.temporal.io/namespaces)
- [Temporal Docs - Task Queues](https://docs.temporal.io/tasks)
- [Temporal Docs - Search Attributes](https://docs.temporal.io/visibility)
- [Multi-tenancy Best Practices](https://docs.temporal.io/kb/multi-tenancy)

---

## 💡 Próximos Pasos Sugeridos

1. **Experimenta con el demo**: Ejecuta `multitenant_demo.py` y observa en Temporal UI
2. **Prueba diferentes cargas**: Modifica el número de deployments por tenant
3. **Implementa rate limiting**: Agrega límites de concurrencia
4. **Configura search attributes**: Para queries más potentes
5. **Mide performance**: Agrega métricas y observa el comportamiento

---

**Autor**: Equipo de Automatización  
**Última actualización**: 2024  
**Versión**: 1.0
