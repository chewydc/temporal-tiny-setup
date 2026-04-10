# Airflow to Temporal MCP Server

MCP Server para migración automatizada de DAGs de Airflow a Workflows de Temporal.

## 🎯 ¿Qué es esto?

Una herramienta que convierte DAGs de Airflow en Workflows de Temporal automáticamente, aplicando las reglas de tu plataforma.

**Antes (manual):**
- Leer DAG línea por línea
- Identificar qué Activities usar
- Escribir código a mano
- ⏱️ 4-6 horas por DAG

**Después (con esta herramienta):**
- Analiza DAG automáticamente
- Detecta Activities centralizadas
- Genera código alineado con tu plataforma
- ⏱️ 5 minutos

## 🚀 Formas de Uso

### Opción 1: Con AI Assistant (Recomendado)

Usa el MCP con cualquier AI que soporte MCP:

**Clientes compatibles:**
- **Kiro** - IDE con AI integrado
- **Claude Desktop** - App de escritorio de Anthropic
- **Cline** - Extensión para VSCode (experimental)

**Ejemplo de uso:**
```
Tú: "Analiza este DAG de Airflow"
[Adjuntas router_config.py]

AI: "Tu DAG tiene 4 tasks:
✅ 3 pueden usar Activities del SDK
⚠️ 1 requiere Activity personalizada
💡 Recomiendo fase HYBRID"

Tú: "Genera el código en fase wrapper"

AI: [Genera workflows.py, activities.py, run_worker.py]
```

### Opción 2: Como Librería Python

Usa directamente en tus scripts:

```python
from airflow_to_temporal_mcp.parsers import DagParser
from airflow_to_temporal_mcp.generators import WorkflowGenerator
from airflow_to_temporal_mcp.rules import PlatformRules

# Leer DAG
with open("router_config.py") as f:
    dag_content = f.read()

# Procesar
rules = PlatformRules("config/platform_config.yaml")
parser = DagParser(rules)
dag_info = parser.parse(dag_content)

# Generar
generator = WorkflowGenerator(rules)
workflow_code = generator.generate(dag_info, phase="wrapper")

# Guardar
with open("workflows.py", "w") as f:
    f.write(workflow_code)
```

### Opción 3: CLI (Próximamente)

```bash
# Migrar DAG
python -m airflow_to_temporal_mcp migrate router_config.py --phase wrapper

# Solo analizar
python -m airflow_to_temporal_mcp analyze router_config.py
```

## 📦 Instalación

### 1. Clonar e Instalar

```bash
git clone https://github.com/tu-org/airflow-to-temporal-mcp.git
cd airflow-to-temporal-mcp
pip install -e .
```

### 2. Configurar (Si usas con AI)

#### Para Kiro

Editar `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "airflow-to-temporal": {
      "command": "python",
      "args": ["-m", "airflow_to_temporal_mcp"],
      "env": {
        "PLATFORM_CONFIG": "./airflow-to-temporal-mcp/config/platform_config.yaml"
      }
    }
  }
}
```

Reconectar: `Ctrl+Shift+P` → `MCP: Reconnect All Servers`

#### Para Claude Desktop

Editar `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac) o `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "airflow-to-temporal": {
      "command": "python",
      "args": ["-m", "airflow_to_temporal_mcp"],
      "env": {
        "PLATFORM_CONFIG": "/ruta/completa/a/platform_config.yaml"
      }
    }
  }
}
```

Reiniciar Claude Desktop.

#### Para Cline (VSCode)

Instalar extensión Cline y configurar MCP servers en settings.

### 3. Probar

**Con AI:**
```
"Analiza este DAG"
[Adjuntar: examples/sample_dag.py]
```

**Con Python:**
```python
python examples/migrate_example.py
```

## 💡 ¿Cómo Funciona?

### El MCP Sabe Qué NO Generar

Lee `config/platform_config.yaml`:

```yaml
centralized_activities:
  - name: "deploy_router"
    module: "platform_sdk.infrastructure"
    triggers: ["ansible", "router", "deploy"]
```

Cuando analiza un DAG:

```python
# DAG de Airflow
deploy = BashOperator(
    bash_command='ansible-playbook deploy_router.yml'
)

# MCP detecta "ansible" → usa Activity centralizada
# Genera: from platform_sdk.infrastructure import deploy_router
# NO genera código nuevo
```

### Fases de Migración

**Fase 1: Wrapper** (Recomendado para empezar)
```
Frontend → Temporal → Airflow (DAG completo)
```
- DAG se ejecuta desde Temporal
- Temporal controla estado y reintentos
- Cambio mínimo, validas que funciona

**Fase 2: Hybrid**
```
Frontend → Temporal → [Activities nativas + Airflow]
```
- Migras tasks uno por uno
- Coexistencia controlada

**Fase 3: Native**
```
Frontend → Temporal → Activities nativas
```
- 100% Temporal
- Airflow deprecado

## 📖 Uso con AI

### Analizar un DAG

```
Tú: "Analiza este DAG"
[Adjuntas router_config.py]

