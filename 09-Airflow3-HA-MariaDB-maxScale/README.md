# Airflow 3 HA con MariaDB + MaxScale (Red Única Simplificada)

## Arquitectura Simplificada

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MaxScale      │    │    MaxScale      │    │                 │
│   Hornos        │    │   San Lorenzo    │    │    Airflow 3    │
│   :4006         │    │    :4007         │    │     :8080       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
    ┌────────────────────────────┼────────────────────────────┐
    │                            │                            │
┌───▼────┐              ┌───────▼──┐              ┌──────────▼┐
│MariaDB │              │ MariaDB  │              │ MariaDB   │
│Hornos  │◄─────────────┤San Lorenzo│◄─────────────┤ Tucuman   │
│:3306   │  Replicación │  :3307   │  Replicación │  :3308    │
│PRIMARY │              │ REPLICA  │              │ARBITRATOR │
└────────┘              └──────────┘              └───────────┘
```

## Características

- **Red única**: Sin complejidad de múltiples redes
- **3 MariaDB**: Hornos (Primary), San Lorenzo (Replica), Tucuman (Arbitrator)
- **2 MaxScale**: Failover automático con monitoreo cooperativo
- **Airflow 3**: Con Celery Executor y Redis
- **Configuración como producción**: Usuarios y parámetros idénticos

## Inicio Rápido

```bash
# Iniciar todo el stack
start.bat

# Verificar estado
status.bat

# Limpiar todo
clean.bat
```

## Accesos

- **Airflow Web UI**: http://localhost:8080 (admin/admin)
- **MaxScale Hornos**: http://localhost:8989 (admin/mariadb)
- **MaxScale San Lorenzo**: http://localhost:8990 (admin/mariadb)

## Bases de Datos

- **MariaDB Hornos**: localhost:3306 (Primary)
- **MariaDB San Lorenzo**: localhost:3307 (Replica)
- **MariaDB Tucuman**: localhost:3308 (Arbitrator)

## MaxScale

- **MaxScale Hornos**: localhost:4006
- **MaxScale San Lorenzo**: localhost:4007

## Prueba de Failover Manual

```bash
# 1. Verificar estado inicial
status.bat

# 2. Simular falla del primary
docker-compose stop mariadb-hornos

# 3. Verificar failover automático (esperar ~10 segundos)
status.bat

# 4. Restaurar primary
docker-compose start mariadb-hornos

# 5. Verificar rejoin automático
status.bat
```

## Monitoreo

```bash
# Estado de MaxScale
docker-compose exec maxscale-hornos maxctrl list servers
docker-compose exec maxscale-sanlorenzo maxctrl list servers

# Estado de replicación
docker-compose exec mariadb-sanlorenzo mysql -u root -proot_pass -e "SHOW SLAVE STATUS\G"
docker-compose exec mariadb-tucuman mysql -u root -proot_pass -e "SHOW SLAVE STATUS\G"

# Logs de MaxScale
docker-compose logs maxscale-hornos
docker-compose logs maxscale-sanlorenzo
```

## DAG de Prueba

El DAG `test_ha_failover` se ejecuta cada 5 minutos y:
- Prueba la conexión a la base de datos
- Muestra información del servidor actual
- Crea tabla de prueba
- Inserta datos de prueba

Úsalo para verificar que el failover funciona correctamente durante las pruebas.

## Configuración de Producción

La configuración MaxScale es idéntica a producción:
- Usuarios: `monitor` y `maxscaleuser`
- Parámetros: `master_conditions=primary_monitor_master`
- Monitoreo cooperativo: `cooperative_monitoring_locks=majority_of_all`
- Intervalo: `monitor_interval=2000ms`