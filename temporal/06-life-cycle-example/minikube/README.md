# Temporal Lifecycle Demo en Minikube

## 🎯 Objetivo

Demostrar el **lifecycle completo** de workflows y workers en Temporal usando Kubernetes, incluyendo:

- ✅ **Replay automático** cuando workers se reinician
- ✅ **Coexistencia de versiones** durante rollouts
- ✅ **Workflows vivos** que sobreviven a cambios de código
- ✅ **Activities retry** con diferentes workers
- ✅ **Pods muriendo** sin afectar workflows
- ✅ **Upgrades reales** sin downtime

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                    Minikube                             │
│                                                         │
│  ┌─────────────────┐  ┌─────────────────┐             │
│  │ Namespace:      │  │ Namespace:      │             │
│  │ temporal        │  │ workers         │             │
│  │                 │  │                 │             │
│  │ ├─ Postgres     │  │ ├─ Workers v1   │             │
│  │ ├─ Temporal (1)  │  │ └─ Workers v2   │             │
│  │ └─ Web UI       │  │                 │             │
│  └─────────────────┘  └─────────────────┘             │
│                                                         │
│  ┌─────────────────┐                                   │
│  │ Namespace:      │                                   │
│  │ infra           │                                   │
│  │                 │                                   │
│  │ └─ Registry     │                                   │
│  └─────────────────┘                                   │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Setup paso a paso

#### Paso 1: Iniciar Minikube
```powershell
minikube start --memory=8192 --cpus=4 --driver=docker
```

#### Paso 2: Crear namespaces
```powershell
kubectl apply -f k8s/00-namespaces.yaml
```

#### Paso 3: Desplegar PostgreSQL
```powershell
kubectl apply -f k8s/01-postgres.yaml
```

#### Paso 4: Esperar PostgreSQL
```powershell
kubectl wait --for=condition=ready pod -l app=postgres -n temporal --timeout=300s
```

#### Paso 5: Desplegar Temporal Server simple
```powershell
kubectl apply -f k8s/02-temporal-server-simple.yaml
```

#### Paso 6: Esperar Temporal Server
```powershell
kubectl wait --for=condition=ready pod -l app=temporal-server -n temporal --timeout=300s
```

#### Paso 7: Desplegar Web UI
```powershell
kubectl apply -f k8s/03-temporal-web.yaml
```

#### Paso 8: Verificar deployment
```powershell
kubectl get pods --all-namespaces
```

### Build y Deploy Workers

#### Paso 9: Configurar Docker para Minikube
```powershell
minikube docker-env | Invoke-Expression
```

#### Paso 10: Build worker image
```powershell
docker build -t lifecycle-worker:v1.0.0 --build-arg VERSION=v1.0.0 .
```

#### Paso 11: Deploy workers
```powershell
kubectl apply -f k8s/04-workers-v1.yaml
```

#### Paso 12: Verificar workers
```powershell
kubectl get pods -n workers
```

### Acceder a Temporal Web UI

```powershell
# Port-forward de la Web UI (mantener ventana abierta)
kubectl port-forward service/temporal-web 8080:8080 -n temporal

# Abrir en navegador: http://localhost:8080
```

**Nota:** El cliente Python se ejecuta DESDE DENTRO del cluster (no desde Windows) porque Temporal Server solo escucha en su IP interna del pod.

## 🎬 Demo: Coexistencia de Versiones v1 y v2

### Paso 1: Abrir Web UI
```powershell
# En una ventana, hacer port-forward de la Web UI
kubectl port-forward service/temporal-web 8080:8080 -n temporal

# Abrir en navegador: http://localhost:8080
```

### Paso 2: Ejecutar workflow desde dentro del cluster
```powershell
# Copiar el cliente al pod worker
kubectl get pods -n workers  # Obtener nombre del pod
kubectl cp client_k8s.py workers/NOMBRE_POD:/tmp/client_k8s.py

# Ejecutar workflow de 5 minutos
kubectl exec -it -n workers NOMBRE_POD -- python /tmp/client_k8s.py lifecycle
```

### Paso 3: Mientras el workflow corre, desplegar v2
```powershell
# Build versión 2
minikube docker-env | Invoke-Expression
docker build -t lifecycle-worker:v2.0.0 --build-arg VERSION=v2.0.0 .

# Deploy v2
kubectl apply -f k8s/05-workers-v2.yaml
kubectl scale deployment lifecycle-workers-v2 -n workers --replicas=1

# Verificar coexistencia
kubectl get pods -n workers
# Deberías ver: v1 (2 pods) y v2 (1 pod) corriendo juntos
```

