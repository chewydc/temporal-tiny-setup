#!/usr/bin/env python3
"""
Cliente para ejecutar workflows CON VERSIONING ESTRICTO.
Los workflows se ejecutan SOLO en la versión especificada.
"""

import asyncio
import sys
from datetime import datetime
from temporalio.client import Client


async def execute_versioned_workflow(version: str):
    """Ejecuta workflow bloqueado a una versión específica."""
    print(f"🔒 Conectando a Temporal Server...")
    
    try:
        client = await Client.connect('temporal-frontend-lb.temporal.svc.cluster.local:7233')
        print("✅ Conectado a Temporal Server")
        
        workflow_id = f"versioned-{version}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        print(f"🎯 Iniciando workflow VERSIONADO: {workflow_id}")
        print(f"🔒 Versión bloqueada: {version}")
        print(f"⚠️  Este workflow SOLO se ejecutará en workers {version}")
        print("")
        
        # Ejecutar con version_id para bloquear a versión específica
        result = await client.execute_workflow(
            'LifecycleWorkflow',
            {'workflow_id': workflow_id},
            id=workflow_id,
            task_queue='lifecycle-versioned-queue',
            # 🔑 Esto bloquea el workflow a la versión específica
            version_id=version
        )
        
        print("🎉 Workflow completado exitosamente!")
        print(f"📊 Resultado: {result}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


async def execute_quick_versioned(version: str):
    """Test rápido con versión bloqueada."""
    print(f"🧪 Conectando a Temporal Server...")
    
    try:
        client = await Client.connect('temporal-frontend-lb.temporal.svc.cluster.local:7233')
        print("✅ Conectado")
        
        test_id = f"quick-versioned-{version}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        print(f"🎯 Test rápido versionado: {test_id}")
        print(f"🔒 Versión: {version}")
        print("")
        
        result = await client.execute_workflow(
            'QuickTestWorkflow',
            test_id,
            id=test_id,
            task_queue='lifecycle-versioned-queue',
            version_id=version
        )
        
        print("🎉 Test completado!")
        print(f"📊 Resultado: {result}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


async def main():
    """Función principal."""
    if len(sys.argv) != 3:
        print("Uso: python client_versioned.py [lifecycle|quick] [version]")
        print("")
        print("Ejemplos:")
        print("  python client_versioned.py lifecycle v1.0.0")
        print("  python client_versioned.py quick v2.0.0")
        return
    
    command = sys.argv[1].lower()
    version = sys.argv[2]
    
    if command == 'lifecycle':
        await execute_versioned_workflow(version)
    elif command == 'quick':
        await execute_quick_versioned(version)
    else:
        print(f"❌ Comando desconocido: {command}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
