# Caso 03: Airflow 3 Multi-Región Active/Passive HA

## ✅ Recent Bug Fixes & Improvements

### Fixed Ping-Pong Switchover Issue
**Problem**: Site controllers were creating unstable ping-pong behavior, rapidly switching DB primary between regions.

**Root Cause**: Incorrect switchover logic triggered switchovers when a region already had the DB locally.

**Solution**: Fixed switchover logic to only trigger when `db_primary=False` and `needs_failover=True`.

### Multi-MaxScale Failover Support
**Enhancement**: Added support for multiple MaxScale URLs with automatic failover.

**Configuration**: 
```yaml
environment:
  - MAXSCALE_URLS=http://maxscale-hornos:8989,http://maxscale-sanlorenzo:8990
```

**Behavior**: Automatically tries backup MaxScale if primary is unavailable.

### Correct MaxScale API Endpoint
**Fixed**: Updated to use correct switchover API endpoint:
```
POST /v1/maxscale/modules/mariadbmon/switchover?{monitor-name}
```

## Arquitectura

```
                    ┌─────────────┐
                    │   HAProxy   │ :8080 (GSLB)
                    │  (balance   │
                    │   first)    │
                    └──────┬──────┘
                           │
              healthcheck  │  healthcheck
              /region-health  /region-health
              (200=active) │  (503=passive)
                    ┌──────┴──────┐
                    │             │
         ┌──────────▼──┐   ┌─────▼───────────┐
         │   HORNOS    │   │   SAN LORENZO    │
         │  (ACTIVE)   │   │   (PASSIVE)      │
         │             │   │                  │
         │ API Server  │   │ API Server       │
         │ Scheduler ▶ │   │ Scheduler ⏸      │
         │ DagProc   ▶ │   │ DagProc   ⏸      │
         │ Workers x2  │   │ Workers x2       │
         │ Redis       │   │ Redis            │
         │             │   │                  │
         │ MaxScale ─┐ │   │ MaxScale ─┐      │
         │           │ │   │           │      │
         │ MariaDB   │ │   │ MariaDB   │      │
         │ (PRIMARY) │ │   │ (REPLICA) │      │
         └───────────┘ │   └───────────┘      │
                       │                      │
         ┌─────────────▼──┐                   │
         │ Site Controller│◄──────────────────┘
         │    (hornos)    │  "¿Mi DB local es primary?"
         │                │  → Sí → scheduler ON
         │                │  → No → scheduler OFF
         └────────────────┘

         ┌────────────────┐
         │  MariaDB       │
         │  TUCUMAN       │
         │  (ARBITRATOR)  │
         │  read-only     │
         └────────────────┘
```

## Principio de diseño: DB primary = región activa

**No hay un servicio de elección de líder separado.** La fuente de verdad es MaxScale:

1. MaxScale ya garantiza que solo hay **un primary** a la vez (`cooperative_monitoring_locks=majority_of_running`)
2. Cada **site-controller** pregunta a su MaxScale local: "¿mi DB es el Master?"
3. Si sí → activa el scheduler (unpause container)
4. Si no → apaga el scheduler (pause container)
5. HAProxy consulta al site-controller: solo enruta al que responde 200

**Split-brain es imposible** porque MaxScale con cooperative locking ya lo previene a nivel DB. El site-controller simplemente **sigue** esa decisión.

## Componentes

| Componente | Función |
|---|---|
| MariaDB (3 nodos) | Primary/Replica/Arbitrator con replicación GTID |
| MaxScale (2 nodos) | Proxy DB con failover automático y cooperative locking |
| Site Controller (2) | Sigue al DB primary, controla scheduler via Docker API |
| HAProxy | GSLB - enruta al site-controller que responde 200 |
| Airflow API Server | Siempre activo en ambas regiones (read-only es OK) |
| Airflow Scheduler | Solo activo en la región con DB primary |
| Airflow Workers | Activos en ambas regiones (ejecutan tasks del broker local) |

## Flujo de failover

### ✅ Comportamiento Corregido
**Escenario original del bug**: MaxScale local caído, necesita switchover
1. **Hornos detecta**: MaxScale local down, `db_primary=False`, `needs_failover=True`
2. **Hornos ejecuta switchover**: DB se mueve a San Lorenzo
3. **San Lorenzo recibe DB**: Se vuelve ACTIVE
4. **FIN**: No más switchovers porque San Lorenzo tiene `db_primary=True`

**Antes (incorrecto)**: Ambas regiones hacían switchover cuando tenían la DB localmente
**Ahora (correcto)**: Solo se hace switchover cuando NO se tiene la DB pero se necesita

