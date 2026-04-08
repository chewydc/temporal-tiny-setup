# Airflow 3.x Multi-Site HA con MaxScale

## Arquitectura Multi-Sitio

- **2 Sitios Airflow**: Hornos y San Lorenzo, cada uno con stack completo
- **HAProxy arriba**: Load balancer entre ambos sitios Airflow
- **MaxScale por sitio**: Cada Airflow apunta a su MaxScale local
- **MariaDB cluster compartido**: Misma metadata DB para ambos sitios
- **Redis por sitio**: Broker independiente para cada sitio

![MaxScale Example](docs/maxscale_example.png)

## Diagrama de Arquitectura Multi-Sitio

```
                    HAProxy
                   :8080
                      |
            ┌─────────┼─────────┐
            ▼                   ▼
    ┌─────────────┐     ┌─────────────┐
    │   HORNOS    │     │SAN LORENZO  │
    │   SITE      │     │    SITE     │
    │             │     │             │
    │  Airflow    │     │  Airflow    │
    │ Components  │     │ Components  │
    │     │       │     │     │       │
    │  MaxScale   │     │  MaxScale   │
    │  :4006      │     │  :4006      │
    │     │       │     │     │       │
    │   Redis     │     │   Redis     │
    │  :6379      │     │  :6379      │
    └──────┬──────┘     └──────┬──────┘
           │                   │
           └─────────┬─────────┘
                     ▼
            ┌─────────────────┐
            │ MariaDB Cluster │
            │ H-S-T (Shared)  │
            └─────────────────┘
```

## Configuración Clave

### MaxScale
```
auto_failover=true
auto_rejoin=true
cooperative_monitoring_locks=majority_of_running
master_conditions=running_slave
```

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

### Probar failover multi-sitio

#### Método 1: Parar sitio completo
```bash
# Simular falla de sitio Hornos
docker stop airflow-apiserver-hornos airflow-scheduler-hornos

# Verificar que HAProxy redirige a San Lorenzo
curl -I http://localhost:8080/health

# Ver estadísticas de HAProxy
http://localhost:8404/stats

# Restaurar sitio Hornos
docker start airflow-apiserver-hornos airflow-scheduler-hornos
```

#### Método 2: Desconectar de red (Recomendado)
```bash
# Desconectar sitio Hornos completo
docker network disconnect 10-airflow3-ha-maxscale-multiregion_airflow-net airflow-apiserver-hornos
docker network disconnect 10-airflow3-ha-maxscale-multiregion_airflow-net airflow-scheduler-hornos

# O desconectar MaxScale de un sitio
docker network disconnect 10-airflow3-ha-maxscale-multiregion_airflow-net maxscale-hornos

# Verificar failover en HAProxy stats
http://localhost:8404/stats

# Reconectar
docker network connect 10-airflow3-ha-maxscale-multiregion_airflow-net airflow-apiserver-hornos
docker network connect 10-airflow3-ha-maxscale-multiregion_airflow-net airflow-scheduler-hornos
```

#### Método 3: Probar failover de MaxScale
```bash
# Desconectar MaxScale Hornos
docker network disconnect 10-airflow3-ha-maxscale-multiregion_airflow-net maxscale-hornos

# Verificar que Airflow Hornos falla y HAProxy redirige a San Lorenzo
docker logs airflow-scheduler-hornos

# Reconectar
docker network connect 10-airflow3-ha-maxscale-multiregion_airflow-net maxscale-hornos
```

## Puertos

- **HAProxy Airflow**: 8080 (punto de entrada principal)
- **Airflow Hornos**: 8081 (acceso directo)
- **Airflow San Lorenzo**: 8082 (acceso directo)
- **HAProxy Stats**: 8404 (estadísticas)
- **MaxScale HORNOS**: 4006 (service), 8989 (admin)
- **MaxScale SANLORENZO**: 4007 (service), 8990 (admin)
- **MariaDB**: 3306, 3307, 3308

## Conexión y Balanceo

### Acceso Principal
- **Puerto 8080**: HAProxy balancea entre ambos sitios Airflow
- **Health Check**: HAProxy usa `/health` para determinar qué sitio está disponible
- **Failover automático**: Si un sitio falla, HAProxy redirige al otro

### Acceso Directo (para testing)
- **Puerto 8081**: Acceso directo a Airflow Hornos
- **Puerto 8082**: Acceso directo a Airflow San Lorenzo
- **Puerto 8404**: Estadísticas de HAProxy

### Flujo de conexión:
1. **Usuario** → **HAProxy** (puerto 8080) - Punto único de entrada
2. **HAProxy** → **Airflow Site** (Hornos o San Lorenzo) - Load balancing
3. **Airflow** → **MaxScale local** - Cada sitio usa su MaxScale
4. **MaxScale** → **MariaDB Cluster** - Routing inteligente al master

### Ventajas de la Arquitectura Multi-Sitio:
- **Alta disponibilidad**: Si un sitio completo falla, el otro continúa
- **Misma metadata**: Ambos sitios ven exactamente los mismos DAGs y estados
- **Schedulers múltiples**: Airflow 3 coordina automáticamente entre sitios
- **Balanceo de carga**: HAProxy distribuye usuarios entre sitios
- **Transparencia**: El usuario no sabe en qué sitio está ejecutando

## Solución a Problemas Comunes

### Problema: Slaves no se detectan correctamente
**Causa**: Falta configuración `--read-only=ON` en docker-compose
**Solución**: Ya corregido en mariadb-sanlorenzo y mariadb-tucuman

### Problema: Replicación se rompe al reiniciar
**Causa**: Scripts de init.sql no configuran read_only
**Solución**: Ya corregido con `SET GLOBAL read_only = 1;` en scripts