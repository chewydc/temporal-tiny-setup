"""
MCP Server principal para migración Airflow → Temporal
"""

import asyncio
import json
from typing import Any
from pathlib import Path

from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

from .parsers.dag_parser import DagParser
from .parsers.task_analyzer import TaskAnalyzer
from .generators.workflow_gen import WorkflowGenerator
from .generators.activity_gen import ActivityGenerator
from .generators.worker_gen import WorkerGenerator
from .rules.platform_rules import PlatformRules


# Inicializar servidor MCP
app = Server("airflow-to-temporal")

# Cargar configuración de plataforma
config_path = Path(__file__).parent.parent.parent / "config" / "platform_config.yaml"
platform_rules = PlatformRules(config_path)


@app.list_tools()
async def list_tools() -> list[Tool]:
    """Lista las herramientas disponibles del MCP"""
    return [
        Tool(
            name="analyze_dag",
            description=(
                "Analiza un DAG de Airflow y extrae información estructural: "
                "tasks, dependencias, operators, configuraciones. "
                "Retorna un análisis detallado sin generar código."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "dag_content": {
                        "type": "string",
                        "description": "Contenido completo del archivo Python del DAG"
                    },
                    "dag_file_path": {
                        "type": "string",
                        "description": "Path del archivo DAG (opcional, para contexto)"
                    }
                },
                "required": ["dag_content"]
            }
        ),
        
        Tool(
            name="generate_workflow",
            description=(
                "Genera un Workflow de Temporal a partir de un DAG de Airflow. "
                "Soporta diferentes fases de migración: wrapper, hybrid, native. "
                "Retorna el código Python del workflow generado."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "dag_content": {
                        "type": "string",
                        "description": "Contenido del DAG de Airflow"
                    },
                    "migration_phase": {
                        "type": "string",
                        "enum": ["wrapper", "hybrid", "native"],
                        "description": "Fase de migración",
                        "default": "wrapper"
                    },
                    "tenant": {
                        "type": "string",
                        "description": "Tenant/equipo propietario del workflow"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Namespace de Temporal",
                        "default": "default"
                    }
                },
                "required": ["dag_content"]
            }
        ),
        
        Tool(
            name="generate_activities",
            description=(
                "Genera Activities de Temporal a partir de tasks de Airflow. "
                "Distingue entre Activities centralizadas (del SDK) y personalizadas. "
                "Aplica reglas de plataforma para reutilización."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "dag_content": {
                        "type": "string",
                        "description": "Contenido del DAG de Airflow"
                    },
                    "migration_phase": {
                        "type": "string",
                        "enum": ["wrapper", "hybrid", "native"],
                        "default": "hybrid"
                    },
                    "force_custom": {
                        "type": "boolean",
                        "description": "Forzar generación de Activities personalizadas",
                        "default": False
                    }
                },
                "required": ["dag_content"]
            }
        ),
        
        Tool(
            name="generate_worker",
            description=(
                "Genera configuración de Worker de Temporal. "
                "Incluye registro de Activities, configuración de Task Queue, "
                "observabilidad y alineación con modelo de subgrupos."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_name": {
                        "type": "string",
                        "description": "Nombre del workflow"
                    },
                    "activities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de nombres de Activities a registrar"
                    },
                    "tenant": {
                        "type": "string",
                        "description": "Tenant propietario"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Namespace de Temporal",
                        "default": "default"
                    }
                },
                "required": ["workflow_name", "activities"]
            }
        ),
        
        Tool(
            name="full_migration",
            description=(
                "Pipeline completo de migración: analiza DAG, genera Workflow, "
                "Activities y Worker. Retorna todos los archivos necesarios "
                "para desplegar el workflow migrado."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "dag_content": {
                        "type": "string",
                        "description": "Contenido del DAG de Airflow"
                    },
                    "migration_phase": {
                        "type": "string",
                        "enum": ["wrapper", "hybrid", "native"],
                        "description": "Fase de migración",
                        "default": "wrapper"
                    },
                    "tenant": {
                        "type": "string",
                        "description": "Tenant propietario",
                        "default": "default-tenant"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Namespace de Temporal",
                        "default": "default"
                    },
                    "generate_readme": {
                        "type": "boolean",
                        "description": "Generar README con documentación",
                        "default": True
                    }
                },
                "required": ["dag_content"]
            }
        ),
        
        Tool(
            name="validate_migration",
            description=(
                "Valida código generado: sintaxis Python, imports, "
                "uso correcto de Activities centralizadas, naming conventions. "
                "Retorna reporte de validación."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_code": {
                        "type": "string",
                        "description": "Código del workflow generado"
                    },
                    "activities_code": {
                        "type": "string",
                        "description": "Código de activities generado"
                    },
                    "worker_code": {
                        "type": "string",
                        "description": "Código del worker generado"
                    }
                },
                "required": ["workflow_code"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Ejecuta una herramienta del MCP"""
    
    try:
        if name == "analyze_dag":
            return await analyze_dag_tool(arguments)
        
        elif name == "generate_workflow":
            return await generate_workflow_tool(arguments)
        
        elif name == "generate_activities":
            return await generate_activities_tool(arguments)
        
        elif name == "generate_worker":
            return await generate_worker_tool(arguments)
        
        elif name == "full_migration":
            return await full_migration_tool(arguments)
        
        elif name == "validate_migration":
            return await validate_migration_tool(arguments)
        
        else:
            return [TextContent(
                type="text",
                text=f"Error: Unknown tool '{name}'"
            )]
    
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error executing tool '{name}': {str(e)}"
        )]


async def analyze_dag_tool(arguments: dict) -> list[TextContent]:
    """Analiza un DAG de Airflow"""
    
    dag_content = arguments["dag_content"]
    dag_file_path = arguments.get("dag_file_path", "unknown.py")
    
    # Parsear DAG
    parser = DagParser(platform_rules)
    dag_info = parser.parse(dag_content, dag_file_path)
    
    # Analizar tasks
    analyzer = TaskAnalyzer(platform_rules)
    analysis = analyzer.analyze(dag_info)
    
    # Formatear resultado
    result = {
        "dag_id": dag_info.dag_id,
        "description": dag_info.description,
        "schedule_interval": dag_info.schedule_interval,
        "tasks": [
            {
                "task_id": task.task_id,
                "operator": task.operator_type,
                "suggested_activity": task.suggested_activity,
                "is_centralized": task.is_centralized,
                "dependencies": task.dependencies
            }
            for task in dag_info.tasks
        ],
        "analysis": {
            "total_tasks": analysis["total_tasks"],
            "centralized_activities": analysis["centralized_count"],
            "custom_activities": analysis["custom_count"],
            "complexity_score": analysis["complexity_score"],
            "migration_recommendation": analysis["recommendation"]
        }
    }
    
    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]


async def generate_workflow_tool(arguments: dict) -> list[TextContent]:
    """Genera Workflow de Temporal"""
    
    dag_content = arguments["dag_content"]
    migration_phase = arguments.get("migration_phase", "wrapper")
    tenant = arguments.get("tenant", "default-tenant")
    namespace = arguments.get("namespace", "default")
    
    # Parsear DAG
    parser = DagParser(platform_rules)
    dag_info = parser.parse(dag_content)
    
    # Generar workflow
    generator = WorkflowGenerator(platform_rules)
    workflow_code = generator.generate(
        dag_info=dag_info,
        migration_phase=migration_phase,
        tenant=tenant,
        namespace=namespace
    )
    
    return [TextContent(
        type="text",
        text=workflow_code
    )]


async def generate_activities_tool(arguments: dict) -> list[TextContent]:
    """Genera Activities de Temporal"""
    
    dag_content = arguments["dag_content"]
    migration_phase = arguments.get("migration_phase", "hybrid")
    force_custom = arguments.get("force_custom", False)
    
    # Parsear DAG
    parser = DagParser(platform_rules)
    dag_info = parser.parse(dag_content)
    
    # Generar activities
    generator = ActivityGenerator(platform_rules)
    activities_code = generator.generate(
        dag_info=dag_info,
        migration_phase=migration_phase,
        force_custom=force_custom
    )
    
    return [TextContent(
        type="text",
        text=activities_code
    )]


async def generate_worker_tool(arguments: dict) -> list[TextContent]:
    """Genera configuración de Worker"""
    
    workflow_name = arguments["workflow_name"]
    activities = arguments["activities"]
    tenant = arguments.get("tenant", "default-tenant")
    namespace = arguments.get("namespace", "default")
    
    # Generar worker
    generator = WorkerGenerator(platform_rules)
    worker_code = generator.generate(
        workflow_name=workflow_name,
        activities=activities,
        tenant=tenant,
        namespace=namespace
    )
    
    return [TextContent(
        type="text",
        text=worker_code
    )]


async def full_migration_tool(arguments: dict) -> list[TextContent]:
    """Pipeline completo de migración"""
    
    dag_content = arguments["dag_content"]
    migration_phase = arguments.get("migration_phase", "wrapper")
    tenant = arguments.get("tenant", "default-tenant")
    namespace = arguments.get("namespace", "default")
    generate_readme = arguments.get("generate_readme", True)
    
    # 1. Parsear DAG
    parser = DagParser(platform_rules)
    dag_info = parser.parse(dag_content)
    
    # 2. Generar Workflow
    workflow_gen = WorkflowGenerator(platform_rules)
    workflow_code = workflow_gen.generate(
        dag_info=dag_info,
        migration_phase=migration_phase,
        tenant=tenant,
        namespace=namespace
    )
    
    # 3. Generar Activities
    activity_gen = ActivityGenerator(platform_rules)
    activities_code = activity_gen.generate(
        dag_info=dag_info,
        migration_phase=migration_phase
    )
    
    # 4. Generar Worker
    worker_gen = WorkerGenerator(platform_rules)
    activity_names = [task.task_id for task in dag_info.tasks]
    worker_code = worker_gen.generate(
        workflow_name=dag_info.dag_id,
        activities=activity_names,
        tenant=tenant,
        namespace=namespace
    )
    
    # 5. Generar README (opcional)
    readme_content = ""
    if generate_readme:
        readme_content = _generate_readme(
            dag_info=dag_info,
            migration_phase=migration_phase,
            tenant=tenant,
            namespace=namespace
        )
    
    # Formatear resultado
    result = {
        "migration_phase": migration_phase,
        "dag_id": dag_info.dag_id,
        "tenant": tenant,
        "namespace": namespace,
        "files": {
            "workflows.py": workflow_code,
            "activities.py": activities_code,
            "run_worker.py": worker_code,
        }
    }
    
    if readme_content:
        result["files"]["README.md"] = readme_content
    
    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]


async def validate_migration_tool(arguments: dict) -> list[TextContent]:
    """Valida código generado"""
    
    workflow_code = arguments["workflow_code"]
    activities_code = arguments.get("activities_code", "")
    worker_code = arguments.get("worker_code", "")
    
    validation_results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "suggestions": []
    }
    
    # Validar sintaxis Python
    try:
        compile(workflow_code, "<workflow>", "exec")
    except SyntaxError as e:
        validation_results["valid"] = False
        validation_results["errors"].append(f"Syntax error in workflow: {str(e)}")
    
    if activities_code:
        try:
            compile(activities_code, "<activities>", "exec")
        except SyntaxError as e:
            validation_results["valid"] = False
            validation_results["errors"].append(f"Syntax error in activities: {str(e)}")
    
    # Validar imports
    if "from temporalio import workflow" not in workflow_code:
        validation_results["warnings"].append("Missing 'from temporalio import workflow' import")
    
    # Validar uso de Activities centralizadas
    if "platform_sdk" in activities_code:
        validation_results["suggestions"].append(
            "Good: Using centralized activities from platform_sdk"
        )
    
    return [TextContent(
        type="text",
        text=json.dumps(validation_results, indent=2)
    )]


def _generate_readme(dag_info, migration_phase: str, tenant: str, namespace: str) -> str:
    """Genera README para el workflow migrado"""
    
    return f"""# {dag_info.dag_id}

## Información de Migración

- **DAG Original**: `{dag_info.dag_id}`
- **Fase de Migración**: `{migration_phase}`
- **Tenant**: `{tenant}`
- **Namespace**: `{namespace}`
- **Fecha de Migración**: Auto-generado por MCP

## Descripción

{dag_info.description or "Sin descripción"}

## Tasks Migrados

{chr(10).join(f"- `{task.task_id}` ({task.operator_type})" for task in dag_info.tasks)}

## Ejecución

### Iniciar Worker

```bash
python run_worker.py
```

### Ejecutar Workflow

```python
from temporalio.client import Client
from workflows import {dag_info.dag_id.replace('-', '_').title()}Workflow

async def main():
    client = await Client.connect("localhost:7233", namespace="{namespace}")
    
    result = await client.execute_workflow(
        {dag_info.dag_id.replace('-', '_').title()}Workflow.run,
        {{"param": "value"}},
        id="{dag_info.dag_id}-{{execution_id}}",
        task_queue="{tenant}-{dag_info.dag_id}"
    )
    
    print(result)
```

## Fase de Migración: {migration_phase}

### {migration_phase.title()}

{_get_phase_description(migration_phase)}

## Próximos Pasos

{_get_next_steps(migration_phase)}
"""


def _get_phase_description(phase: str) -> str:
    """Retorna descripción de la fase"""
    descriptions = {
        "wrapper": "El DAG completo se ejecuta desde Temporal como un wrapper. Airflow actúa solo como ejecutor.",
        "hybrid": "Algunas tasks migradas a Activities nativas, otras siguen en Airflow.",
        "native": "Completamente migrado a Temporal. Airflow deprecado para este automatismo."
    }
    return descriptions.get(phase, "")


def _get_next_steps(phase: str) -> str:
    """Retorna próximos pasos según la fase"""
    steps = {
        "wrapper": "1. Validar ejecución del wrapper\n2. Identificar tasks para migrar a nativo\n3. Avanzar a fase hybrid",
        "hybrid": "1. Migrar tasks restantes a Activities nativas\n2. Validar comportamiento\n3. Avanzar a fase native",
        "native": "1. Monitorear ejecución\n2. Deprecar DAG de Airflow\n3. Documentar lecciones aprendidas"
    }
    return steps.get(phase, "")


def serve():
    """Inicia el servidor MCP"""
    import sys
    from mcp.server.stdio import stdio_server
    
    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )
    
    asyncio.run(main())


if __name__ == "__main__":
    serve()
