# Caso 05: Arquitectura Multitenant con Namespaces

## 🎯 Objetivo

Demostrar cómo implementar una **arquitectura multitenant con aislamiento REAL** usando Namespaces de Temporal, donde múltiples clientes tienen separación completa de datos y cada uno solo ve sus propios workflows.

## 📚 Documentación Completa

👉 **[Ver MULTITENANT.md](./MULTITENANT.md)** para documentación detallada sobre:
- Conceptos de multitenant
- Estrategias de escalabilidad
- Arquitectura implementada
- Roadmap de implementación

## 🏗️ Arquitectura Multitenant con Namespaces

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Tenant A  │     │   Tenant B  │     │   Tenant C  │
│  (chogar)   │     │   (amovil)  │     │   (afijo)   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌────────────────────────────────────────────────────┐
│           Temporal Server (localhost:7233)         │
└────────────────────────────────────────────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Namespace:   │     │ Namespace:   │     │ Namespace:   │
│   chogar     │     │   amovil     │     │   afijo      │
│              │     │              │     │              │
│ Solo ve SUS  │     │ Solo ve SUS  │     │ Solo ve SUS  │
│ workflows    │     │ workflows    │     │ workflows    │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                   │                   │
       └───────────────────┴───────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Worker Pool     │
                  │ (por namespace) │
                  └─────────────────┘
```

## 🔑 Conceptos Clave Implementados

### 1. Namespaces por Tenant
```python
# Cada tenant tiene su NAMESPACE
client = await Client.connect("localhost:7233", namespace="chogar")
```
**Beneficio**: Aislamiento COMPLETO de datos - cada tenant solo ve sus workflows

### 2. Workflow IDs Únicos
```python
workflow_id = f"{tenant_id}-deployment-{router_num}-{timestamp}"
```
**Beneficio**: Evita colisiones entre tenants

### 3. Workers por Namespace
```python
# Worker para namespace chogar
client = await Client.connect("localhost:7233", namespace="chogar")
worker = Worker(client, task_queue="chogar-deployments", ...)
```
**Beneficio**: Procesamiento dedicado por tenant

### 4. Aislamiento Real
```python
# Chogar conecta a su namespace
client_chogar = await Client.connect("localhost:7233", namespace="chogar")
# Solo ve workflows de chogar

# AMovil conecta a su namespace
client_amovil = await Client.connect("localhost:7233", namespace="amovil")
# Solo ve workflows de amovil
```
**Beneficio**: Seguridad y privacidad - ningún tenant ve datos de otros

## 🚀 Guía de Uso Rápida

### Paso 1: Crear Namespaces
```bash
python setup_namespaces.py
```

Esto crea los namespaces: `chogar`, `amovil`, `afijo`

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
   📦 Namespace: chogar
      📋 Task Queue: chogar-deployments
   📦 Namespace: amovil
      📋 Task Queue: amovil-deployments
   📦 Namespace: afijo
      📋 Task Queue: afijo-deployments
```

### Paso 4: Ejecutar Demo Multitenant

En otra terminal:
```bash
python multitenant_demo.py
```

Esto iniciará:
- **2 deployments** para `chogar` (en namespace chogar)
- **1 deployment** para `amovil` (en namespace amovil)
- **3 deployments** para `afijo` (en namespace afijo)

### Paso 5: Monitorear en Temporal UI

Abre: **http://localhost:8233**

**Seleccioná el namespace del tenant** en el dropdown (arriba a la izquierda):
- Namespace `chogar` → Solo ves workflows de chogar
- Namespace `amovil` → Solo ves workflows de amovil
- Namespace `afijo` → Solo ves workflows de afijo

✅ **Aislamiento real**: Cada tenant solo ve SUS workflows

## 📊 Estrategias de Escalabilidad

| Estrategia | Aislamiento | Complejidad | Costo | Cuándo Usar |
|------------|-------------|-------------|-------|-------------|
| **Namespaces** (implementado) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 💰💰 | Producción, aislamiento real |
| **Task Queues** | ⭐⭐⭐ | ⭐ | 💰 | PoC, aislamiento lógico |
| **Workers Dedicados** | ⭐⭐⭐⭐⭐ | ⭐⭐ | 💰💰💰 | Requisitos específicos |

## 📦 Archivos del Proyecto

```
05-multitenant/
├── MULTITENANT.md              # 📚 Documentación completa
├── README.md                   # Este archivo
├── RESUMEN_EJECUTIVO.md        # Para compartir con el equipo
├── INICIO.md                   # Inicio rápido
├── setup_namespaces.py         # ⭐ Crear namespaces
├── models.py                   # Modelos con tenant_id
├── workflows.py                # Workflow multitenant
├── activities.py               # Activities simuladas
├── multitenant_worker.py       # ⭐ Workers por namespace
├── multitenant_demo.py         # ⭐ Demo con 3 tenants
├── simple_demo.py              # Demo simple con 1 tenant
└── docker-compose.yml          # Infraestructura
```

## 🎯 Valor Demostrado

Este caso de uso demuestra:

1. **Aislamiento REAL**: Cada tenant tiene su namespace - no ve datos de otros
2. **Seguridad**: Imposible que un tenant acceda a workflows de otro
3. **Escalabilidad**: Agregar más workers por namespace es trivial
4. **Observabilidad**: UI limpia - cada tenant solo ve lo suyo
5. **Producción-Ready**: Patrón usado en sistemas reales multitenant

## 🔍 Comparación: Task Queues vs Namespaces

### Con Task Queues (Problema)
```python
# Todos en namespace "default"
task_queue = f"tenant-{tenant_id}-deployments"
```

❌ Problemas:
- Todos los tenants ven workflows de todos en Temporal UI
- Necesitás filtros complicados
- No hay aislamiento real de datos
- Riesgo de seguridad

### Con Namespaces (Solución)
```python
# Cada tenant en su namespace
client = await Client.connect("localhost:7233", namespace=tenant_id)
```

✅ Beneficios:
- Cada tenant SOLO ve sus workflows
- No necesitás filtros
- Aislamiento completo de datos
- Seguro por diseño

## 🛠️ Troubleshooting

### Namespaces no existen
```bash
# Ejecutar setup
python setup_namespaces.py
```

### Workers no inician
```bash
# Verificar Temporal Server
temporal operator cluster health

# Verificar namespaces
temporal operator namespace list
```

### Workflows no aparecen
```bash
# Verificar que estés en el namespace correcto en UI
# Dropdown arriba a la izquierda
```

## 📚 Próximos Pasos

1. **Lee la documentación completa**: [MULTITENANT.md](./MULTITENANT.md)
2. **Experimenta con el demo**: Modifica número de tenants y deployments
3. **Implementa rate limiting**: Agrega límites de concurrencia por namespace
4. **Prueba workers dedicados**: Un worker exclusivo por tenant
5. **Explora políticas**: Diferentes configuraciones por namespace

## 🔗 Referencias

- [Documentación Multitenant Completa](./MULTITENANT.md)
- [Temporal Docs - Namespaces](https://docs.temporal.io/namespaces)
- [Multi-tenancy Best Practices](https://docs.temporal.io/kb/multi-tenancy)

---

**💡 Tip**: Namespaces es la forma CORRECTA de hacer multitenant en producción. Task queues son solo para aislamiento de procesamiento, no de datos.