AI: "Tu DAG tiene 4 tasks:
✅ 3 pueden usar Activities del SDK
⚠️ 1 requiere Activity personalizada
💡 Recomiendo fase HYBRID"
```

### Generar Código

```
Tú: "Genera el código en fase wrapper"

AI: [Genera 4 archivos]
"Listo! ¿Dónde los guardo?"

Tú: "En ./workflows/router_config/"
```

### Comandos Útiles

```bash
# Solo analizar (sin generar)
"Analiza este DAG sin generar código"

# Generar en fase específica
"Genera en fase wrapper"
"Genera en fase hybrid"
"Genera en fase native"

# Validar código generado
"Valida este workflow"
[Adjuntas workflows.py]
```

## 📖 Uso como Librería

### Ejemplo Completo

```python
from airflow_to_temporal_mcp.parsers import DagParser
from airflow_to_temporal_mcp.generators import (
    WorkflowGenerator,
    ActivityGenerator,
    WorkerGenerator
)
from airflow_to_temporal_mcp.rules import PlatformRules

# Configuración
rules = PlatformRules("config/platform_config.yaml")

# Leer DAG
with open("router_config.py") as f:
    dag_content = f.read()

# Parsear
parser = DagParser(rules)
dag_info = parser.parse(dag_content)

print(f"DAG: {dag_info.dag_id}")
print(f"Tasks: {len(dag_info.tasks)}")

# Generar Workflow
workflow_gen = WorkflowGenerator(rules)
workflow_code = workflow_gen.generate(
    dag_info=dag_info,
    migration_phase="wrapper",
    tenant="network-team",
    namespace="default"
)

# Generar Activities
activity_gen = ActivityGenerator(rules)
activities_code = activity_gen.generate(
    dag_info=dag_info,
    migration_phase="wrapper"
)

# Generar Worker
worker_gen = WorkerGenerator(rules)
worker_code = worker_gen.generate(
    workflow_name=dag_info.dag_id,
    activities=[task.task_id for task in dag_info.tasks],
    tenant="network-team"
)

# Guardar archivos
with open("workflows.py", "w") as f:
    f.write(workflow_code)

with open("activities.py", "w") as f:
    f.write(activities_code)

with open("run_worker.py", "w") as f:
    f.write(worker_code)

print("✅ Archivos generados!")
```

### Integración en CI/CD

```python
# migrate_dags.py
import sys
from pathlib import Path
from airflow_to_temporal_mcp.parsers import DagParser
from airflow_to_temporal_mcp.generators import WorkflowGenerator
from airflow_to_temporal_mcp.rules import PlatformRules

def migrate_dag(dag_file: Path, output_dir: Path):
    rules = PlatformRules("config/platform_config.yaml")
    
    with open(dag_file) as f:
        dag_content = f.read()
    
    parser = DagParser(rules)
    dag_info = parser.parse(dag_content)
    
    generator = WorkflowGenerator(rules)
    workflow_code = generator.generate(dag_info, phase="wrapper")
    
    output_file = output_dir / f"{dag_info.dag_id}_workflow.py"
    with open(output_file, "w") as f:
        f.write(workflow_code)
    
    print(f"✅ Migrated: {dag_file} → {output_file}")

if __name__ == "__main__":
    dag_file = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    migrate_dag(dag_file, output_dir)
```

```bash
# En tu pipeline
python migrate_dags.py dags/router_config.py output/
```

## ⚙️ Personalización

### Agregar tus Activities

Editar `config/platform_config.yaml`:

```yaml
centralized_activities:
  # Agregar la tuya
  - name: "mi_activity"
    module: "mi_sdk.mi_modulo"
    function: "mi_activity"
    triggers: ["mi_keyword", "otro_keyword"]
    parameters:
      - name: "param1"
        type: "str"
        required: true
```

**Si usas con AI:** Reconectar MCP server  
**Si usas como librería:** Recargar PlatformRules

### Configurar tu SDK

```yaml
platform:
  sdk:
    package: "tu_empresa_sdk"
    version: ">=2.0.0"
    repository: "https://nexus.tu-empresa.com/pypi/tu-sdk"
```

## 🔧 Troubleshooting

### MCP no aparece en el AI

**Para Kiro/Claude Desktop:**

```bash
# 1. Verificar instalación
python -c "import airflow_to_temporal_mcp; print('OK')"

# 2. Ver logs del AI
# Kiro: View → Output → "MCP Servers"
# Claude: Ver logs en la app

