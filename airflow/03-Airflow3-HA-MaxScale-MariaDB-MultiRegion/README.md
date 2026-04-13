# Caso 03: Airflow 3 Multi-Región Active/Passive HA

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
# Via MaxScale API:
curl -u admin:mariadb -X POST http://localhost:8989/v1/maxscale/modules/mariadbmon/Replication-Monitor/switchover?HORNOS
```

### Endpoints

| URL | Descripción |
|---|---|
| http://localhost:8080 | Airflow UI (via HAProxy → región activa) |
| http://localhost:8404/stats | HAProxy stats |
| http://localhost:8001/health | Site controller Hornos (detalle) |
| http://localhost:8002/health | Site controller SanLorenzo (detalle) |
| http://localhost:8001/role | Solo el rol (active/passive) |
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
| 8001 | Site Controller Hornos |
| 8002 | Site Controller SanLorenzo |
| 8404 | HAProxy Stats |
| 8989 | MaxScale Hornos Admin |
| 8990 | MaxScale SanLorenzo Admin |
