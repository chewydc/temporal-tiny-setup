# Temporal + Ansible + Airflow Integration Examples

Este repositorio contiene ejemplos progresivos de integración entre **Temporal**, **Ansible** y **Airflow** para automatización de infraestructura de red.

## 📁 Estructura del Proyecto

```
Tiny-Setup/
├── 01-basic-simulation/          # Simulación básica con Temporal
├── 02-airflow-integration/       # Temporal + Airflow
├── 03-ansible-integration/       # Temporal + Ansible + Airflow
├── 04-complete-integration/      # Demo completa con firewall
├── 05-multitenant/               # Arquitectura multitenant
├── 06-life-cycle-example/        # Ciclo de vida con Kubernetes
├── 07-airflow-to-temporal-mcp-example/  # MCP Server para migración Airflow→Temporal
├── 08-Airflow3-MaxScale-MariaDB/         # Airflow 3 HA con MariaDB + MaxScale
├── 09-Airflow3-HA-Galera-MariaDB/        # Airflow 3 HA con Galera Cluster (3 regiones)
└── README.md                     # Este archivo
```

## 🎯 Casos de Uso

### [Caso 01: Simulación Básica](./01-basic-simulation/)
- **Tecnologías**: Temporal
- **Objetivo**: Simulación de despliegue de routers virtuales
- **Qué hace**: Simula el despliegue de 3 routers con archivos JSON, demuestra workflows básicos de Temporal con activities, manejo de errores y reportes. No usa infraestructura real.
- **Características**: Activities, workflows, modelos de datos

### [Caso 02: Integración con Airflow](./02-airflow-integration/)
- **Tecnologías**: Temporal + Airflow
- **Objetivo**: Orquestación de DAGs desde workflows de Temporal
- **Qué hace**: Temporal ejecuta un workflow que dispara un DAG de Airflow via API REST. El DAG simula configuración de software en routers. Demuestra comunicación entre herramientas.
- **Características**: Trigger de DAGs, manejo de estados, fallbacks

### [Caso 03: Integración con Ansible](./03-ansible-integration/)
- **Tecnologías**: Temporal + Ansible + Airflow
- **Objetivo**: Despliegue real de infraestructura con Docker
- **Qué hace**: Ansible despliega un router FRR real en Docker, Temporal orquesta el proceso, Airflow configura rutas estáticas. Primera implementación con infraestructura real.
- **Características**: Ansible Runner, playbooks, configuración de rutas

### [Caso 04: Demo Completa](./04-complete-integration/)
- **Tecnologías**: Temporal + Ansible + Airflow + Docker Networks
- **Objetivo**: Conectividad cliente-servidor con firewall selectivo
- **Qué hace**: Demuestra un problema real: cliente y servidor aislados. Ansible despliega router con firewall (PING ✅, HTTP ❌). Temporal pausa con Signal desde Web UI. Airflow habilita HTTP. Resultado: conectividad completa.
- **Características**: Temporal Signals, firewall iptables, tests de conectividad

### [Caso 05: Arquitectura Multitenant](./05-multitenant/)
- **Tecnologías**: Temporal
- **Objetivo**: Arquitectura multitenant escalable con namespaces separados
- **Qué hace**: Demuestra cómo múltiples clientes (chogar, amovil, afijo) tienen aislamiento COMPLETO usando namespaces. Cada tenant tiene su propio namespace y solo ve sus workflows en Temporal UI. Aislamiento real de datos.
- **Características**: Namespaces por tenant, aislamiento completo, escalabilidad horizontal, seguridad

### [Caso 07: MCP Server para Migración Airflow→Temporal](./07-airflow-to-temporal-mcp-example/)
- **Tecnologías**: Model Context Protocol (MCP)
- **Objetivo**: Herramienta de migración automática de DAGs de Airflow a Workflows de Temporal
- **Qué hace**: MCP Server que analiza DAGs de Airflow y genera automáticamente código de Temporal equivalente (workflows, activities, workers). Facilita la migración masiva de procesos existentes.
- **Características**: Análisis de DAGs, generación de código, patrones de migración, SDK público/privado

### [Caso 08: Airflow 3 HA con MariaDB + MaxScale](08-Airflow3-MaxScale-MariaDB/)
- **Tecnologías**: Airflow 3.x, MariaDB, MaxScale, Redis, Celery
- **Objetivo**: PoC de Airflow 3 en alta disponibilidad con base de datos replicada y failover automático
- **Qué hace**: Despliega Airflow 3.x con API Server, Scheduler y 2 Workers usando CeleryExecutor. MariaDB Primary/Replica con replicación GTID y MaxScale como proxy con read/write split y failover automático.
- **Características**: HA con failover automático, read/write split, workers escalables, sin autenticación (SimpleAuthManager)

### [Caso 09: Airflow 3 HA con Galera Cluster (3 Regiones)](09-Airflow3-HA-MariaDB-maxScale/)
- **Tecnologías**: Airflow 3.x, MariaDB Galera Cluster, Redis, Celery
- **Objetivo**: PoC de Airflow 3 en alta disponibilidad con Galera Cluster puro distribuido en 3 regiones geográficas
- **Qué hace**: Despliega Airflow 3.x HA en 2 regiones (Hornos/SanLorenzo) con Galera Cluster de 3 nodos (2 datos + 1 arbitrator en Tucumán). Simula fallos de conectividad entre regiones para probar failover automático sin MaxScale.
- **Características**: Galera multi-master, quorum automático, 3 redes separadas, control de conectividad, failover transparente

## 🚀 Inicio Rápido

### Prerequisitos
- Docker Desktop
- Python 3.8+
- Temporal Server (localhost:7233)

### Ejecutar un Caso
```bash
# Navegar al caso deseado
cd 04-complete-integration/

# Levantar infraestructura
docker-compose up -d

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar worker
python run_worker.py

# En otra terminal: ejecutar workflow
python run_deployment.py
```

## 🎯 Valor Demostrado

Cada caso demuestra:

1. **Separación de Responsabilidades**:
   - **Temporal**: Orquestación y coordinación
   - **Ansible**: Despliegue de infraestructura
   - **Airflow**: Configuración especializada

2. **Escalabilidad**: De simulación básica a infraestructura real

3. **Observabilidad**: Logs detallados y estados visibles

4. **Reproducibilidad**: Workflows determinísticos y repetibles

5. **Integración Real**: Herramientas trabajando juntas, no aisladas

## 📚 Documentación

Cada carpeta contiene su propio README.md con:
- Instrucciones específicas
- Arquitectura del caso
- Comandos de verificación
- Troubleshooting

## 🔧 Configuración del Repositorio

- **Independiente**: Cada caso es autocontenido
- **Sin dependencias externas**: No requiere archivos de otras carpetas
- **Gitignore**: Excluye `env/`, `logs/`, `Backup/`
- **Docker**: Toda la infraestructura en containers

## 🤝 Contribución

Cada caso puede ejecutarse independientemente. Para agregar nuevos casos:

1. Crear nueva carpeta -nuevo-caso/`
2. Incluir todos los archivos necesarios
3. Agregar README.md específico
4. Actualizar este README principal