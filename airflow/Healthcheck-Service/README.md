# Healthcheck Service + Site Controller

## Evolución del diseño

Este componente evolucionó en tres etapas:

1. **Healthcheck simple** — Evaluaba salud de Airflow, exponía endpoint para HAProxy
2. **Healthcheck + Site Controller (un servicio)** — Agregó control del scheduler basado en DB primary
3. **Dos microservicios separados (actual)** — Separación de concerns para producción

La separación en dos servicios responde a necesidades reales de producción:
- Ciclos de vida independientes (actualizar uno sin tocar el otro)
- El healthcheck es **stateless** (sensor), el controller es **stateful** (actuador)
- El healthcheck puede ser consumido por otros sistemas (Prometheus, alertas, dashboards)
- Escalabilidad y monitoreo independiente

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  HEALTHCHECK (sensor)              SITE CONTROLLER (actuador)       │
│  ┌───────────────────┐             ┌──────────────────────┐        │
│  │ Observa:          │  GET /ready │ Decide:              │        │
│  │  • Airflow API    │────────────▶│  • DB primary local  │        │
│  │  • Redis          │             │    + checks OK       │        │
│  │  • DB primary     │             │    → scheduler ON    │        │
│  │  • Custom checks  │             │                      │        │
│  │                   │             │  • DB primary local  │        │
│  │ Reporta:          │             │    + check crítico   │        │
│  │  • /health        │             │    FALLA             │        │
│  │  • /region-health │             │    → FORZAR          │        │
│  │  • /ready         │             │    SWITCHOVER DB     │        │
│  │                   │             │                      │        │
│  │ NO toma acciones  │             │  • DB no primary     │        │
│  └───────────────────┘             │    → scheduler OFF   │        │
│                                    └──────────┬───────────┘        │
│                                               │                    │
│                                    ┌──────────▼───────────┐        │
│                                    │ Actúa via:           │        │
│                                    │  • Docker API        │        │
│                                    │    (pause/unpause)   │        │
│                                    │  • MaxScale API      │        │
│                                    │    (switchover)      │        │
│                                    └──────────────────────┘        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## El problema que resuelve el switchover forzado

Sin switchover forzado, hay un escenario de deadlock:

```
Hornos:      DB=PRIMARY, Airflow=MUERTO  → no puede servir
SanLorenzo:  DB=REPLICA, Airflow=OK      → no se promueve (DB no es primary)

Resultado: NADIE sirve. Deadlock.
```

Con switchover forzado:

```
1. Healthcheck-hornos detecta: airflow=unhealthy (check crítico)
2. Site-controller-hornos ve: needs_failover=true + DB es primary local
3. Después de N checks consecutivos → fuerza switchover via MaxScale
4. MaxScale promueve mariadb-sanlorenzo a PRIMARY
5. Site-controller-sanlorenzo detecta DB primary local → ACTIVE
6. Problema resuelto automáticamente
```

## Checks configurables

El healthcheck soporta checks configurables via variables de entorno. Cada check puede ser:
- **Habilitado/deshabilitado** → variable `CHECKS`
- **Crítico o informativo** → variable `CRITICAL_CHECKS`

Un check **crítico** que falla dispara el flag `needs_failover`. Un check **informativo** que falla se reporta pero no dispara acción.

### Checks built-in

| Check | Qué evalúa | Recomendación |
|---|---|---|
| `airflow` | Airflow API Server responde en /api/v2/monitor/health | **Crítico** — sin API Server no hay servicio |
| `redis` | Redis responde a PING | **Informativo** — Redis se reinicia rápido, no justifica mover DB |
| `db_primary` | DB local es Master en MaxScale | **Crítico** — sin DB primary no hay escrituras |

### Checks custom (extensible)

Para agregar checks sin tocar código:

```bash
# Formato: nombre:url,nombre:url
CUSTOM_CHECKS=vault:http://vault:8200/v1/sys/health,kafka:http://kafka:8083/health
# Agregarlos a la lista de checks
CHECKS=airflow,redis,db_primary,vault,kafka
# Marcar como críticos si corresponde
CRITICAL_CHECKS=airflow,db_primary,vault
```

### Ejemplo: configuración conservadora (producción)

```yaml
# Solo Airflow y DB son críticos. Redis es informativo.
# Switchover forzado habilitado pero con threshold alto.
environment:
  CHECKS: "airflow,redis,db_primary"
  CRITICAL_CHECKS: "airflow,db_primary"
  FAILURE_THRESHOLD: "5"          # 5 checks fallidos antes de confirmar
  CHECK_INTERVAL: "10"            # cada 10s
  # → 50 segundos antes de declarar unhealthy
```

### Ejemplo: configuración agresiva (desarrollo)

```yaml
environment:
  CHECKS: "airflow,redis,db_primary"
  CRITICAL_CHECKS: "airflow,redis,db_primary"  # todo es crítico
  FAILURE_THRESHOLD: "2"
  CHECK_INTERVAL: "5"
  # → 10 segundos antes de declarar unhealthy
```

## Estructura de carpetas

```
Healthcheck-Service/
├── healthcheck/                  # Microservicio 1: Sensor
│   ├── healthcheck.py            # Checks configurables + hysteresis
│   ├── Dockerfile
│   └── requirements.txt
├── site-controller/              # Microservicio 2: Actuador
│   ├── site_controller.py        # Consume healthcheck, controla scheduler
│   ├── Dockerfile
│   └── requirements.txt
├── healthcheck.py                # Versión monolítica (un solo servicio)
├── Dockerfile                    # Dockerfile de la versión monolítica
├── requirements.txt
└── README.md                     # Este archivo
```

La **versión monolítica** (`healthcheck.py` en la raíz) se mantiene como referencia y para demos. Para producción, usar los dos servicios separados.

