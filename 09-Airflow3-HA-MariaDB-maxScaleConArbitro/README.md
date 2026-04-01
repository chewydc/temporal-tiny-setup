# Airflow 3.x HA + MaxScale + 3 Regiones - FUNCIONANDO ✅

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

## Características ✅

- **MaxScale con 3 Regiones**: Primary/Replica + Arbitrator
- **Failover Automático**: MaxScale detecta fallos y promueve replicas
- **Arbitrator Dedicado**: Tucumán solo para desempate (nunca master)
- **Conectividad Multi-Red**: Cada MaxScale conectado a todas las redes vía VRouter
- **Replicación Funcionando**: Master-Slave correctamente configurado
- **Control de Tráfico**: Preparado para iptables en VRouter

## Componentes

### Región Hornos (172.20.0.0/24) - PRINCIPAL
- Airflow completo (API, Scheduler, DAG Processor, Workers)
- Redis local
- MariaDB Primary (Master)
- MaxScale (conectado a todas las redes)
- Puerto 8080 (Airflow UI)
- Puerto 3306 (MariaDB)
- Puerto 4006 (MaxScale)
- Puerto 8989 (MaxScale Admin)

### Región San Lorenzo (172.21.0.0/24) - REPLICA
- MariaDB Replica (Slave)
- MaxScale (conectado a todas las redes)
- Puerto 3307 (MariaDB)
- Puerto 4007 (MaxScale)
- Puerto 8990 (MaxScale Admin)

### Región Tucumán (172.22.0.0/24) - ARBITRATOR
- Solo MariaDB configurado como arbitrator
- **NUNCA puede ser promovido a master**
- Solo para desempate en split-brain
- Puerto 3308 (MariaDB)

### VRouter Central
- Conecta las 3 redes
- Permite desconectar regiones específicas
- Simula fallos de conectividad

## Inicio Rápido

```bash
# 1. Iniciar todo el cluster
start.bat

# 2. Verificar estado
status.bat

# 3. Probar conectividad
network-control.bat status
```

## Accesos

- **Airflow (Principal)**: http://localhost:8080
- **MaxScale Hornos Admin**: http://localhost:8989
- **MaxScale San Lorenzo Admin**: http://localhost:8990
- **MariaDB Hornos (Primary)**: localhost:3306
- **MariaDB San Lorenzo (Replica)**: localhost:3307
- **MariaDB Tucumán (Arbitrator)**: localhost:3308
- **MaxScale Hornos (Routing)**: localhost:4006
- **MaxScale San Lorenzo (Routing)**: localhost:4007

## Pruebas de Failover

### 1. Fallo de Hornos (Primary)
```bash
network-control.bat disconnect hornos
```
- MaxScale detecta fallo del primary
- Promueve San Lorenzo a master automáticamente
- Airflow solo disponible en San Lorenzo (puerto 8081)
- Tucumán sigue como arbitrator

### 2. Fallo de San Lorenzo (Replica)
```bash
network-control.bat disconnect sanlorenzo
```
- Hornos sigue como master
- Airflow sigue funcionando desde Hornos
- Tucumán mantiene arbitraje

### 3. Fallo de Tucumán (Arbitrator)
```bash
network-control.bat disconnect tucuman
```
- Cluster vulnerable a split-brain
- Hornos y San Lorenzo siguen funcionando
- Sin arbitrator para desempate

### 4. Prueba Completa de Failover
```bash
network-control.bat failover
```
- Desconecta Hornos automáticamente
- Verifica promoción de San Lorenzo
- Reconecta todo
- Prueba completa de HA

### 5. Reconectar Todo
```bash
network-control.bat reconnect
```
- Todas las regiones vuelven online
- MaxScale reconfigura automáticamente
- Replicación se restablece

## Comandos Útiles

### Estado del Cluster
```bash
# Ver estado general
network-control.bat status

# Monitor en tiempo real
status.bat

# Test de conectividad
network-control.bat test
```

### Consultas MaxScale
```bash
# Estado de servidores
curl http://localhost:8989/v1/servers

# Estado de servicios
curl http://localhost:8989/v1/services

# Logs de MaxScale
docker logs maxscale-hornos
```

