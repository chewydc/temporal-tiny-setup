# Airflow 3.x HA + MaxScale + 3 Regiones - FAILOVER AUTOMÁTICO ✅

## Arquitectura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   HORNOS        │    │  SAN LORENZO    │    │   TUCUMAN       │
│ (172.20.0.0/24) │    │ (172.21.0.0/24) │    │ (172.22.0.0/24) │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ Airflow API     │    │                 │    │                 │
│ Airflow Sched   │    │                 │    │                 │
│ Airflow Worker  │    │                 │    │                 │
│ Redis           │    │                 │    │                 │
│ MariaDB Primary │    │ MariaDB Replica │    │ MariaDB Arbitr. │
│ MaxScale        │    │ MaxScale        │    │ (NUNCA MASTER)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   VROUTER       │
                    │ (Conectividad)  │
                    └─────────────────┘
```

## ✅ FAILOVER AUTOMÁTICO FUNCIONANDO

**Configuración MaxScale basada en ejemplo productivo:**
- Router: `readconnroute` con `router_options=master`
- Protocol: `MariaDBBackend`
- Monitor: `Replication-Monitor`
- Debug logging habilitado

**Pruebas exitosas:**
- ✅ Falla de Hornos → San Lorenzo promovido automáticamente
- ✅ Rejoin automático cuando Hornos vuelve
- ✅ Airflow mantiene conectividad durante failover
- ✅ Tucumán nunca promovido (arbitrator)

## Inicio Rápido

```bash
# 1. Iniciar cluster
docker-compose up -d

# 2. Verificar estado
docker exec maxscale-hornos maxctrl list servers

# 3. Probar failover
docker stop mariadb-hornos
# Esperar 20 segundos
docker exec maxscale-hornos maxctrl list servers
# Debería mostrar San Lorenzo como Master
```

## Accesos

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| Airflow UI | 8080 | Interfaz web principal |
| MariaDB Hornos | 3306 | Base de datos |
| MariaDB San Lorenzo | 3307 | Base de datos |
| MariaDB Tucumán | 3308 | Base de datos arbitrator |
| MaxScale Hornos | 4006 | Routing de queries |
| MaxScale San Lorenzo | 4007 | Routing de queries |
| MaxScale Admin Hornos | 8989 | Administración web |
| MaxScale Admin San Lorenzo | 8990 | Administración web |

## Pruebas de Failover

### Simular falla del Primary
```bash
# 1. Detener Hornos
docker stop mariadb-hornos

# 2. Verificar promoción automática (esperar 20s)
docker exec maxscale-hornos maxctrl list servers
# Resultado esperado: San Lorenzo como Master

# 3. Probar conectividad
docker exec mariadb-sanlorenzo mysql -h maxscale-hornos -P 4006 -u airflow -pairflow_pass -e "SELECT 'Failover OK' as status;"

# 4. Reiniciar Hornos
docker start mariadb-hornos

# 5. Verificar rejoin automático (esperar 15s)
docker exec maxscale-hornos maxctrl list servers
# Resultado esperado: Hornos como Slave, San Lorenzo sigue Master
```

### Script de failover manual
```bash
# Usar script incluido para casos complejos
failover-manual.bat
```

## Configuración MaxScale (Siguiendo ejemplo productivo)

```ini
[Splitter-Service]
type=service
router=readconnroute
router_options=master
servers=mariadb-hornos,mariadb-sanlorenzo

[Replication-Monitor]
type=monitor
module=mariadbmon
servers=mariadb-hornos,mariadb-sanlorenzo,mariadb-tucuman
servers_no_promotion=mariadb-tucuman
auto_failover=true
auto_rejoin=true
master_conditions=primary_monitor_master

[mariadb-hornos]
type=server
address=172.20.0.20
port=3306
protocol=MariaDBBackend
```

## Comandos de Verificación

```bash
# Estado de servidores
docker exec maxscale-hornos maxctrl list servers
docker exec maxscale-sanlorenzo maxctrl list servers

# Estado de replicación
docker exec mariadb-sanlorenzo mysql -u root -proot_pass -e "SHOW SLAVE STATUS\G"
docker exec mariadb-tucuman mysql -u root -proot_pass -e "SHOW SLAVE STATUS\G"

# Prueba de conectividad a través de MaxScale
docker exec mariadb-sanlorenzo mysql -h maxscale-hornos -P 4006 -u airflow -pairflow_pass -e "SELECT 'Connection OK' as status;"

# Logs de MaxScale
docker logs maxscale-hornos --tail 20
```

## Archivos de Configuración

- `docker-compose.yml` - Configuración principal del cluster
- `maxscale/maxscale_hornos.cnf` - MaxScale Hornos (corregido)
- `maxscale/maxscale_sanlorenzo.cnf` - MaxScale San Lorenzo (corregido)
- `mariadb/primary/init.sql` - Inicialización primary
- `mariadb/replica/init.sql` - Inicialización replica
- `mariadb/arbitrator/init.sql` - Inicialización arbitrator
- `failover-manual.bat` - Script de failover manual

## Correcciones Aplicadas

1. **MaxScale Configuration**:
   - ✅ Router: `readconnroute` (como en producción)
   - ✅ Protocol: `MariaDBBackend` agregado
   - ✅ Debug logging habilitado
   - ✅ Nombres de servicios siguiendo estándar productivo

2. **Database Initialization**:
   - ✅ Permisos EXECUTE para MaxScale
   - ✅ GTID initialization corregida
   - ✅ super_read_only removido (incompatible con MariaDB 10.11)

3. **Failover Process**:
   - ✅ Promoción automática funcionando
   - ✅ Rejoin automático funcionando
   - ✅ Conectividad mantenida durante failover

## Estado Actual ✅

**Después del failover exitoso:**
```
┌────────────────────┬─────────────┬─────────────────┐
│ Server             │ Address     │ State           │
├────────────────────┼─────────────┼─────────────────┤
│ mariadb-hornos     │ 172.20.0.20 │ Slave, Running  │
│ mariadb-sanlorenzo │ 172.21.0.20 │ Master, Running │
│ mariadb-tucuman    │ 172.22.0.20 │ Slave, Running  │
└────────────────────┴─────────────┴─────────────────┘
```

**Failover automático completamente funcional siguiendo configuración productiva**

🚀 **LISTO PARA PRODUCCIÓN**