# Airflow 3.x Multi-Site HA con MaxScale

## Arquitectura Multi-Sitio

- **2 Sitios Airflow**: Hornos y San Lorenzo, cada uno con stack completo
- **HAProxy arriba**: Load balancer entre ambos sitios Airflow
- **Health Check por región**: Cada sitio tiene su propio microservicio de salud
- **MaxScale por sitio**: Cada Airflow apunta a su MaxScale local
- **MariaDB cluster compartido**: Misma metadata DB para ambos sitios
- **Redis por sitio**: Broker independiente para cada sitio

## Diagrama de Arquitectura Multi-Sitio

```
                    Usuario
                      |
                      ▼
                  HAProxy :8080
                 (Active/Passive)
                      |
              ┌───────┼───────┐
              ▼               ▼
      ┌─────────────┐   ┌─────────────┐
      │   HORNOS    │   │SAN LORENZO  │
      │ (PRIMARY)   │   │  (BACKUP)   │
      │             │   │             │
      │HealthCheck  │   │HealthCheck  │
      │  :8001      │   │  :8002      │
      │     │       │   │     │       │
      │     ▼       │   │     ▼       │
      │  Airflow    │   │  Airflow    │
      │ API:8081    │   │ API:8082    │
      │ Scheduler   │   │ Scheduler   │
      │     │       │   │     │       │
      │     ▼       │   │     ▼       │
      │   Redis     │   │   Redis     │
      │  :6379      │   │  :6379      │
      │     │       │   │     │       │
      │     ▼       │   │     ▼       │
      │  Workers    │   │  Workers    │
      │             │   │             │
      │     │       │   │     │       │
      │     ▼       │   │     ▼       │
      │  MaxScale   │   │  MaxScale   │
      │  :4006      │   │  :4007      │
      └──────┬──────┘   └──────┬──────┘
             │                 │
             └─────────┬───────┘
                       ▼
              ┌─────────────────┐
              │ MariaDB Cluster │
              │ H-S-T (Shared)  │
              │ 3306,3307,3308  │
              └─────────────────┘
```

### Flujo de Decisión HAProxy:
```
1. Usuario → HAProxy :8080
2. HAProxy → HealthCheck Hornos :8001/region-health
3. ¿Hornos healthy?
   ├─ SÍ → Enviar a Hornos :8081
   └─ NO → HealthCheck San Lorenzo :8002/region-health
              ├─ SÍ → Enviar a San Lorenzo :8082
              └─ NO → Error 503
```

## Configuración Clave

### MaxScale
```
auto_failover=true
auto_rejoin=true
cooperative_monitoring_locks=majority_of_running
master_conditions=running_slave
```

![MaxScale Example](docs/maxscale_example.png)

### MariaDB Slaves (CRÍTICO)
```
# Docker-compose
--read-only=ON

# Scripts de inicialización
SET GLOBAL read_only = 1;
SET GLOBAL super_read_only = 1;
```

## Proceso de Failover

1. **HORNOS DB falla** → MaxScale detecta la falla
2. **SANLORENZO DB** se promueve automáticamente a master
3. **Tráfico se redirige** al nuevo master
4. **HORNOS DB vuelve** → Se reintegra como replica

## Comandos Básicos

### Scripts de gestión
```bash
# Limpiar todo (volúmenes, contenedores, redes)
clear.bat

# Iniciar toda la infraestructura
start.bat

# Verificar estado de todos los servicios
status.bat
```

### Comandos manuales
```bash
# Iniciar manualmente
docker-compose up -d

# Parar todo
docker-compose down
```

### Verificar estado
```bash
# MaxScale 1
docker exec maxscale-hornos maxctrl list servers

# MaxScale 2 (puerto diferente)
docker exec maxscale-sanlorenzo maxctrl --hosts=127.0.0.1:8990 list servers
```

### Probar failover activo/pasivo

#### Escenario Normal: Todo va a Hornos
```bash
# Verificar que todo el tráfico va a Hornos
curl -I http://localhost:8080/

# Ver estadísticas - Hornos debe tener todo el tráfico
http://localhost:8404/stats

# Estado del health check por región
curl http://localhost:8001/health  # Hornos
curl http://localhost:8002/health  # San Lorenzo
```

#### Escenario Failover: Hornos falla, va a San Lorenzo
```bash
# Simular falla de Hornos
docker stop airflow-scheduler-hornos
# o
docker network disconnect 10-airflow3-ha-maxscale-multiregion_airflow-net airflow-apiserver-hornos

# Esperar ~90 segundos (3 health checks fallidos)
# Verificar que ahora va a San Lorenzo
curl -I http://localhost:8080/

# Ver stats - San Lorenzo debe estar activo, Hornos DOWN
http://localhost:8404/stats

# Estado detallado por región
curl http://localhost:8001/health  # Hornos
curl http://localhost:8002/health  # San Lorenzo
```

