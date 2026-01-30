#!/usr/bin/env python3
"""
Cliente para ejecutar workflows de Temporal Lifecycle Demo.
"""

import asyncio
import sys
from datetime import datetime
from temporalio.client import Client


async def execute_lifecycle_workflow():
    """Ejecuta el LifecycleWorkflow de 5 minutos."""
    print("🚀 Conectando a Temporal Server...")
    
    try:
        client = await Client.connect('localhost:7233')
        print("✅ Conectado a Temporal Server")
        
        workflow_id = f"lifecycle-demo-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        print(f"🎯 Iniciando workflow: {workflow_id}")
        print("⏳ Duración estimada: 5 minutos")
        print("🌐 Ver progreso en Web UI: http://localhost:8080")
        print("")
        
        result = await client.execute_workflow(
            'LifecycleWorkflow.run',
            {'workflow_id': workflow_id},
            id=workflow_id,
            task_queue='lifecycle-queue'
        )
        
        print("🎉 Workflow completado exitosamente!")
        print(f"📊 Resultado: {result}")
        
    except Exception as e:
        print(f"❌ Error ejecutando workflow: {e}")
        print("\n🔧 Verificar:")
        print("   1. Port-forward corriendo: kubectl port-forward service/temporal-frontend-lb 7233:7233 -n temporal")
        print("   2. Workers desplegados: kubectl get pods -n workers")
        sys.exit(1)


async def execute_quick_test():
    """Ejecuta el QuickTestWorkflow de 30 segundos."""
    print("🧪 Conectando a Temporal Server...")
    
    try:
        client = await Client.connect('localhost:7233')
        print("✅ Conectado a Temporal Server")
        
        test_id = f"quick-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        print(f"🎯 Iniciando test rápido: {test_id}")
        print("⏳ Duración estimada: 30 segundos")
        print("")
        
        result = await client.execute_workflow(
            'QuickTestWorkflow.run',
            test_id,
            id=test_id,
            task_queue='lifecycle-queue'
        )
        
        print("🎉 Test completado exitosamente!")
        print(f"📊 Resultado: {result}")
        
    except Exception as e:
        print(f"❌ Error ejecutando test: {e}")
        sys.exit(1)


def show_help():
    """Muestra ayuda de uso."""
    print("🎬 Temporal Lifecycle Demo - Cliente")
    print("====================================")
    print("")
    print("Uso:")
    print("  python client.py lifecycle    # Ejecutar workflow de 5 minutos")
    print("  python client.py quick        # Ejecutar test de 30 segundos")
    print("  python client.py help         # Mostrar esta ayuda")
    print("")
    print("Prerequisitos:")
    print("  1. Port-forward Temporal Server:")
    print("     kubectl port-forward service/temporal-frontend-lb 7233:7233 -n temporal")
    print("")
    print("  2. Workers desplegados:")
    print("     kubectl get pods -n workers")
    print("")
    print("  3. Web UI (opcional):")
    print("     kubectl port-forward service/temporal-web 8080:8080 -n temporal")
    print("     http://localhost:8080")


async def main():
    """Función principal."""
    if len(sys.argv) != 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'lifecycle':
        await execute_lifecycle_workflow()
    elif command == 'quick':
        await execute_quick_test()
    elif command == 'help':
        show_help()
    else:
        print(f"❌ Comando desconocido: {command}")
        show_help()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())