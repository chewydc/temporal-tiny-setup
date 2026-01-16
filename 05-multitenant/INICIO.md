# 05-Multitenant - Temporal

## 🚀 Ejecutar Demo

```bash
# 1. Iniciar Temporal
docker-compose up -d

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Terminal 1: Workers
python multitenant_worker.py

# 4. Terminal 2: Demo
python multitenant_demo.py

# 5. Ver workflows
http://localhost:8233
```

## 📁 Archivos

### Código
- `multitenant_worker.py` - Workers que escuchan 3 tenants
- `multitenant_demo.py` - Demo con chogar, amovil, afijo
- `simple_demo.py` - Demo simple con 1 tenant
- `workflows.py` - Workflow multitenant
- `models.py` - Modelos con tenant_id
- `activities.py` - Activities

### Documentación
- `README.md` - Guía completa
- `RESUMEN_EJECUTIVO.md` - Para compartir con el equipo
- `MULTITENANT.md` - Documentación técnica detallada

## 💡 Concepto Clave

Cada tenant tiene su **task queue dedicada**:
- `tenant-chogar-deployments`
- `tenant-amovil-deployments`
- `tenant-afijo-deployments`

Los workers escuchan todas las queues → aislamiento lógico + eficiencia.

## 🔍 Filtrar en Temporal UI

```
CustomStringField = "chogar"
```
