# Caso 04: Conectividad Cliente-Servidor con Temporal + Ansible + Airflow

## 🎯 Objetivo

Demostrar cómo **Temporal + Ansible + Airflow** puede resolver problemas de conectividad de red desplegando automáticamente un router virtual con firewall selectivo.

## 🏗️ Escenario del Problema

```
ESTADO 1 (Sin conectividad):
┌─────────────────┐    ❌    ┌─────────────────┐
│   Cliente       │          │    Servidor     │
│ 192.168.100.10  │    NO    │ 192.168.200.10  │
│                 │ CONECTA  │                 │
└─────────────────┘          └─────────────────┘
     Red Aislada                  Red Aislada

ESTADO 2 (Post-Ansible: PING OK, HTTP BLOQUEADO):
┌─────────────────┐  ✅🚫   ┌─────────────────┐
│   Cliente       │ ←──────→ │    Servidor     │
│ 192.168.100.10  │ PING OK  │ 192.168.200.10  │
│                 │ HTTP NO  │                 │
└─────────────────┘          └─────────────────┘
        ↑                            ↑
        └── Router + Firewall ───────┘
           (Solo permite ICMP)

ESTADO 3 (Post-Airflow: PING + HTTP OK):
┌─────────────────┐   ✅✅  ┌─────────────────┐
│   Cliente       │ ←──────→ │    Servidor     │
│ 192.168.100.10  │ PING+HTTP│ 192.168.200.10  │
│                 │    OK    │                 │
└─────────────────┘          └─────────────────┘
        ↑                            ↑
        └── Router + Firewall ───────┘
           (Permite ICMP + HTTP)
```

## 📦 Componentes

### 🐳 Infraestructura (Docker Compose)
- **Cliente**: Container Alpine (192.168.100.10) - Red aislada
- **Servidor**: Nginx (192.168.200.10) - Red aislada  
- **Router Virtual**: FRR con firewall desplegado por Ansible
- **Temporal**: Orquestador del workflow
- **Airflow**: Configuración de firewall para habilitar HTTP
- **Ansible Runner**: Despliegue de infraestructura

### 🔄 Workflow de Conectividad

1. **Test Inicial**: Verifica que NO hay conectividad (PING ❌, HTTP ❌)
2. **Despliegue Router**: Ansible despliega router con firewall (PING ✅, HTTP ❌)
3. **Pausa Manual**: Verificación intermedia de conectividad parcial
4. **Configurar Firewall**: Airflow habilita puerto HTTP (PING ✅, HTTP ✅)
5. **Test Final**: Verifica conectividad completa
6. **Reporte**: Genera reporte final del despliegue

## 🚀 Guía de Uso

### Prerequisitos
- Docker Desktop corriendo
- Python 3.8+
- Temporal Server corriendo en localhost:7233

### 1. Setup Automático
```bash
# Ejecutar setup (Windows)
setup_caso04.bat

# O manualmente
docker-compose up -d
```

### 2. Instalar Dependencias
```bash
python -m venv env
```
```bash
.\env\Scripts\activate
```
```bash
pip install -r requirements.txt
```

### 3. Ejecutar Demo

#### Opción A: Demo Completo con Pausa Manual
```bash
# Terminal 1: Iniciar worker
python run_worker.py

# Terminal 2: Ejecutar workflow
python run_deployment.py
```

#### 🌐 Cómo Continuar el Workflow:
1. **Después del despliegue de Ansible**, el workflow se pausará
2. **Verifica conectividad parcial**:
   ```bash
   docker exec test-client ping -c 1 -W 1 192.168.200.10     # ✅ Debe funcionar
   docker exec test-client wget -O - http://192.168.200.10 --timeout=5 --tries=1  # ❌ Debe fallar
   ```
