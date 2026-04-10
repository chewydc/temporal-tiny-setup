#!/usr/bin/env python3
"""
Cliente para ejecutar workflows de Temporal Lifecycle Demo DESDE KUBERNETES.
"""

import asyncio
import sys
from datetime import datetime
from temporalio.client import Client


async def execute_lifecycle_workflow(version_id: str = None):
    """Ejecuta el LifecycleWorkflow de 5 minutos.
    
    Args:
        version_id: Si se especifica, bloquea el workflow a esa versión específica.
    """
    print("🚀 Conectando a Temporal Server...")
    
    try:
        # Conectar usando el DNS interno de Kubernetes
        client = await Client.connect('temporal-frontend-lb.temporal.svc.cluster.local:7233')
        print("✅ Conectado a Temporal Server")
        
        workflow_id = f"lifecycle-demo-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        if version_id:
            print(f"🎯 Iniciando workflow VERSIONADO: {workflow_id}")
            print(f"🔒 Versión bloqueada: {version_id}")
            workflow_id = f"versioned-{version_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        else:
            print(f"🎯 Iniciando workflow: {workflow_id}")
        
        print("⏳ Duración estimada: 5 minutos")
        print("")
        
        # Preparar argumentos
        workflow_kwargs = {
            'workflow': 'LifecycleWorkflow',
            'arg': {'workflow_id': workflow_id},
            'id': workflow_id,
            'task_queue': 'lifecycle-queue'
        }
        
        # Agregar version_id si se especificó
        if version_id:
            workflow_kwargs['version_id'] = version_id
        
        result = await client.execute_workflow(**workflow_kwargs)
        
        print("🎉 Workflow completado exitosamente!")
        print(f"📊 Resultado: {result}")
        
    except Exception as e:
        print(f"❌ Error ejecutando workflow: {e}")
        sys.exit(1)


async def execute_quick_test(version_id: str = None):
    """Ejecuta el QuickTestWorkflow de 30 segundos.
    
    Args:
        version_id: Si se especifica, bloquea el workflow a esa versión específica.
    """
    print("🧪 Conectando a Temporal Server...")
    
    try:
        client = await Client.connect('temporal-frontend-lb.temporal.svc.cluster.local:7233')
        print("✅ Conectado a Temporal Server")
        
        test_id = f"quick-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        if version_id:
            print(f"🎯 Test rápido VERSIONADO: {test_id}")
            print(f"🔒 Versión bloqueada: {version_id}")
            test_id = f"quick-versioned-{version_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        else:
            print(f"🎯 Iniciando test rápido: {test_id}")
        
        print("⏳ Duración estimada: 30 segundos")
        print("")
        
        workflow_kwargs = {
            'workflow': 'QuickTestWorkflow',
            'arg': test_id,
            'id': test_id,
            'task_queue': 'lifecycle-queue'
        }
        
        if version_id:
            workflow_kwargs['version_id'] = version_id
        
        result = await client.execute_workflow(**workflow_kwargs)
        
        print("🎉 Test completado exitosamente!")
        print(f"📊 Resultado: {result}")
        
    except Exception as e:
        print(f"❌ Error ejecutando test: {e}")
        sys.exit(1)


async def main():
    """Función principal."""
    if len(sys.argv) < 2:
        print("Uso: python client_k8s.py [lifecycle|quick] [version_id]")
        print("")
        print("Ejemplos:")
        print("  python client_k8s.py lifecycle          # Sin versioning")
        print("  python client_k8s.py lifecycle v1.0.0   # Bloqueado a v1.0.0")
        print("  python client_k8s.py quick v2.0.0       # Test rápido en v2.0.0")
        return
    
    command = sys.argv[1].lower()
    version_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    if command == 'lifecycle':
        await execute_lifecycle_workflow(version_id)
    elif command == 'quick':
        await execute_quick_test(version_id)
    else:
        print(f"❌ Comando desconocido: {command}")
        print("Uso: python client_k8s.py [lifecycle|quick] [version_id]")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
