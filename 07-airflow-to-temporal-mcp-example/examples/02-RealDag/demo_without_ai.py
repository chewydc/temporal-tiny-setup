#!/usr/bin/env python3
"""
Demo script - Backup si el MCP falla
Usa el MCP como librería Python directamente
"""

import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from airflow_to_temporal_mcp.parsers.dag_parser import DagParser
from airflow_to_temporal_mcp.generators.workflow_gen import WorkflowGenerator
from airflow_to_temporal_mcp.generators.activity_gen import ActivityGenerator
from airflow_to_temporal_mcp.generators.worker_gen import WorkerGenerator
from airflow_to_temporal_mcp.rules.platform_rules import PlatformRules


def main():
    print("=" * 60)
    print("🚀 DEMO: Airflow to Temporal Migration")
    print("=" * 60)
    print()
    
    # Rutas
    config_path = Path(__file__).parent.parent.parent / "config" / "platform_config.yaml"
    dag_path = Path(__file__).parent / "input_real_dag_chogar" / "chogar_despertar_tr.py"
    output_dir = Path(__file__).parent / "output_mcp_server"
    
    # Crear output dir si no existe
    output_dir.mkdir(exist_ok=True)
    
    print(f"📄 DAG Input: {dag_path.name}")
    print(f"⚙️  Config: {config_path.name}")
    print(f"📁 Output: {output_dir}")
    print()
    
    # 1. Cargar reglas
    print("1️⃣  Cargando reglas de plataforma...")
    rules = PlatformRules(str(config_path))
    print(f"   ✅ {len(rules.centralized_activities)} Activities centralizadas detectadas")
    print()
    
    # 2. Leer DAG
    print("2️⃣  Leyendo DAG de Airflow...")
    with open(dag_path, 'r', encoding='utf-8') as f:
        dag_content = f.read()
    print(f"   ✅ {len(dag_content)} caracteres leídos")
    print()
    
    # 3. Parsear DAG
    print("3️⃣  Analizando DAG con AST...")
    parser = DagParser(rules)
    dag_info = parser.parse(dag_content, str(dag_path))
    
    print(f"   📊 DAG ID: {dag_info.dag_id}")
    print(f"   📊 Tasks encontradas: {len(dag_info.tasks)}")
    print()
    
    print("   📋 Detalle de tasks:")
    for task in dag_info.tasks:
        print(f"      - {task.task_id} ({task.operator_type})")
        if task.is_centralized:
            print(f"        ✅ Usa Activity centralizada: {task.centralized_activity}")
        else:
            print(f"        ⚠️  Requiere Activity personalizada")
    print()
    
    # 4. Generar Workflow
    print("4️⃣  Generando Workflow (fase HYBRID)...")
    workflow_gen = WorkflowGenerator(rules)
    workflow_code = workflow_gen.generate(
        dag_info=dag_info,
        migration_phase="hybrid",
        tenant="chogar-team",
        namespace="default"
    )
    
    workflow_file = output_dir / "workflows.py"
    with open(workflow_file, 'w', encoding='utf-8') as f:
        f.write(workflow_code)
    print(f"   ✅ Generado: {workflow_file.name}")
    print()
    
    # 5. Generar Activities
    print("5️⃣  Generando Activities...")
    activity_gen = ActivityGenerator(rules)
    activities_code = activity_gen.generate(
        dag_info=dag_info,
        migration_phase="hybrid"
    )
    
    activities_file = output_dir / "activities.py"
    with open(activities_file, 'w', encoding='utf-8') as f:
        f.write(activities_code)
    print(f"   ✅ Generado: {activities_file.name}")
    print()
    
    # 6. Generar Worker
    print("6️⃣  Generando Worker definition...")
    worker_gen = WorkerGenerator(rules)
    worker_code = worker_gen.generate(
        workflow_name=dag_info.dag_id,
        activities=[task.task_id for task in dag_info.tasks],
        tenant="chogar-team"
    )
    
    worker_file = output_dir / "run_worker.py"
    with open(worker_file, 'w', encoding='utf-8') as f:
        f.write(worker_code)
    print(f"   ✅ Generado: {worker_file.name}")
    print()
    
    # Resumen
    print("=" * 60)
    print("✅ MIGRACIÓN COMPLETADA")
    print("=" * 60)
    print()
    print("📁 Archivos generados en:", output_dir)
    print()
    print("   1. workflows.py      - Workflow de Temporal")
    print("   2. activities.py     - Activities (centralizadas + custom)")
    print("   3. run_worker.py     - Worker definition")
    print()
    print("🎯 Próximos pasos:")
    print()
    print("   1. Revisar TODOs en activities.py")
    print("   2. Completar lógica personalizada")
    print("   3. Probar localmente con Temporal")
    print("   4. Desplegar a staging")
    print()
    print("💡 Beneficios clave:")
    print()
    print("   ✅ Usa Activities del SDK (no duplica código)")
    print("   ✅ Naming estandarizado")
    print("   ✅ Worker configurado con observabilidad")
    print("   ✅ Migración gradual (fase HYBRID)")
    print()
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
