# 01 - Simulación Básica de Temporal

## Descripción

**SIMULACIÓN COMPLETA** - No instala ni configura nada real.

Este ensayo demuestra cómo Temporal orquesta un workflow de despliegue de red simulando:
- Provisioning de infraestructura (Semaphore/Ansible simulado)
- Despliegue de software (Airflow simulado)  
- Validación end-to-end
- Rollback automático

## Archivos

| Archivo | Propósito |
|---------|-----------|
| `models.py` | Define `NetworkDeploymentRequest` |
| `workflows.py` | `NetworkDeploymentWorkflow` - orquestación |
| `activities.py` | Activities individuales (provision, deploy, validate, cleanup) |
| `run_worker.py` | Worker de Temporal |
| `run_deployment.py` | Cliente que lanza workflows |

## Ejecución

### Prerequisitos:
```bash
# Temporal Server corriendo
temporal server start-dev --db-filename temporal_DB.db

# Virtual environment
cd 01-basic-simulation
env\Scripts\activate
pip install -r requirements.txt
```

### Ejecutar:
```bash
# Terminal 1: Worker
python run_worker.py

# Terminal 2: Lanzar workflow  
python run_deployment.py
```

## Resultados Esperados

### Consola:
```
Starting deployment for router: router-lab-002
IP: 192.168.100.11
Software: IOS-XE-17.3.4
Deployment completed: Router router-lab-002 deployed successfully...
```

### Temporal Web UI (localhost:8233):
- Workflow completado exitosamente
- 3 activities ejecutadas (provision → deploy → validate)
- Timeline completo visible

## Qué simula

✅ **Solo simulación con:**
- `asyncio.sleep()` para tiempos de ejecución
- Strings de retorno simulando resultados
- Logs en Temporal Web UI

❌ **NO hace:**
- No crea archivos reales
- No conecta APIs externas
- No configura dispositivos
- No instala software

## Próximo paso

Ver `../02-airflow-integration/` para integración real con Airflow.