## Deploy: docker-compose

```yaml
# ─── HEALTHCHECK (sensor) ───
healthcheck-hornos:
  build: ./Healthcheck-Service/healthcheck
  environment:
    - REGION_NAME=hornos
    - AIRFLOW_URL=http://airflow-apiserver-hornos:8080
    - MAXSCALE_URL=http://maxscale-hornos:8989
    - LOCAL_DB_SERVER=HORNOS
    - REDIS_HOST=redis-hornos
    - CHECKS=airflow,redis,db_primary
    - CRITICAL_CHECKS=airflow,db_primary
    - CHECK_INTERVAL=10
    - FAILURE_THRESHOLD=3
  ports:
    - "8001:8000"

# ─── SITE CONTROLLER (actuador) ───
site-controller-hornos:
  build: ./Healthcheck-Service/site-controller
  environment:
    - REGION_NAME=hornos
    - HEALTHCHECK_URL=http://healthcheck-hornos:8000
    - MAXSCALE_URL=http://maxscale-hornos:8989
    - LOCAL_DB_SERVER=HORNOS
    - MAXSCALE_MONITOR=Replication-Monitor
    - SCHEDULER_CONTAINER=airflow-scheduler-hornos
    - DAG_PROCESSOR_CONTAINER=airflow-dag-processor-hornos
    - FORCE_SWITCHOVER=true
    - SWITCHOVER_THRESHOLD=5
    - CHECK_INTERVAL=10
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
  ports:
    - "8011:8100"
```

## Deploy: OpenShift / Kubernetes

```yaml
# ─── ConfigMap (compartido) ───
apiVersion: v1
kind: ConfigMap
metadata:
  name: ha-config-hornos
data:
  REGION_NAME: "hornos"
  CHECKS: "airflow,redis,db_primary"
  CRITICAL_CHECKS: "airflow,db_primary"
  CHECK_INTERVAL: "10"
  FAILURE_THRESHOLD: "3"
  FORCE_SWITCHOVER: "true"
  SWITCHOVER_THRESHOLD: "5"

---
# ─── Healthcheck Deployment ───
apiVersion: apps/v1
kind: Deployment
metadata:
  name: healthcheck-hornos
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: healthcheck
          image: registry.internal/healthcheck:latest
          envFrom:
            - configMapRef:
                name: ha-config-hornos
          env:
            - name: AIRFLOW_URL
              value: "http://airflow-apiserver:8080"
            - name: MAXSCALE_URL
              value: "http://maxscale:8989"
          ports:
            - containerPort: 8000

---
# ─── Site Controller Deployment ───
# En Kubernetes, en lugar de docker.sock, el controller
# escalaría el Deployment del scheduler a 0/1 réplicas
# via Kubernetes API.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: site-controller-hornos
spec:
  replicas: 1
  template:
    spec:
      serviceAccountName: site-controller  # necesita permisos para scale
      containers:
        - name: controller
          image: registry.internal/site-controller:latest
          envFrom:
            - configMapRef:
                name: ha-config-hornos
          env:
            - name: HEALTHCHECK_URL
              value: "http://healthcheck-hornos:8000"
            - name: MAXSCALE_URL
              value: "http://maxscale:8989"
          ports:
            - containerPort: 8100
```

## Endpoints

### Healthcheck (puerto 8000)

| Endpoint | Uso | Respuesta |
|---|---|---|
| `GET /health` | Monitoreo/debugging | 200 siempre, estado detallado de todos los checks |
| `GET /region-health` | HAProxy | 200 si critical checks OK, 503 si no |
| `GET /ready` | Site-controller | 200 siempre, incluye `needs_failover` flag |

### Site Controller (puerto 8100)

| Endpoint | Uso | Respuesta |
|---|---|---|
| `GET /health` | Monitoreo/debugging | 200 siempre, estado del controller |
| `GET /region-health` | HAProxy (alternativo) | 200 si ACTIVE + healthy, 503 si no |
| `GET /role` | Scripts | 200 siempre, solo el rol |

## Flujo completo de failover

### Escenario: Airflow cae en la región activa

```
t=0s    Airflow cae en Hornos
t=10s   healthcheck-hornos: airflow=unhealthy (count=1/3)
t=20s   healthcheck-hornos: airflow=unhealthy (count=2/3)
t=30s   healthcheck-hornos: airflow=unhealthy (count=3/3) → needs_failover=true
t=30s   site-controller-hornos: ve needs_failover=true (sw_count=1/5)
t=40s   site-controller-hornos: sw_count=2/5
t=50s   site-controller-hornos: sw_count=3/5
t=60s   site-controller-hornos: sw_count=4/5
t=70s   site-controller-hornos: sw_count=5/5 → FORZAR SWITCHOVER
t=70s   site-controller-hornos: pause scheduler, POST switchover a MaxScale
t=72s   MaxScale promueve mariadb-sanlorenzo a PRIMARY
t=82s   site-controller-sanlorenzo: DB primary local (count=1/2)
t=92s   site-controller-sanlorenzo: DB primary local (count=2/2) → PROMOTE
t=92s   site-controller-sanlorenzo: unpause scheduler → ACTIVE

Tiempo total: ~90 segundos (configurable bajando thresholds)
```

### Escenario: MariaDB cae en la región activa

```
t=0s    mariadb-hornos cae
t=6s    MaxScale detecta y promueve mariadb-sanlorenzo (~failcount=3)
t=16s   site-controller-sanlorenzo: DB primary local (count=1/2)
t=26s   site-controller-sanlorenzo: DB primary local (count=2/2) → PROMOTE
t=36s   site-controller-hornos: DB no primary (count=3/3) → DEMOTE

Tiempo total: ~26 segundos (no necesita switchover forzado)
```
