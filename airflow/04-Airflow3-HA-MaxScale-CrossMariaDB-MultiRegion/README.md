# Caso 04: Airflow 3 HA — Cross-DB Multi-Region (MaxScale como árbitro)

## Cambio clave vs Caso 03

| | Caso 03 | Caso 04 |
|---|---|---|
| Trigger de failover | DB Master se mueve | MaxScale local cae o Airflow cae |
| DB cruzada | Causa failover ❌ | OK, no pasa nada ✅ |
| Healthcheck crítico | `airflow` + `db_primary` | `airflow` + `maxscale_healthy` |
| Site-controller | Sigue al DB Master | Región preferida + peer cross-check |
| Switchover de DB | Forzado por controller | No, MaxScale se encarga solo |
| Anti split-brain | DB Master único | MaxScale cooperative locking |

## Arquitectura

```
                    ┌─────────────┐
                    │   HAProxy   │ :8080
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
         │  PREFERRED  │   │   STANDBY        │
         │             │   │                  │
         │ API Server  │   │ API Server       │
         │ Scheduler ▶ │   │ Scheduler ⏸      │
         │ DagProc   ▶ │   │ DagProc   ⏸      │
         │ Workers x2  │   │ Workers x2       │
         │ Redis       │   │ Redis            │
         │             │   │                  │
         │ MaxScale ───┼───┼── MaxScale       │
         │    ↕        │   │      ↕           │
         │ MariaDB     │   │  MariaDB         │
         │ (PRIMARY o  │   │  (PRIMARY o      │
         │  REPLICA)   │   │   REPLICA)       │
         └─────────────┘   └──────────────────┘
                    │             │
         ┌──────────▼─────────────▼──┐
         │  Site Controller hornos   │◄──► Site Controller sanlorenzo
         │  PREFERRED=true           │     PREFERRED=false
         │                           │
         │  "¿Mi MaxScale ve Master?"│     "¿Mi MaxScale ve Master?"
         │  "¿Mi Airflow está OK?"   │     "¿Mi Airflow está OK?"
         │  "¿Soy preferida?"       │     "¿El peer está caído?"
         └───────────────────────────┘
                    │
         ┌──────────▼───────────────┐
         │  MariaDB TUCUMAN         │
         │  (ARBITRATOR)            │
         │  read-only, no-promotion │
         └──────────────────────────┘
```

## Principio de diseño: MaxScale como árbitro

**La DB puede estar en cualquier región.** Lo que importa es:

1. MaxScale con `cooperative_monitoring_locks=majority_of_running` garantiza que solo un MaxScale opera failovers
2. Cada MaxScale rutea al Master esté donde esté (cross-region OK con ~1ms latencia)
3. El healthcheck valida: ¿mi MaxScale responde Y ve un Master?
4. El site-controller decide: ¿soy la región preferida? ¿o el peer está caído?

**Anti split-brain:** Si se corta la red entre regiones, el MaxScale aislado pierde el cooperative lock y no ve Master → healthcheck unhealthy → site PASSIVE. Solo la región con mayoría de nodos MariaDB visibles puede ser ACTIVE.

## Lógica de decisión del Site Controller

| Mi MaxScale | Ve Master | Airflow | Preferida | Peer | Resultado |
|---|---|---|---|---|---|
| ✅ | ✅ | ✅ | Sí | - | **ACTIVE** |
| ✅ | ✅ | ✅ | No | Caído | **ACTIVE** (failover) |
| ✅ | ✅ | ✅ | No | OK | PASSIVE |
| ✅ | ❌ | - | - | - | PASSIVE |
| ❌ | - | - | - | - | PASSIVE |
| - | - | ❌ | - | - | PASSIVE |

## Flujos de failover

### Estado normal
```
Hornos:      MaxScale OK + Airflow OK + PREFERRED → ACTIVE  → HAProxy 200
SanLorenzo:  MaxScale OK + Airflow OK + !PREFERRED + peer OK → PASSIVE → HAProxy 503
DB Master:   En Hornos (o en San Lorenzo, no importa)
```

### Falla Airflow en Hornos
```
1. Airflow Hornos cae
2. Healthcheck Hornos → airflow=unhealthy → critical_healthy=false
3. Site-controller Hornos → DEMOTE → scheduler OFF → HAProxy 503
4. Site-controller SanLorenzo → peer unhealthy → PROMOTE → scheduler ON → HAProxy 200
5. MaxScale SanLorenzo rutea al DB Master (esté donde esté)
6. ✅ San Lorenzo opera con DB cruzada si es necesario
```