### Consultas MariaDB Directas
```bash
# Estado del master
docker exec cluster-monitor mysql -h mariadb-primary-hornos -u root -proot_pass --skip-ssl -e "SHOW MASTER STATUS"

# Estado de replica
docker exec cluster-monitor mysql -h mariadb-replica-sanlorenzo -u root -proot_pass --skip-ssl -e "SHOW SLAVE STATUS"

# Verificar arbitrator (read-only)
docker exec cluster-monitor mysql -h mariadb-arbitrator-tucuman -u root -proot_pass --skip-ssl -e "SELECT @@read_only, @@super_read_only"
```

## Escenarios de Prueba

### Escenario 1: Fallo del Primary
1. Ejecutar DAG `failover_test` en Hornos
2. `network-control.bat disconnect hornos`
3. Verificar que MaxScale promueve San Lorenzo
4. DAG debería completar desde San Lorenzo

### Escenario 2: Split-Brain Prevention
1. `network-control.bat disconnect tucuman`
2. `network-control.bat disconnect hornos`
3. Solo San Lorenzo queda → MaxScale no puede decidir
4. Verificar comportamiento de failover

### Escenario 3: Recuperación Automática
1. Desconectar cualquier región
2. Esperar 2 minutos
3. `network-control.bat reconnect`
4. Verificar reconfiguración automática

## Configuración MaxScale

### Servidores
- **mariadb-primary-hornos**: Priority 100 (preferido como master)
- **mariadb-replica-sanlorenzo**: Priority 90 (puede ser promovida)
- **mariadb-arbitrator-tucuman**: Priority 1 + `servers_no_promotion`

### Failover
- `auto_failover=true`: Failover automático
- `auto_rejoin=true`: Rejoin automático
- `verify_master_failure=true`: Verificación de fallo
- `master_failure_timeout=30s`: Timeout de detección

### Read/Write Split
- Writes → Primary (o nuevo master tras failover)
- Reads → Cualquier servidor disponible
- `master_accept_reads=true`: Master también acepta reads

## Troubleshooting

### MaxScale No Inicia
```bash
# Verificar logs
docker logs maxscale-hornos

# Verificar conectividad a MariaDB
docker exec maxscale-hornos maxctrl list servers
```

### Replicación Rota
```bash
# Reiniciar replicación
docker exec mariadb-replica-sanlorenzo mysql -u root -proot_pass -e "STOP SLAVE; START SLAVE;"

# Verificar estado
docker exec mariadb-replica-sanlorenzo mysql -u root -proot_pass -e "SHOW SLAVE STATUS\G"
```

### Failover Manual
```bash
# Forzar failover via MaxScale
docker exec maxscale-hornos maxctrl call command mariadbmon failover MariaDB-Monitor
```

## Archivos de Configuración

- `docker-compose.yml`: Definición completa del cluster
- `maxscale/maxscale_hornos.cnf`: Configuración MaxScale Hornos
- `maxscale/maxscale_sanlorenzo.cnf`: Configuración MaxScale San Lorenzo
- `mariadb/primary/init.sql`: Inicialización primary
- `mariadb/replica/init.sql`: Inicialización replica
- `mariadb/arbitrator/init.sql`: Inicialización arbitrator
- `network-control.bat`: Control de conectividad
- `start.bat`: Inicio secuencial del cluster
- `status.bat`: Monitor en tiempo real

## Ventajas de esta Arquitectura

1. **MaxScale Probado**: Solución madura para HA
2. **Failover Automático**: Sin intervención manual
3. **Arbitrator Dedicado**: Prevención de split-brain
4. **Conectividad Multi-Red**: MaxScale ve todos los servidores
5. **Control de Tráfico**: VRouter preparado para iptables
6. **Replicación Sólida**: Master-Slave funcionando correctamente
7. **Monitoreo Completo**: Estado en tiempo real

## Estado Actual ✅

```
=== MAXSCALE SERVERS ===
--- MaxScale Hornos ---
│ mariadb-hornos     │ 172.20.0.20 │ Master, Running │
│ mariadb-sanlorenzo │ 172.21.0.20 │ Slave, Running  │
│ mariadb-tucuman    │ 172.22.0.20 │ Slave, Running  │

--- MaxScale San Lorenzo ---
│ mariadb-hornos     │ 172.20.0.20 │ Master, Running │
│ mariadb-sanlorenzo │ 172.21.0.20 │ Slave, Running  │
│ mariadb-tucuman    │ 172.22.0.20 │ Slave, Running  │
```

**Conectividad establecida**: Cada MaxScale conectado a todas las redes vía VRouter
**Replicación funcionando**: Todos los servidores sincronizados con GTID
**Listo para**: Configuración de iptables en VRouter para control de tráfico