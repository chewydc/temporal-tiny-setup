# 03 - Integración Ansible Runner: Router Virtual Real

## 🎯 Objetivo
Temporal orquesta **Ansible Runner** (despliegue real de router) + **Airflow** (configuración software)

## 🏗️ Arquitectura
```
┌─ TEMPORAL (Orquestador) ──────────────────────┐
│                                               │
│  ┌─ Activity 1 ─┐  ┌─ Activity 2 ─┐          │
│  │ Ansible      │  │ Airflow      │          │
│  │ Runner       │  │ Configure    │          │
│  │ Deploy       │  │ Software     │          │
│  └──────────────┘  └──────────────┘          │
│         │                  │                 │
│         ▼                  ▼                 │
│  🔧 Router Real     📡 DAG Real              │
└───────────────────────────────────────────────┘
```

## 📋 Componentes Reales

### 1. Ansible Runner (Contenedor Docker)
- **Función**: Ejecuta playbooks Ansible directamente
- **Playbook**: `deploy_router.yml`
- **Resultado**: Container router corriendo

### 2. Router Virtual
- **Imagen**: `frrouting/frr:latest` (open source, compatible Cisco)
- **Configuración**: Interfaces, routing, OSPF
- **Verificación**: Router responde a ping

### 3. Airflow (Configuración REAL)
- **Función**: Configura rutas estáticas REALES en router FRR
- **DAG**: `temporal_network_deployment`
- **Resultado**: Router configurado con rutas reales

## 🚀 Flujo Completo
1. **Temporal** → **Ansible Runner**: Despliega router container
2. **Temporal** → **Airflow**: Configura software router  
3. **Temporal** → **Validación**: Verifica que router funciona

## 🔧 Setup
```bash
# 1. Levantar Ansible Runner + Airflow
docker-compose up -d

# 2. Temporal worker
python run_worker.py

# 3. Ejecutar workflow
python run_deployment.py
```

## ✅ Verificación Real
- ✅ Container router creado por Ansible Runner
- ✅ Router FRR responde a ping
- ✅ Airflow DAG configura rutas estáticas REALES
- ✅ Tabla de rutas aplicada en router FRR