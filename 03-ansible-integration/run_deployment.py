import asyncio
from temporalio.client import Client
from models import NetworkDeploymentRequest
from workflows import NetworkDeploymentWithAnsibleRunner

async def main():
    """Ejecuta workflow de despliegue con Ansible Runner + Airflow"""
    
    print("🚀 CASO 03: Despliegue con Ansible Runner + Airflow")
    print("="*60)
    
    # Configurar request
    request = NetworkDeploymentRequest(
        router_id="virtual-router-003",
        router_ip="172.20.0.10",
        software_version="FRR-8.5.1",
        network_config={
            "ospf_area": "0.0.0.0",
            "bgp_asn": "65001"
        }
    )
    
    print(f"📋 Router ID: {request.router_id}")
    print(f"🌐 Router IP: {request.router_ip}")
    print(f"💿 Software: {request.software_version}")
    print(f"⚙️ Config: {request.network_config}")
    print()
    
    # Conectar a Temporal
    client = await Client.connect("localhost:7233")
    
    print("⚡ Iniciando workflow Temporal...")
    print("🔧 Step 1: Ansible Runner desplegará router container")
    print("🌊 Step 2: Airflow configurará software")
    print("🔍 Step 3: Validación completa")
    print()
    
    try:
        # Ejecutar workflow
        result = await client.execute_workflow(
            NetworkDeploymentWithAnsibleRunner.run,
            request,
            id=f"network-deployment-{request.router_id}",
            task_queue="network-deployment-queue"
        )
        
        print("✅ WORKFLOW COMPLETADO EXITOSAMENTE!")
        print("="*60)
        print(f"📊 Resultado: {result}")
        print()
        print("🔍 Para verificar el router desplegado:")
        print(f"   docker ps --filter name={request.router_id}")
        print(f"   docker logs {request.router_id}")
        print()
        print("🌐 Para acceder al router:")
        print(f"   docker exec -it {request.router_id} vtysh")
        
    except Exception as e:
        print(f"❌ WORKFLOW FALLÓ: {str(e)}")
        print()
        print("🔍 Para debug:")
        print("   • Verificar que Temporal server esté corriendo")
        print("   • Verificar que worker esté corriendo")
        print("   • Verificar que Ansible Runner esté disponible (ansible-runner container)")
        print("   • Verificar que Airflow esté disponible (localhost:8080)")

if __name__ == "__main__":
    asyncio.run(main())