#### Escenario Recovery: Hornos vuelve, tráfico regresa
```bash
# Restaurar Hornos
docker start airflow-scheduler-hornos
# o
docker network connect 10-airflow3-ha-maxscale-multiregion_airflow-net airflow-apiserver-hornos

# Esperar ~60 segundos (2 health checks exitosos)
# Verificar que el tráfico regresó a Hornos
curl -I http://localhost:8080/

# Ver stats - Hornos activo, San Lorenzo backup
http://localhost:8404/stats
```

## Puertos

- **HAProxy Airflow**: 8080 (punto de entrada principal)
- **Health Check Hornos**: 8001 (microservicio de salud Hornos)
- **Health Check San Lorenzo**: 8002 (microservicio de salud San Lorenzo)
- **Airflow Hornos**: 8081 (acceso directo)
- **Airflow San Lorenzo**: 8082 (acceso directo)
- **HAProxy Stats**: 8404 (estadísticas)
- **MaxScale HORNOS**: 4006 (service), 8989 (admin)
- **MaxScale SANLORENZO**: 4007 (service), 8990 (admin)
- **MariaDB**: 3306, 3307, 3308

## Microservicio de Health Check (Distribuido)

### Arquitectura
- **Una imagen, múltiples instancias**: Mismo código fuente, configuración por ENV
- **Health Check Hornos**: Monitorea solo Airflow Hornos (puerto 8001)
- **Health Check San Lorenzo**: Monitorea solo Airflow San Lorenzo (puerto 8002)
- **Resiliencia**: Si una región cae, su health check también (comportamiento deseado)

### Configuración por Variables de Entorno
```bash
# Hornos
REGION_NAME=hornos
AIRFLOW_URL=http://airflow-apiserver-hornos:8080
LISTEN_PORT=8000

# San Lorenzo
REGION_NAME=sanlorenzo
AIRFLOW_URL=http://airflow-apiserver-sanlorenzo:8080
LISTEN_PORT=8000
```

### Propósito
- **Evalúa salud de Airflow**: Consume `/api/v2/monitor/health` de su región
- **Lógica inteligente**: Analiza metadatabase, scheduler, dag_processor
- **Histeresis**: Evita flapping con contadores de falla/recuperación
- **Endpoints para HAProxy**: Respuestas simples 200/503

### Criterios de Decisión
- **Healthy**: metadatabase + scheduler + dag_processor = healthy
- **Unhealthy**: Cualquier componente crítico falla
- **Degraded**: En período de gracia (< 3 fallas consecutivas)
- **Heartbeat**: Scheduler heartbeat debe ser reciente (< 2 min)

### Endpoints por Región
```bash
# Health Check Hornos
GET http://localhost:8001/health
GET http://localhost:8001/region-health

# Health Check San Lorenzo
GET http://localhost:8002/health
GET http://localhost:8002/region-health
```

## Conexión y Balanceo

### Acceso Principal
- **Puerto 8080**: HAProxy con failover activo/pasivo
- **Sitio Primario**: Hornos (preferencia siempre)
- **Sitio Backup**: San Lorenzo (solo si Hornos falla)
- **Health Check Inteligente**: Microservicio evalúa salud real de Airflow
- **Failover automático**: Si Hornos falla, redirige a San Lorenzo

### Acceso Directo (para testing)
- **Puerto 8081**: Acceso directo a Airflow Hornos
- **Puerto 8082**: Acceso directo a Airflow San Lorenzo
- **Puerto 8404**: Estadísticas de HAProxy
- **Puerto 8001**: Health Check Hornos (estado detallado)
- **Puerto 8002**: Health Check San Lorenzo (estado detallado)

### Flujo de conexión (Activo/Pasivo):
1. **Usuario** → **HAProxy** (puerto 8080) - Punto único de entrada
2. **HAProxy** → **Health Check Hornos** (puerto 8001) - ¿Está Hornos healthy?
3. **Si Hornos OK** → **Airflow Hornos** - Siempre preferencia
4. **Si Hornos FAIL** → **Health Check San Lorenzo** (puerto 8002) - ¿Está San Lorenzo healthy?
5. **Si San Lorenzo OK** → **Airflow San Lorenzo** - Solo como backup
6. **Airflow** → **MaxScale local** - Cada sitio usa su MaxScale
7. **MaxScale** → **MariaDB Cluster** - Routing inteligente al master

### Ventajas de la Arquitectura con Health Check:
- **Salud real**: No solo conectividad, evalúa componentes críticos
- **Evita falsos positivos**: Histeresis previene flapping
- **Transparencia total**: Usuario no sabe en qué sitio ejecuta
- **Producción ready**: Mismo patrón que GSLB corporativo
- **Observabilidad**: Endpoints detallados para monitoreo

## Solución a Problemas Comunes

### Problema: Slaves no se detectan correctamente
**Causa**: Falta configuración `--read-only=ON` en docker-compose
**Solución**: Ya corregido en mariadb-sanlorenzo y mariadb-tucuman

### Problema: Replicación se rompe al reiniciar
**Causa**: Scripts de init.sql no configuran read_only
**Solución**: Ya corregido con `SET GLOBAL read_only = 1;` en scripts