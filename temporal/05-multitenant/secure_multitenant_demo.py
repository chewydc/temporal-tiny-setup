"""
Demo Multitenant con NAMESPACES - Segmentación Real
====================================================

Cada tenant tiene su propio namespace = aislamiento total.
En producción + autenticación = seguridad completa.
"""

import asyncio
from temporalio.client import Client
from workflows import NetworkDeploymentWorkflow
from models import NetworkDeploymentRequest

# Simula usuarios autenticados
USERS = {
    "user_chogar": {"tenant_id": "chogar", "role": "admin"},
    "user_amovil": {"tenant_id": "amovil", "role": "operator"},
    "user_afijo": {"tenant_id": "afijo", "role": "admin"}
}

async def get_tenant_client(tenant_id: str) -> Client:
    """
    Conecta al namespace específico del tenant.
    En producción: validar permisos antes de retornar el cliente.
    """
    return await Client.connect(
        "localhost:7233",
        namespace=f"tenant-{tenant_id}"
    )

async def start_deployment_for_tenant(user_id: str, router_config: dict):
    """
    Inicia deployment validando que el usuario pertenece al tenant.
    """
    # 1. Obtener info del usuario (en prod: desde JWT/session)
    user = USERS.get(user_id)
    if not user:
        raise Exception(f"Usuario {user_id} no autorizado")
    
    tenant_id = user["tenant_id"]
    
    # 2. Conectar al namespace del tenant
    client = await get_tenant_client(tenant_id)
    
    # 3. Crear request
    request = NetworkDeploymentRequest(
        tenant_id=tenant_id,
        router_id=router_config["router_id"],
        router_ip=router_config["router_ip"],
        software_version=router_config["software_version"]
    )
    
    # 4. Iniciar workflow en el namespace del tenant
    workflow_id = f"{tenant_id}-{request.router_id}"
    
    handle = await client.start_workflow(
        NetworkDeploymentWorkflow.run,
        request,
        id=workflow_id,
        task_queue=f"tenant-{tenant_id}-deployments"
    )
    
    print(f"✅ [{user_id}] Workflow iniciado: {workflow_id}")
    print(f"   Namespace: tenant-{tenant_id}")
    print(f"   UI: http://localhost:8233/namespaces/tenant-{tenant_id}/workflows/{workflow_id}")
    
    return handle

async def list_my_workflows(user_id: str):
    """
    Lista workflows del tenant del usuario.
    Solo ve workflows de su namespace.
    """
    user = USERS.get(user_id)
    if not user:
        raise Exception(f"Usuario {user_id} no autorizado")
    
    tenant_id = user["tenant_id"]
    client = await get_tenant_client(tenant_id)
    
    print(f"\n📋 Workflows de {user_id} (tenant: {tenant_id}):")
    print("="*60)
    
    count = 0
    async for workflow in client.list_workflows():
        print(f"  {workflow.id} - {workflow.status}")
        count += 1
        if count >= 5:  # Limitar a 5
            break
    
    if count == 0:
        print("  (sin workflows)")

async def main():
    """
    Demo: Cada usuario solo ve workflows de su tenant.
    """
    
    print("\n" + "="*80)
    print("DEMO: MULTITENANT CON NAMESPACES (Segmentación Real)")
    print("="*80)
    print("\n⚠️  PREREQUISITO: Crear namespaces primero")
    print("   Ejecuta: python setup_namespaces.py\n")
    
    # Simular 3 usuarios iniciando deployments
    deployments = [
        ("user_chogar", {"router_id": "RTR-CH-001", "router_ip": "10.1.1.1", "software_version": "v2.1"}),
        ("user_amovil", {"router_id": "RTR-AM-001", "router_ip": "10.2.1.1", "software_version": "v2.1"}),
        ("user_afijo", {"router_id": "RTR-AF-001", "router_ip": "10.3.1.1", "software_version": "v2.1"}),
    ]
    
    print("\n🚀 Iniciando deployments por usuario/tenant:\n")
    
    for user_id, config in deployments:
        try:
            await start_deployment_for_tenant(user_id, config)
        except Exception as e:
            print(f"❌ Error: {e}")
        
        await asyncio.sleep(0.5)
    
    print("\n" + "="*80)
    print("VERIFICACIÓN: Cada usuario solo ve sus workflows")
    print("="*80)
    
    # Cada usuario lista sus workflows (solo ve los de su namespace)
    for user_id in ["user_chogar", "user_amovil", "user_afijo"]:
        try:
            await list_my_workflows(user_id)
        except Exception as e:
            print(f"\n❌ {user_id}: {e}")
    
    print("\n" + "="*80)
    print("🔍 VERIFICAR EN TEMPORAL UI:")
    print("="*80)
    print("  1. http://localhost:8233")
    print("  2. Cambiar namespace en el dropdown superior")
    print("  3. Cada namespace solo muestra workflows de ese tenant")
    print()

if __name__ == "__main__":
    asyncio.run(main())
