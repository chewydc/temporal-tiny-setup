"""
Script simple para probar un deployment de un solo tenant.
Útil para entender el flujo básico antes de ejecutar el demo completo.
"""
import asyncio
from datetime import datetime
from temporalio.client import Client
from models import NetworkDeploymentRequest

async def simple_tenant_demo():
    """Demo simple con un solo tenant"""
    
    print("="*60)
    print("DEMO SIMPLE: UN TENANT")
    print("="*60)
    print()
    
    tenant_id = "chogar"
    
    try:
        # Conectar a Temporal
        client = await Client.connect("localhost:7233")
        print(f"✅ Conectado a Temporal Server\n")
        
        # Crear request
        request = NetworkDeploymentRequest(
            tenant_id=tenant_id,
            router_id=f"{tenant_id}-router-001",
            router_ip="10.100.1.1",
            software_version="frr-8.0",
            network_config={
                "client_network": "192.168.1.0/24",
                "server_network": "192.168.2.0/24"
            }
        )
        
        # Workflow ID único
        workflow_id = f"{tenant_id}-deployment-{int(datetime.now().timestamp())}"
        
        # Task queue del tenant
        task_queue = f"tenant-{tenant_id}-deployments"
        
        print(f"🏢 Tenant: {tenant_id}")
        print(f"📋 Task Queue: {task_queue}")
        print(f"🆔 Workflow ID: {workflow_id}")
        print(f"🔧 Router: {request.router_id}")
        print()
        
        # Iniciar workflow (no bloqueante)
        handle = await client.start_workflow(
            "NetworkDeploymentWorkflow",
            request,
            id=workflow_id,
            task_queue=task_queue,
            search_attributes={"CustomStringField": [tenant_id]}
        )
        
        print(f"✅ Workflow iniciado!")
        print(f"   URL: http://localhost:8233/namespaces/default/workflows/{workflow_id}")
        print()
        print("💡 Para aprobar el deployment:")
        print(f"   temporal workflow signal --workflow-id {workflow_id} --name approve_deployment")
        print()
        print("🔍 Para ver el estado:")
        print(f"   temporal workflow describe --workflow-id {workflow_id}")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nVerifica que:")
        print("  1. Temporal Server esté corriendo: docker-compose ps")
        print("  2. Worker esté activo: python multitenant_worker.py")

if __name__ == "__main__":
    asyncio.run(simple_tenant_demo())
