# Airflow 3 HA PoC - MariaDB + MaxScale

## Descripción
Prueba de concepto de Airflow 3 en alta disponibilidad con:
- Airflow Standalone (webserver + scheduler + triggerer integrados)
- 2 Airflow Workers adicionales (CeleryExecutor)
- MariaDB Primary + Replica (replicación GTID)
- MaxScale (proxy con read/write split y failover automático)
- Redis (broker para Celery)

## Inicio Rápido

### 1. Iniciar el stack completo
```cmd
start.bat
```

### 2. Verificar estado
```cmd
status.bat
```

### 3. Limpiar y reiniciar
```cmd
clean.bat
start.bat
```

### 4. Accesos
- **Airflow Web UI**: http://localhost:8080 (sin autenticación - acceso directo)
- **MaxScale GUI**: http://localhost:8989

## Comandos Útiles

### Ver logs en tiempo real
```cmd
docker-compose logs -f airflow-standalone
docker-compose logs -f maxscale
```

### Verificar estado de MaxScale
```cmd
docker exec maxscale maxctrl list servers
docker exec maxscale maxctrl show server mariadb-primary
```

### Conectar a MariaDB directamente
```cmd
# Primary
docker exec -it mariadb-primary mysql -u airflow -pairflow_pass airflow

# Replica  
docker exec -it mariadb-replica mysql -u airflow -pairflow_pass airflow
```

## Arquitectura

```
┌─────────────────────────────────────┐
│        Airflow Standalone           │
│  (webserver + scheduler + triggerer)│
│            (port 8080)              │
└─────────────────────────────────────┘
                    │
       ┌────────────┼────────────┐
       │            │            │
┌─────────────┐     │     ┌─────────────┐
│   Worker-1  │     │     │   Worker-2  │
│             │     │     │             │
└─────────────┘     │     └─────────────┘
                    │
          ┌─────────────────┐
          │    MaxScale     │
          │   (port 4006)   │
          │  Read/Write     │
          │     Split       │
          └─────────────────┘
                   │
      ┌────────────┴────────────┐
      │                         │
┌───────────────┐         ┌───────────────┐
│   MariaDB     │         │   MariaDB     │
│   Primary     │────────▶│   Replica     │
│               │         │   (read-only) │
└───────────────┘         └───────────────┘
```

## Configuración de HA

### Failover Automático
- MaxScale detecta fallas en el primary automáticamente
- Promueve la replica a primary sin intervención manual
- Airflow continúa operando transparentemente

### Workers Escalables
- 2 workers por defecto
- Escalable agregando más servicios worker en docker-compose.yml
- Balanceo de carga automático vía Celery/Redis

## Archivos del Proyecto

### Esenciales
- `docker-compose.yml` - Configuración principal del stack
- `airflow.cfg` - Configuración de Airflow 3
- `.env` - Variables de entorno
- `start.bat` - Script de inicio
- `status.bat` - Script de monitoreo
- `clean.bat` - Script de limpieza

### Configuraciones
- `mariadb/primary/init.sql` - Inicialización MariaDB Primary
- `mariadb/replica/init.sql` - Inicialización MariaDB Replica  
- `maxscale/maxscale_minimal.cnf` - Configuración MaxScale

### DAGs de Prueba
- `dags/test_ha_dag.py` - DAG de prueba básico
- `dags/failover_stress_test.py` - DAG para pruebas de failover