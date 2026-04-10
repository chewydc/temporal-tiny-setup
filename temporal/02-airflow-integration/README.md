# 02 - Integración Real con Airflow

## Descripción

**INTEGRACIÓN HÍBRIDA** - Airflow real + Semaphore simulado.

Este ensayo demuestra:
- ✅ **Provisioning simulado** (Semaphore - próximo paso)
- ✅ **Despliegue REAL con Airflow** (API + DAGs reales)
- ✅ **Validación simulada**
- ✅ **Fallback automático** si Airflow no está disponible

## Diferencias vs 01-basic-simulation

| Aspecto | 01-basic | 02-airflow |
|---------|----------|------------|
| **Provisioning** | Simulado | Simulado |
| **Software Deploy** | Simulado | **REAL Airflow API** |
| **Validación** | Simulado | Simulado |
| **Fallback** | No | **Sí (automático)** |

## Archivos Nuevos/Modificados

| Archivo | Cambios |
|---------|----------|
| `activities.py` | ✅ Integración real con Airflow API |
| `docker-compose.yml` | ✅ Airflow + Scheduler |
| `requirements.txt` | ✅ + apache-airflow-client |
| `../airflow_dags/temporal_network_deployment.py` | ✅ DAG real para Temporal |

## Setup y Ejecución

### 1. Prerequisitos:
```bash
# Temporal Server
temporal server start-dev --db-filename temporal_DB.db

# Virtual environment
cd 02-airflow-integration
env\Scripts\activate
pip install -r requirements.txt
```

### 2. Levantar Airflow:
```bash
# En 02-airflow-integration/
docker-compose up -d

# Verificar que esté corriendo
docker-compose ps
```

### 3. Verificar Airflow UI:
- URL: http://localhost:8080
- Usuario: admin
- Password: admin
- Buscar DAG: `temporal_network_deployment`

### 4. Ejecutar Workflow:
```bash
# Terminal 1: Worker
python run_worker.py

# Terminal 2: Lanzar workflow
python run_deployment.py
```

## Qué verás

### En Temporal Web UI:
- Workflow ejecutándose normalmente
- Activity `deploy_router_software` tarda más (llama Airflow real)

### En Airflow Web UI:
- DAG `network_software_deployment` se ejecuta automáticamente
- Puedes ver logs detallados de cada tarea
- Timeline de ejecución real

### En Consola del Worker:
```
[SIMULADO] Provisioning router router-lab-001
[REAL AIRFLOW] Deploying software to router-lab-001
Triggering Airflow DAG: http://localhost:8080/api/v1/dags/network_software_deployment/dagRuns
DAG triggered successfully: temporal-router-lab-001-20260105-210800
DAG temporal-router-lab-001-20260105-210800 state: running
DAG temporal-router-lab-001-20260105-210800 completed successfully
```

## Fallback Automático

Si Airflow no está disponible:
```
Airflow integration failed: Connection refused
Falling back to simulation...
[FALLBACK SIMULATION] Software IOS-XE-17.3.4 deployed on router-lab-001
```

## Próximo Paso

Ver `../03-semaphore-integration/` para agregar Semaphore real.