### Estado normal
```
Hornos:      DB=PRIMARY  → site-controller=ACTIVE  → scheduler=ON   → HAProxy=200
SanLorenzo:  DB=REPLICA  → site-controller=PASSIVE → scheduler=OFF  → HAProxy=503
```

### Falla Hornos (DB cae)
```
1. MaxScale detecta caída de mariadb-hornos (failcount=3, ~6s)
2. MaxScale promueve mariadb-sanlorenzo a PRIMARY
3. site-controller-sanlorenzo detecta DB primary local (recovery_threshold=2, ~20s)
4. site-controller-sanlorenzo UNPAUSE scheduler-sanlorenzo
5. site-controller-hornos detecta DB ya no es primary (failover_threshold=3, ~30s)
6. site-controller-hornos PAUSE scheduler-hornos (si aún corre)
7. HAProxy detecta sanlorenzo=200, hornos=503 → redirige tráfico
```

### Recuperación Hornos
```
1. mariadb-hornos vuelve → MaxScale lo reincorpora como REPLICA (auto_rejoin)
2. DB primary sigue en SanLorenzo (no hay switchback automático)
3. Para volver a Hornos: switchover manual via MaxScale
```

## Uso

### Arranque
```bash
start.bat
```

### Ver estado
```bash
status.bat
```

### Probar failover
```bash
# Simular caída de Hornos
docker pause mariadb-hornos

# Esperar ~30-40s y verificar
status.bat

# Recuperar Hornos (queda como replica)
docker unpause mariadb-hornos

# Switchover manual a Hornos (opcional)
# Via MaxScale API (endpoint corregido):
curl -u admin:mariadb -X POST http://localhost:8989/v1/maxscale/modules/mariadbmon/switchover?Replication-Monitor
```

### ✅ Probar el bug fix (MaxScale local caído)
```bash
# Simular MaxScale Hornos caído (el escenario original del bug)
docker pause maxscale-hornos

# Hornos detectará que necesita DB pero no la tiene localmente
# Ejecutará switchover via maxscale-sanlorenzo (backup)
# San Lorenzo recibirá la DB y se volverá ACTIVE
# NO habrá ping-pong porque San Lorenzo ya tiene la DB

# Verificar logs
docker logs site-controller-hornos --tail 20
docker logs site-controller-sanlorenzo --tail 20

# Recuperar MaxScale Hornos
docker unpause maxscale-hornos
```

### Endpoints

| URL | Descripción |
|---|---|
| http://localhost:8080 | Airflow UI (via HAProxy → región activa) |
| http://localhost:8404/stats | HAProxy stats |
| http://localhost:8011/health | Site controller Hornos (detalle) |
| http://localhost:8012/health | Site controller SanLorenzo (detalle) |
| http://localhost:8011/role | Solo el rol (active/passive) |
| http://localhost:8081 | Airflow Hornos directo |
| http://localhost:8082 | Airflow SanLorenzo directo |

### ✅ Nuevos Endpoints de Healthcheck
| URL | Descripción |
|---|---|
| http://localhost:8001/health | Healthcheck Hornos (detalle) |
| http://localhost:8002/health | Healthcheck SanLorenzo (detalle) |
| http://localhost:8001/ready | Status para site-controller |
| http://localhost:8002/ready | Status para site-controller |

## Puertos

| Puerto | Servicio |
|---|---|
| 3306 | MariaDB Hornos |
| 3307 | MariaDB SanLorenzo |
| 3308 | MariaDB Tucumán |
| 4006 | MaxScale Hornos |
| 4007 | MaxScale SanLorenzo |
| 8080 | HAProxy → Airflow |
| 8081 | Airflow Hornos directo |
| 8082 | Airflow SanLorenzo directo |
| 8001 | Healthcheck Hornos |
| 8002 | Healthcheck SanLorenzo |
| 8011 | Site Controller Hornos |
| 8012 | Site Controller SanLorenzo |
| 8404 | HAProxy Stats |
| 8989 | MaxScale Hornos Admin |
| 8990 | MaxScale SanLorenzo Admin |

## ✅ Troubleshooting

### Verificar estado del sistema
```bash
# Estado general
status.bat

# Logs de site-controllers
docker logs site-controller-hornos --tail 20
docker logs site-controller-sanlorenzo --tail 20

# Logs de healthchecks
docker logs healthcheck-hornos --tail 20
docker logs healthcheck-sanlorenzo --tail 20

# Estado de MaxScale
curl -u admin:mariadb http://localhost:8989/v1/servers
curl -u admin:mariadb http://localhost:8990/v1/servers
```

### Problemas comunes
1. **Ping-pong behavior**: Verificar que se esté usando la lógica corregida
2. **MaxScale connection failures**: Verificar MAXSCALE_URLS en docker-compose.yml
3. **Switchover API errors**: Verificar formato del endpoint y nombre del monitor