3. **Desde Temporal Web UI** (http://localhost:8233):
   - Ve a **Workflows** → Busca tu workflow
   - Click en **"Signal"**
   - Signal Name: `enter`
   - Payload: `{}` (vacío)
   - Click **"Send Signal"**
4. **El workflow continuará** con Airflow para habilitar HTTP

### 4. Verificación Manual

#### Test de Conectividad por Etapas
```bash
# ESTADO 1: Sin router (debería fallar todo)
docker exec test-client ping -c 1 -W 1 192.168.200.10
docker exec test-client wget -q -O - http://192.168.200.10 --timeout=5 --tries=1

# ESTADO 2: Post-Ansible (PING OK, HTTP FAIL)
docker exec test-client ping -c 1 -W 1 192.168.200.10     # ✅ Funciona
docker exec test-client wget -q -O - http://192.168.200.10  --timeout=5 --tries=1 # ❌ Bloqueado

# ESTADO 3: Post-Airflow (PING + HTTP OK)
docker exec test-client ping -c 1 -W 1 192.168.200.10     # ✅ Funciona
docker exec test-client wget -q -O - http://192.168.200.10  --timeout=5 --tries=1 # ✅ Funciona
```

#### Acceso Web
- **Servidor Test**: http://localhost:8080
- **Airflow UI**: http://localhost:8081 (admin/admin)
- **Temporal UI**: Requiere instalación separada

## 🔍 Cómo Funciona

### Paso 1: Estado Inicial
- Cliente y servidor en redes separadas
- Sin router entre ellas
- **Resultado**: Sin conectividad (PING ❌, HTTP ❌)

### Paso 2: Despliegue del Router + Firewall (Ansible)
```yaml
# Ansible despliega:
- Container FRR (router virtual)
- Conecta a red cliente (192.168.100.0/24)  
- Conecta a red servidor (192.168.200.0/24)
- Configura firewall: PERMITE ICMP, BLOQUEA HTTP
- Habilita IP forwarding
```
**Resultado**: PING ✅, HTTP ❌

### Paso 3: Pausa para Verificación Manual (Temporal Signal)
- Workflow se pausa automáticamente después del despliegue de Ansible
- Usuario verifica conectividad parcial: PING ✅, HTTP ❌
- **Desde Temporal Web UI**: Envía signal `enter`
- Demuestra que Ansible proporciona conectividad básica pero Airflow es necesario

### Paso 4: Configuración de Firewall (Airflow)
```bash
# Airflow DAG configura:
- Elimina regla: iptables -D FORWARD -p tcp --dport 80 -j DROP
- Agrega regla: iptables -A FORWARD -p tcp --dport 80 -j ACCEPT
- Valida configuración del firewall
```
**Resultado**: PING ✅, HTTP ✅

### Paso 5: Resultado Final
- Router enruta tráfico entre redes
- Firewall permite ICMP y HTTP
- Cliente puede hacer ping al servidor
- Cliente puede acceder al servidor web
- **Resultado**: Conectividad completa establecida

## 📊 Resultados Esperados

### ✅ Ejecución Exitosa
```
=== RESULTADOS DE LA DEMOSTRACIÓN ===
Estado: SUCCESS
Router desplegado: SI
Firewall configurado: SI
Conectividad establecida: SI

TESTS DE CONECTIVIDAD:
   INICIAL (sin router):
      FAIL PING: 192.168.100.10 -> 192.168.200.10
      FAIL HTTP: 192.168.100.10 -> 192.168.200.10

   POST-ANSIBLE (router + firewall):
      OK PING: 192.168.100.10 -> 192.168.200.10
      FAIL HTTP: 192.168.100.10 -> 192.168.200.10 (BLOQUEADO)

   POST-AIRFLOW (firewall configurado):
      OK PING: 192.168.100.10 -> 192.168.200.10
      OK HTTP: 192.168.100.10 -> 192.168.200.10

Resumen: EXITO COMPLETO: Router vrouter-connectivity-001 
desplegado con firewall configurado y conectividad completa

DEMOSTRACION EXITOSA!
```

## 🛠️ Troubleshooting

### Problema: PING funciona pero HTTP no (después de Ansible)
```bash
# Esto es ESPERADO - Airflow debe habilitar HTTP
# Verificar reglas de firewall
docker exec vrouter-connectivity-001 iptables -L FORWARD -n

# Debe mostrar:
# ACCEPT icmp -- 0.0.0.0/0 0.0.0.0/0
# DROP tcp -- 0.0.0.0/0 0.0.0.0/0 tcp dpt:80
```

### Problema: Sin conectividad después del workflow completo
```bash
# Verificar que el router existe
docker ps | grep vrouter

# Verificar reglas de firewall finales
docker exec vrouter-connectivity-001 iptables -L FORWARD -n

# Debe mostrar:
# ACCEPT icmp -- 0.0.0.0/0 0.0.0.0/0
# ACCEPT tcp -- 0.0.0.0/0 0.0.0.0/0 tcp dpt:80
```

### Problema: Containers no inician
```bash
# Verificar Docker
docker --version
docker-compose ps

# Reiniciar
docker-compose down
docker-compose up -d
```

## 🔄 Limpieza

```bash
# Detener todo
docker-compose down

# Limpiar completamente
docker-compose down -v
docker system prune -f
```

## 📚 Archivos del Proyecto

```
04-complete-integration/
├── docker-compose.yml                    # Infraestructura completa
├── setup_caso04.bat                     # Setup automático
├── requirements.txt                     # Dependencias Python
├── models.py                           # Modelos de datos
├── workflows.py                        # Workflow Temporal
├── activities.py                       # Activities Temporal
├── run_worker.py                       # Worker Temporal
├── run_deployment.py                   # Ejecutor principal
├── monitor_workflow.py                 # ⭐ Monitor de workflows (consulta externa)
├── ansible-playbooks/
│   ├── deploy_router.yml                   # Playbook Ansible (router + firewall)
│   └── inventory.ini                       # Inventario Ansible
├── ../airflow_dags/
│   └── temporal_network_deployment.py      # DAG Airflow (configuración firewall)
└── server-content/
    └── index.html                          # Página del servidor
```

## 🔍 Monitoreo y Consulta Externa

### Monitor de Workflows (`monitor_workflow.py`)

Script para consultar el estado de workflows desde fuera, útil para:
- **Integración con IA**: Enviar info de errores a IA para diagnóstico automático
- **Sistemas de monitoreo**: Dashboards externos
- **Alertas personalizadas**: Notificaciones cuando workflows fallan

```bash
python monitor_workflow.py
```

**Funcionalidades**:
1. Consultar estado de un workflow específico
2. Listar workflows fallidos (para análisis de IA)
3. Monitorear workflow en tiempo real
4. Exportar datos para análisis de IA

### Flujo Técnico

El monitor se comunica con **Temporal Server vía gRPC** (no REST):

```
monitor_workflow.py
       │
       │ gRPC (puerto 7233)
       ▼
Temporal Server
       │
       │ SQL
       ▼
PostgreSQL/Cassandra
(historial de workflows)
```

**Llamadas API principales**:

1. **Conexión**:
```python
client = await Client.connect("localhost:7233")
# Establece conexión gRPC con Temporal Server
```

2. **Consultar estado**:
```python
handle = client.get_workflow_handle(workflow_id)
desc = await handle.describe()  # Llamada gRPC: DescribeWorkflowExecution
```

3. **Obtener resultado**:
```python
result = await handle.result()  # Llamada gRPC: GetWorkflowExecutionHistory
```

4. **Listar workflows**:
```python
async for workflow in client.list_workflows(query):
    # Llamada gRPC: ListWorkflowExecutions
    # Query SQL-like sobre índices de Temporal
```

**Ejemplo de uso con IA**:
```bash
# 1. Ejecutar monitor
python monitor_workflow.py

# 2. Seleccionar opción 4 (Export data)
# 3. Copiar el JSON generado
# 4. Enviarlo a ChatGPT/Claude:
#    "Analiza este error de workflow y sugiere solución"
```

**Caso de uso real**:
```python
# Sistema de monitoreo externo
status = await get_workflow_status("deployment-123")

if status["status"] == "FAILED":
    # Enviar a IA para diagnóstico automático
    ai_response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        json={"messages": [{"role": "user", "content": json.dumps(status)}]}
    )
```

## 🎯 Valor Demostrado

Este caso de uso demuestra:

1. **Problema Real**: Redes aisladas sin conectividad
2. **Solución Escalonada**: 
   - **Ansible**: Despliega infraestructura (router + firewall básico)
   - **Temporal**: Orquesta el workflow completo y tests de conectividad
   - **Airflow**: Configuración especializada de firewall (habilita HTTP)
3. **Validación por Etapas**: Tests automáticos verifican cada paso
4. **Demostración Clara**: Cada herramienta tiene un rol específico y necesario
5. **Reproducibilidad**: El workflow puede ejecutarse múltiples veces
6. **Observabilidad**: Logs detallados en cada paso del proceso
7. **Separación de Responsabilidades**:
   - **Ansible**: Despliegue de infraestructura y configuración básica
   - **Temporal**: Orquestación, coordinación y tests de conectividad
   - **Airflow**: Configuración avanzada de red y firewall

**Resultado**: De redes aisladas a conectividad completa en etapas, demostrando que cada herramienta (Ansible, Temporal, Airflow) es necesaria para completar la solución.