### Falla MaxScale en Hornos
```
1. MaxScale Hornos cae
2. Healthcheck Hornos → maxscale_healthy=unhealthy → critical_healthy=false
3. Site-controller Hornos → DEMOTE → scheduler OFF → HAProxy 503
4. Site-controller SanLorenzo → peer unhealthy → PROMOTE → scheduler ON → HAProxy 200
5. ✅ San Lorenzo opera normalmente
```

### DB Master se mueve (MaxScale failover automático)
```
1. MariaDB Hornos cae → MaxScale promueve MariaDB SanLorenzo a Master
2. Healthcheck Hornos → maxscale_healthy=healthy (MaxScale ve nuevo Master)
3. Site-controller Hornos → sigue ACTIVE (es preferred y MaxScale funciona)
4. ✅ Hornos opera con DB cruzada (Master en SanLorenzo, ~1ms latencia)
5. NO hay failover de región, solo de DB
```

### Corte de red entre regiones (split-brain prevention)
```
1. Red entre Hornos y SanLorenzo se corta
2. MaxScale Hornos: ve 1 de 3 MariaDB → pierde cooperative lock → no ve Master
3. MaxScale SanLorenzo: ve 2 de 3 MariaDB → mantiene lock → ve Master
4. Healthcheck Hornos → maxscale_healthy=unhealthy → PASSIVE
5. Healthcheck SanLorenzo → maxscale_healthy=healthy → ACTIVE
6. ✅ Solo una región activa, no hay split-brain
```

### Recuperación de Hornos
```
1. Hornos vuelve → MaxScale reconecta → ve Master
2. Healthcheck Hornos → maxscale_healthy=healthy + airflow=healthy
3. Site-controller Hornos → PREFERRED + healthy → PROMOTE → ACTIVE
4. Site-controller SanLorenzo → peer healthy + !PREFERRED → DEMOTE → PASSIVE
5. ✅ Hornos retoma como región activa
```

## Componentes

| Componente | Función |
|---|---|
| MariaDB (3 nodos) | Primary/Replica/Arbitrator con replicación GTID |
| MaxScale (2 nodos) | Proxy DB con failover automático y cooperative locking |
| Healthcheck (2) | Valida MaxScale funcional + Airflow OK |
| Site Controller (2) | Región preferida + peer cross-check, controla scheduler |
| HAProxy | Enruta al site-controller que responde 200 |
| Airflow API Server | Siempre activo en ambas regiones |
| Airflow Scheduler | Solo activo en la región ACTIVE |
| Airflow Workers | Activos solo en la región ACTIVE |

## Uso

### Arranque
```bash
start.bat
```

### Ver estado
```bash
status.bat
```

### Probar failover — Airflow cae
```bash
# Simular caída de Airflow en Hornos
docker pause airflow-apiserver-hornos

# Esperar ~20-30s
status.bat

# Recuperar
docker unpause airflow-apiserver-hornos
```

### Probar failover — MaxScale cae
```bash
# Simular caída de MaxScale en Hornos
docker pause maxscale-hornos

# Esperar ~20-30s → SanLorenzo toma el control
status.bat

# Recuperar
docker unpause maxscale-hornos
```

### Probar DB cruzada (NO debe causar failover)
```bash
# Mover DB Master a SanLorenzo
curl -u admin:mariadb -X POST http://localhost:8989/v1/maxscale/modules/mariadbmon/switchover?Replication-Monitor

# Verificar: Hornos sigue ACTIVE, DB Master en SanLorenzo
status.bat

# Volver DB a Hornos (opcional)
curl -u admin:mariadb -X POST http://localhost:8989/v1/maxscale/modules/mariadbmon/switchover?Replication-Monitor
```

## Endpoints

| URL | Descripción |
|---|---|
| http://localhost:8080 | Airflow UI (via HAProxy → región activa) |
| http://localhost:8404/stats | HAProxy stats |
| http://localhost:8011/health | Site controller Hornos (detalle) |
| http://localhost:8012/health | Site controller SanLorenzo (detalle) |
| http://localhost:8011/role | Solo el rol (active/passive) |
| http://localhost:8001/health | Healthcheck Hornos (detalle) |
| http://localhost:8002/health | Healthcheck SanLorenzo (detalle) |
| http://localhost:8081 | Airflow Hornos directo |
| http://localhost:8082 | Airflow SanLorenzo directo |

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

## Troubleshooting

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
1. **Ambas regiones PASSIVE**: Verificar que al menos un MaxScale ve un Master
2. **DB cruzada con latencia alta**: Verificar conectividad entre MaxScale y MariaDB remota
3. **Split-brain sospechado**: Verificar cooperative_monitoring_locks en MaxScale logs
4. **Failover lento**: Ajustar FAILURE_THRESHOLD y CHECK_INTERVAL
