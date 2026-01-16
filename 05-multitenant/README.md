# Caso 05: Arquitectura Multitenant con Temporal

## 🎯 Objetivo

Demostrar cómo implementar una **arquitectura multitenant escalable** usando Temporal, donde múltiples clientes (tenants) comparten infraestructura pero mantienen aislamiento lógico de sus operaciones.

## 📚 Documentación Completa

👉 **[Ver MULTITENANT.md](./MULTITENANT.md)** para documentación detallada sobre:
- Conceptos de multitenant
- Estrategias de escalabilidad
- Arquitectura implementada
- Roadmap de implementación

## 🏗️ Arquitectura Multitenant

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Tenant A  │     │   Tenant B  │     │   Tenant C  │
│  (chogar)   │     │   (amovil)  │     │   (afijo)   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │ Start Workflow    │                   │
       ▼                   ▼                   ▼
┌────────────────────────────────────────────────────┐
│           Temporal Server (localhost:7233)         │
└────────────────────────────────────────────────────┘
       │                   │                   │
       │ Task Queue        │                   │
       ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│tenant-chogar│     │tenant-amovil│     │tenant-afijo │
│-deployments │     │-deployments │     │-deployments │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┴───────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Worker Pool     │
                  │ (Shared)        │
                  └─────────────────┘
```

## 🔑 Conceptos Clave Implementados

### 1. Task Queues por Tenant
```python
task_queue = f"tenant-{tenant_id}-deployments"
```
**Beneficio**: Aislamiento lógico de workloads

### 2. Workflow IDs Únicos
```python
workflow_id = f"{tenant_id}-deployment-{router_num}-{timestamp}"
```
**Beneficio**: Evita colisiones entre tenants

### 3. Search Attributes
```python
search_attributes={"CustomStringField": [tenant_id]}
```
**Beneficio**: Filtrado por tenant en Temporal UI

### 4. Workers Compartidos
```python
# Un worker escucha múltiples task queues
for tenant_id in ["chogar", "amovil", "afijo"]:
    worker = Worker(client, task_queue=f"tenant-{tenant_id}-deployments", ...)
```
**Beneficio**: Eficiente en recursos, fácil de escalar

## 🚀 Guía de Uso Rápida

### Paso 1: Iniciar Temporal Server
```bash
docker-compose up -d
```

### Paso 2: Instalar Dependencias
```bash
python -m venv env
.\env\Scripts\activate
pip install -r requirements.txt
```

### Paso 3: Iniciar Workers Multitenant
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

### Paso 4: Ejecutar Demo Multitenant

En otra terminal:
```bash
python multitenant_demo.py
```

Esto iniciará:
- **2 deployments** para `chogar`
- **1 deployment** para `amovil`
- **3 deployments** para `afijo`

### Paso 5: Monitorear en Temporal UI

Abre: **http://localhost:8233**

Filtra workflows por tenant:
```
CustomStringField = "chogar"
```

## 📊 Estrategias de Escalabilidad

| Estrategia | Aislamiento | Complejidad | Costo | Cuándo Usar |
|------------|-------------|-------------|-------|-------------|
| **Task Queues** (implementado) | ⭐⭐⭐ | ⭐ | 💰 | 100-1000 tenants, workloads similares |
| **Namespaces** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 💰💰 | Tenants enterprise, SLAs estrictos |
| **Workers Dedicados** | ⭐⭐⭐⭐⭐ | ⭐⭐ | 💰💰💰 | Requisitos específicos de performance |

## 📦 Archivos del Proyecto

```
05-example-with-temp-features/
├── MULTITENANT.md              # 📚 Documentación completa
├── README.md                   # Este archivo
├── models.py                   # Modelos con tenant_id
├── workflows.py                # Workflow multitenant
├── activities.py               # Activities (sin cambios)
├── multitenant_worker.py       # ⭐ Worker que escucha múltiples queues
├── multitenant_demo.py         # ⭐ Demo con 3 tenants
├── run_worker.py               # Worker original (legacy)
├── run_deployment.py           # Deployment original (legacy)
└── docker-compose.yml          # Infraestructura
```

## 🎯 Valor Demostrado

Este caso de uso demuestra:

1. **Aislamiento Lógico**: Cada tenant tiene su task queue dedicada
2. **Escalabilidad Horizontal**: Agregar más workers es trivial
3. **Observabilidad**: Filtrado por tenant en Temporal UI
4. **Eficiencia**: Workers compartidos optimizan recursos
5. **Producción-Ready**: Patrones usados en sistemas reales

## 🔍 Comparación: Single-Tenant vs Multitenant

### Antes (Single-Tenant)
```python
# Un solo task queue para todos
task_queue = "deployments"
workflow_id = f"deployment-{timestamp}"
```

❌ Problemas:
- Colisiones de workflow IDs
- No se puede filtrar por cliente
- Difícil aplicar rate limiting
- No hay aislamiento

### Después (Multitenant)
```python
# Task queue por tenant
task_queue = f"tenant-{tenant_id}-deployments"
workflow_id = f"{tenant_id}-deployment-{timestamp}"
search_attributes = {"CustomStringField": [tenant_id]}
```

✅ Beneficios:
- IDs únicos garantizados
- Filtrado por tenant
- Rate limiting por tenant
- Aislamiento lógico

## 🛠️ Troubleshooting

### Workers no inician
```bash
# Verificar Temporal Server
docker-compose ps

# Reiniciar
docker-compose restart
```

### Workflows no aparecen en UI
```bash
# Verificar que workers estén corriendo
python multitenant_worker.py

# Verificar logs
```

### Filtros no funcionan en UI
```bash
# Search attributes requieren configuración en Temporal
# Por ahora, busca por workflow ID que incluye tenant_id
```

## 📚 Próximos Pasos

1. **Lee la documentación completa**: [MULTITENANT.md](./MULTITENANT.md)
2. **Experimenta con el demo**: Modifica número de tenants y deployments
3. **Implementa rate limiting**: Agrega límites de concurrencia
4. **Prueba workers dedicados**: Un worker por tenant
5. **Explora namespaces**: Para aislamiento completo

## 🔗 Referencias

- [Documentación Multitenant Completa](./MULTITENANT.md)
- [Temporal Docs - Task Queues](https://docs.temporal.io/tasks)
- [Temporal Docs - Namespaces](https://docs.temporal.io/namespaces)
- [Multi-tenancy Best Practices](https://docs.temporal.io/kb/multi-tenancy)

---

**💡 Tip**: Este ejemplo es un punto de partida. En producción, considera:
- Rate limiting por tenant
- Métricas y alertas por tenant
- Auto-scaling de workers
- Namespaces para tenants enterprise
