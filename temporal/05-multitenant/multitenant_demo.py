import asyncio
from datetime import datetime
from temporalio.client import Client
from models import NetworkDeploymentRequest

async def deploy_for_tenant(tenant_id: str, router_number: int):
    """Ejecuta un deployment para un tenant específico en su namespace"""
    
    # Conectar al namespace del tenant
    client = await Client.connect(
        "localhost:7233",
        namespace=tenant_id  # ⭐ Namespace separado
    )
    
    deployment_request = NetworkDeploymentRequest(
        tenant_id=tenant_id,
        router_id=f"{tenant_id}-router-{router_number:03d}",
        router_ip=f"10.{hash(tenant_id) % 255}.{router_number}.1",
        software_version="frr-8.0",
        network_config={
            "client_network": f"192.168.{router_number}.0/24",
            "server_network": f"192.168.{router_number + 100}.0/24"
        }
    )
    
    workflow_id = f"{tenant_id}-deployment-{router_number}-{int(datetime.now().timestamp())}"
    task_queue = f"{tenant_id}-deployments"
    
    print(f"🚀 [{tenant_id}] Iniciando deployment: {deployment_request.router_id}")
    print(f"   Namespace: {tenant_id}")
    print(f"   Workflow ID: {workflow_id}")
    print(f"   Task Queue: {task_queue}\n")
    
    try:
        handle = await client.start_workflow(
            "NetworkDeploymentWorkflow",
            deployment_request,
            id=workflow_id,
            task_queue=task_queue
        )
        
        print(f"✅ [{tenant_id}] Workflow iniciado: {handle.id}")
        return handle
        
    except Exception as e:
        print(f"❌ [{tenant_id}] Error iniciando workflow: {e}")
        return None

async def multitenant_demo():
    """
    Demo de arquitectura multitenant con Namespaces separados.
    
    Conceptos demostrados:
    1. Namespace por tenant: Aislamiento COMPLETO de datos
    2. Cada tenant solo ve sus workflows en Temporal UI
    3. Workflow IDs únicos por namespace
    4. Ejecución concurrente de múltiples tenants
    """
    
    print("="*80)
    print("DEMO: ARQUITECTURA MULTITENANT CON NAMESPACES")
    print("="*80)
    print()
    
    try:
        # Configuración de tenants y sus deployments
        tenant_deployments = {
            "chogar": 2,
            "amovil": 1,
            "afijo": 3
        }
        
        print("🏢 Configuración de tenants:")
        for tenant, count in tenant_deployments.items():
            print(f"   {tenant}: {count} deployment(s) en namespace '{tenant}'")
        print()
        
        print("="*80)
        print("INICIANDO DEPLOYMENTS CONCURRENTES")
        print("="*80)
        print()
        
        # Iniciar todos los deployments concurrentemente
        tasks = []
        for tenant_id, deployment_count in tenant_deployments.items():
            for router_num in range(1, deployment_count + 1):
                task = deploy_for_tenant(tenant_id, router_num)
                tasks.append(task)
        
        handles = await asyncio.gather(*tasks)
        successful_handles = [h for h in handles if h is not None]
        
        print()
        print("="*80)
        print(f"WORKFLOWS INICIADOS: {len(successful_handles)}/{len(tasks)}")
        print("="*80)
        print()
        
        print("📊 Monitoreo:")
        print(f"   Total workflows: {len(successful_handles)}")
        print(f"   Temporal UI: http://localhost:8233")
        print()
        
        print("🔍 Cómo ver workflows por tenant:")
        for tenant in tenant_deployments.keys():
            print(f"   {tenant}: Seleccioná namespace '{tenant}' en el dropdown de Temporal UI")
        print()
        
        print("🎯 Aislamiento:")
        print("   - Cada tenant SOLO ve sus workflows")
        print("   - No hay filtros necesarios")
        print("   - Aislamiento completo de datos")
        print()
        
        print("⏳ Esperando 10 segundos para ver el progreso inicial...")
        await asyncio.sleep(10)
        
        print("\n✅ Demo completado. Los workflows continúan ejecutándose.")
        print("   Usa Temporal UI para monitorear el progreso.\n")
        
        return successful_handles
        
    except Exception as e:
        print(f"\n❌ Error en demo: {e}")
        print("\nVerifica que:")
        print("  - Temporal Server esté corriendo: docker-compose ps")
        print("  - Namespaces estén creados: python setup_namespaces.py")
        print("  - Workers estén activos: python multitenant_worker.py")
        return None

async def query_tenant_workflows(tenant_id: str):
    """Consulta workflows de un tenant específico"""
    
    print(f"\n🔍 Consultando workflows del tenant: {tenant_id}")
    
    try:
        client = await Client.connect("localhost:7233")
        
        # Listar workflows usando search attributes
        # Nota: Requiere configuración de search attributes en Temporal
        async for workflow in client.list_workflows(f'CustomStringField = "{tenant_id}"'):
            print(f"   - {workflow.id}: {workflow.status}")
            
    except Exception as e:
        print(f"❌ Error consultando workflows: {e}")

if __name__ == "__main__":
    print("\n" + "="*80)
    print("TEMPORAL MULTITENANT DEMO - NAMESPACES")
    print("="*80)
    print("\nAsegúrate de tener corriendo:")
    print("  1. Temporal Server: docker-compose up -d")
    print("  2. Namespaces creados: python setup_namespaces.py")
    print("  3. Workers: python multitenant_worker.py")
    print("\nPresiona Ctrl+C para cancelar\n")
    
    try:
        asyncio.run(multitenant_demo())
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo cancelado por el usuario\n")