# 3. Verificar config
cat ~/.kiro/settings/mcp.json  # Kiro
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json  # Claude
```

### Error: "Config file not found"

Usar ruta absoluta:

```json
{
  "env": {
    "PLATFORM_CONFIG": "/ruta/completa/a/platform_config.yaml"
  }
}
```

### AI no usa el MCP automáticamente

Ser más explícito:

```
❌ "Analiza este archivo"
✅ "Usa airflow-to-temporal para analizar este DAG"
```

## 📦 Distribución a tu Equipo

### Opción 1: Git (Recomendado)

```bash
# Subir a Git interno
git remote add origin https://git.empresa.com/platform/mcp.git
git push

# Equipo clona e instala
git clone https://git.empresa.com/platform/mcp.git
cd mcp
pip install -e .
```

### Opción 2: PyPI Interno

```bash
# Publicar
python -m build
twine upload --repository-url https://pypi.empresa.com dist/*

# Equipo instala
pip install --index-url https://pypi.empresa.com airflow-to-temporal-mcp
```

### Opción 3: Script de Instalación

```bash
# install.sh
#!/bin/bash
git clone https://git.empresa.com/platform/mcp.git
cd mcp
pip install -e .
echo "✅ Instalado! Configura tu AI client y reconecta MCP"
```

## 🏗️ Arquitectura

Ver [ARCHITECTURE.md](ARCHITECTURE.md) para detalles de:
- Integración con planos de arquitectura
- Modelo de Co-Living
- Flujo completo de migración
- Separación de responsabilidades

## 📊 Estructura del Proyecto

```
airflow-to-temporal-mcp/
├── README.md                    # Este archivo
├── ARCHITECTURE.md              # Arquitectura detallada
│
├── config/
│   └── platform_config.yaml     # Reglas de plataforma
│
├── src/airflow_to_temporal_mcp/
│   ├── server.py                # MCP server (6 tools)
│   ├── parsers/                 # Parser de DAGs (AST)
│   ├── generators/              # Generadores de código
│   └── rules/                   # Reglas configurables
│
├── examples/
│   ├── sample_dag.py            # DAG de ejemplo
│   └── migrate_example.py       # Demo
│
└── pyproject.toml
```

## ❓ FAQ

### ¿Con qué AI funciona?

Cualquier cliente que soporte MCP:
- ✅ Kiro
- ✅ Claude Desktop
- ✅ Cline (VSCode)
- ✅ Cualquier cliente MCP compatible

### ¿Puedo usarlo sin AI?

**Sí**, como librería Python en tus scripts.

### ¿Necesita internet?

**No.** Corre 100% local en tu máquina.

### ¿Modifica mis DAGs originales?

**No.** Solo lee y genera código nuevo.

### ¿Puedo editar el código generado?

**Sí, debes hacerlo.** El MCP genera código base, tú completas la lógica específica.

### ¿Qué pasa con DAGs complejos?

Soporta la mayoría de operators. Para casos no soportados, genera código base con TODOs.

### ¿Cuánto tiempo toma migrar?

- Análisis: 1-2 min
- Generación: 2-3 min
- Revisión: 15-30 min
- Testing: 30-60 min
**Total: 1-2 horas** (vs 4-6 horas manual)

### ¿Cómo actualizo el MCP?

```bash
cd airflow-to-temporal-mcp
git pull
pip install -e . --upgrade
# Si usas con AI: Reconectar MCP server
```

## 🎯 Ejemplo Completo

### DAG de Entrada

```python
# router_config.py
from airflow import DAG
from airflow.operators.bash import BashOperator

dag = DAG('router_config', ...)

deploy = BashOperator(
    task_id='deploy_router',
    bash_command='ansible-playbook deploy_router.yml'
)

configure = BashOperator(
    task_id='configure_firewall',
    bash_command='iptables -A FORWARD -p tcp --dport 80 -j ACCEPT'
)

deploy >> configure
```

### Código Generado

**workflows.py**
```python
from temporalio import workflow
from datetime import timedelta

@workflow.defn
class RouterConfigWorkflow:
    @workflow.run
    async def run(self, request: dict) -> dict:
        # Fase wrapper: ejecuta DAG en Airflow
        result = await workflow.execute_activity(
            "trigger_airflow_dag",
            {"dag_id": "router_config", "conf": request},
            start_to_close_timeout=timedelta(minutes=30)
        )
        return result
```

**activities.py**
```python
from temporalio import activity
from platform_sdk.infrastructure import deploy_router  # ← Centralizada
from platform_sdk.network import configure_firewall    # ← Centralizada

# Wrapper para Airflow (fase transición)
@activity.defn
async def trigger_airflow_dag(params: dict) -> dict:
    # Implementación del adapter
    ...
```

## 🤝 Contribuir

1. Fork del repositorio
2. Crear branch: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -m 'feat: agregar funcionalidad'`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Abrir Pull Request

## 📄 Licencia

[Tu licencia]

## 📞 Soporte

- **Issues**: [Link a tu repo]
- **Slack/Teams**: [Canal de soporte]
- **Email**: platform-team@tu-empresa.com

---

**Versión**: 0.1.0  
**Mantenido por**: Platform Team
