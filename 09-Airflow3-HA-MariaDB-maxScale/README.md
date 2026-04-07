# MaxScale HA con Failover Automático

## Arquitectura Simple

- **2 MaxScale nodes**: Ambos con failover automático habilitado
- **3 MariaDB nodes**: HORNOS (master), SANLORENZO (replica), TUCUMAN (arbitrator)
- **Cooperative locking**: Evita split-brain entre MaxScale nodes

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

### Iniciar
```bash
docker-compose up -d
```

### Verificar estado
```bash
# MaxScale 1
docker exec maxscale-hornos maxctrl list servers

# MaxScale 2 (puerto diferente)
docker exec maxscale-sanlorenzo maxctrl --hosts=127.0.0.1:8990 list servers
```

### Probar failover
```bash
# Simular falla
docker stop mariadb-hornos

# Verificar promoción (esperar ~10 segundos)
docker exec maxscale-hornos maxctrl list servers

# Restaurar
docker start mariadb-hornos
```

## Puertos

- **MaxScale HORNOS**: 4006 (service), 8989 (admin)
- **MaxScale SANLORENZO**: 4007 (service), 8990 (admin)
- **MariaDB**: 3306, 3307, 3308

## Conexión desde Airflow

Airflow se conecta a `maxscale-hornos:4006` y MaxScale maneja automáticamente el routing al master actual.

## Solución a Problemas Comunes

### Problema: Slaves no se detectan correctamente
**Causa**: Falta configuración `--read-only=ON` en docker-compose
**Solución**: Ya corregido en mariadb-sanlorenzo y mariadb-tucuman

### Problema: Replicación se rompe al reiniciar
**Causa**: Scripts de init.sql no configuran read_only
**Solución**: Ya corregido con `SET GLOBAL read_only = 1;` en scripts