### Paso 4: Observar la distribución de activities
```powershell
# Ventana 1: Logs de v1
kubectl logs -f deployment/lifecycle-workers-v1 -n workers

# Ventana 2: Logs de v2
kubectl logs -f deployment/lifecycle-workers-v2 -n workers

# Verás que las activities se distribuyen entre v1 y v2
```

### Paso 5: Ver resultado en Web UI
- Ve a http://localhost:8080
- Busca tu workflow (lifecycle-demo-...)
- En la pestaña "History" verás qué versión ejecutó cada activity
- Al finalizar, el resultado mostrará:
  ```json
  {
    "worker_versions_used": ["v1.0.0", "v2.0.0", "v1.0.0", "v2.0.0"],
    "version_changes_detected": true,
    "rollout_detected": true
  }
  ```

## 🔍 Qué Puedes Observar

### 1. **Replay Real**
- Mata un pod worker durante ejecución
- Workflow continúa automáticamente en otro pod
- Estado se mantiene intacto

### 2. **Rollout Sin Downtime**
- Workers v1 y v2 corriendo simultáneamente
- Nuevas activities van a cualquier versión disponible
- Workflows en curso no se interrumpen

### 3. **Versionado de Código**
- Cada worker reporta su versión
- Puedes ver qué versión ejecutó cada activity
- Coexistencia transparente

### 4. **Activities Retry**
- Simula fallos en activities
- Retry automático en diferentes workers
- Políticas de retry configurables

## 📁 Estructura del Proyecto

```
minikube/
├── workflows/
│   └── lifecycle_workflows.py     # Workflows de demo
├── activities/
│   └── lifecycle_activities.py    # Activities con versionado
├── worker/
│   └── lifecycle_worker.py        # Worker principal
├── k8s/
│   ├── 00-namespaces.yaml        # Namespaces
│   ├── 01-postgres.yaml          # Base de datos
│   ├── 02-temporal-server.yaml   # Cluster Temporal (no usado)
│   ├── 03-temporal-web.yaml      # Web UI
│   ├── 04-workers-v1.yaml        # Workers v1
│   └── 05-workers-v2.yaml        # Workers v2
├── ci/
│   └── build.ps1                 # Build y deploy (PowerShell)
├── client.py                     # Cliente para ejecutar workflows
├── Dockerfile                    # Worker container
├── requirements.txt              # Dependencias
└── README.md                     # Esta guía
```

## 🧪 Experimentos Adicionales

### Experimento 1: Worker Resilience
```powershell
# Mientras un workflow corre, matar un pod worker
kubectl delete pod NOMBRE_POD -n workers

# El workflow continúa automáticamente en otro pod
kubectl logs -f deployment/lifecycle-workers-v1 -n workers
```

### Experimento 2: Escalar workers
```powershell
# Escalar v1 y v2 para más distribución
kubectl scale deployment lifecycle-workers-v1 -n workers --replicas=3
kubectl scale deployment lifecycle-workers-v2 -n workers --replicas=2

# Ver distribución de activities entre 5 workers
kubectl get pods -n workers
```

### Experimento 3: Test rápido (30 segundos)
```powershell
# Para probar rápidamente sin esperar 5 minutos
kubectl exec -it -n workers NOMBRE_POD -- python /tmp/client_k8s.py quick
```

## 🔧 Comandos Útiles

### Monitoreo
```bash
# Ver estado de todos los componentes
kubectl get all --all-namespaces

# Logs de workers
kubectl logs -f deployment/lifecycle-workers-v1 -n workers

# Logs de Temporal Server
kubectl logs -f deployment/temporal-frontend -n temporal
```

### Debugging
```bash
# Conectar a worker pod
kubectl exec -it deployment/lifecycle-workers-v1 -n workers -- /bin/bash

# Port forward Temporal
kubectl port-forward service/temporal-frontend-lb 7233:7233 -n temporal

# Port forward Web UI
kubectl port-forward service/temporal-web 8080:8080 -n temporal
```

### Cleanup
```bash
# Limpiar todo
kubectl delete namespace temporal workers infra

# O reiniciar minikube
minikube delete
```

## 🎯 Conceptos Demostrados

