# Airflow 3 HA PoC - MariaDB + MaxScale

## Descripción
Prueba de concepto de **Airflow 3.x** en alta disponibilidad con:
- Airflow API Server (UI + API REST)
- Airflow Scheduler
- 2 Airflow Workers (CeleryExecutor)
- MariaDB Primary + Replica (replicación GTID)
- MaxScale (proxy con read/write split y failover automático)
- Redis (broker para Celery)

> **Nota**: Airflow 3.x reemplazó `webserver` por `api-server` y usa `SimpleAuthManager` por defecto (sin autenticación).

## Inicio Rápido

### 1. Copiar archivos de configuración
```cmd
copy airflow.cfg.example airflow.cfg
copy .env.example .env
```
> `start.bat` los copia automáticamente si no existen.

### 2. Iniciar el stack completo
```cmd
start.bat
```

### 3. Verificar estado
```cmd
status.bat
```

### 4. Limpiar y reiniciar
```cmd
clean.bat
start.bat
```

### 5. Accesos
- **Airflow Web UI**: http://localhost:8080 (sin autenticación - acceso directo como admin)
- **MaxScale GUI**: http://localhost:8989

## Comandos Útiles

### Ver logs en tiempo real
```cmd
docker compose logs -f airflow-apiserver
docker compose logs -f airflow-scheduler
docker compose logs -f maxscale
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
│        Airflow API Server           │
│       (UI + API REST)               │
│          (port 8080)                │
└─────────────────────────────────────┘
                    │
       ┌────────────┼────────────┐
       │            │            │
┌─────────────┐ ┌───────────┐ ┌─────────────┐
│  Scheduler  │ │  Worker-1 │ │  Worker-2   │
└─────────────┘ └───────────┘ └─────────────┘
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

### Autenticación
- Airflow 3.x usa `SimpleAuthManager` por defecto
- Configurado con `simple_auth_manager_all_admins = True` en `airflow.cfg`
- Acceso directo al UI como admin sin credenciales

## Archivos del Proyecto

### Esenciales
- `docker-compose.yml` - Configuración principal del stack
- `airflow.cfg.example` - Configuración de Airflow 3 (copiar a `airflow.cfg`)
- `.env.example` - Variables de entorno (copiar a `.env`)
- `start.bat` - Script de inicio (copia los .example automáticamente)
- `status.bat` - Script de monitoreo
- `clean.bat` - Script de limpieza

### Configuraciones
- `mariadb/primary/init.sql` - Inicialización MariaDB Primary
- `mariadb/replica/init.sql` - Inicialización MariaDB Replica
- `maxscale/maxscale_minimal.cnf` - Configuración MaxScale

### DAGs de Prueba
- `dags/test_ha_dag.py` - DAG de validación HA
- `dags/failover_stress_test.py` - DAG para pruebas de failover
- `dags/simple_failover_test.py` - DAG de failover simplificado

## Notas Airflow 3.x
- `airflow webserver` fue reemplazado por `airflow api-server`
- `airflow standalone` levanta todo junto (api-server + scheduler + triggerer) pero no permite deshabilitar auth fácilmente
- El auth manager por defecto es `SimpleAuthManager` (no requiere instalar providers adicionales)