### 1. **Temporal Lifecycle**
- Workflows persisten en DB, no en workers
- Workers son stateless y reemplazables
- Estado se reconstruye automáticamente (replay)

### 2. **Kubernetes Integration**
- Workers como Deployments escalables
- Rolling updates sin interrumpir workflows
- Health checks y auto-restart

### 3. **Version Management**
- Coexistencia de múltiples versiones
- Gradual rollout de nuevas versiones
- Backward compatibility automática

### 4. **Production Patterns**
- Multi-pod Temporal cluster
- Shared database
- Load balancing automático
- Monitoring y observabilidad

## 🔒 Demo: Workflows con Versioning Estricto

### ¿Qué es Worker Versioning?

Temporal permite **bloquear workflows a versiones específicas** de workers usando `build_id` y `use_worker_versioning`. Esto garantiza que:

- ✅ Un workflow se ejecuta SOLO en la versión especificada
- ✅ No hay mezcla de versiones durante la ejecución
- ✅ Control total sobre qué código ejecuta cada workflow
- ✅ Rollbacks seguros a versiones anteriores

### Diferencia con el Demo Anterior

| Característica | Demo Normal | Demo Versionado |
|----------------|-------------|------------------|
| Task Queue | `lifecycle-queue` | `lifecycle-versioned-queue` |
| Distribución | Cualquier worker disponible | Solo workers con build_id específico |
| Coexistencia | v1 y v2 procesan el mismo workflow | v1 y v2 procesan workflows separados |
| Uso | Rollouts graduales | Control estricto de versiones |

### Paso 1: Desplegar Workers Versionados

```powershell
# Build images (si no lo hiciste antes)
minikube docker-env | Invoke-Expression
docker build -t lifecycle-worker:v1.0.0 --build-arg VERSION=v1.0.0 .
docker build -t lifecycle-worker:v2.0.0 --build-arg VERSION=v2.0.0 .

# Deploy workers versionados
kubectl apply -f k8s/06-versioned-workers-v1.yaml
kubectl apply -f k8s/07-versioned-workers-v2.yaml

# Verificar
kubectl get pods -n workers -l app=lifecycle-versioned
```

### Paso 2: Ejecutar Workflow Bloqueado a v1.0.0

```powershell
# Copiar cliente versionado al pod
kubectl get pods -n workers -l version=v1.0.0
kubectl cp client_versioned.py workers/NOMBRE_POD:/tmp/client_versioned.py

# Ejecutar workflow que SOLO corre en v1.0.0
kubectl exec -it -n workers NOMBRE_POD -- python /tmp/client_versioned.py lifecycle v1.0.0
```

### Paso 3: Ejecutar Workflow Bloqueado a v2.0.0

```powershell
# Desde un pod v2
kubectl get pods -n workers -l version=v2.0.0
kubectl exec -it -n workers NOMBRE_POD_V2 -- python /tmp/client_versioned.py lifecycle v2.0.0
```

### Paso 4: Observar la Diferencia

```powershell
# Logs de v1 - solo verás el workflow v1.0.0
kubectl logs -f deployment/lifecycle-versioned-v1 -n workers

# Logs de v2 - solo verás el workflow v2.0.0
kubectl logs -f deployment/lifecycle-versioned-v2 -n workers
```

### Resultado Esperado

- Workflow con `version_id=v1.0.0` → **TODAS** las activities se ejecutan en workers v1
- Workflow con `version_id=v2.0.0` → **TODAS** las activities se ejecutan en workers v2
- No hay mezcla de versiones dentro del mismo workflow

### Casos de Uso

1. **Testing de nuevas versiones**: Ejecuta workflows de prueba en v2 mientras producción sigue en v1
2. **Rollback seguro**: Si v2 falla, workflows nuevos pueden volver a v1 sin afectar workflows en curso
3. **A/B Testing**: Compara comportamiento entre versiones con workflows idénticos
4. **Compliance**: Garantiza que workflows críticos usen versiones certificadas

## 🚀 Próximos Pasos

1. **Ejecutar todos los demos** para entender el lifecycle
2. **Comparar demo normal vs versionado** para ver las diferencias
3. **Modificar código** y ver hot-reload en acción
4. **Simular fallos** para ver resilience
5. **Escalar workers** para ver load balancing
6. **Implementar tus propios workflows** usando este setup

¡Este entorno te da una **experiencia completa** de cómo Temporal funciona en producción con Kubernetes!