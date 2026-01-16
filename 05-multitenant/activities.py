import asyncio
from temporalio import activity
from models import NetworkDeploymentRequest, ConnectivityTest, DeploymentResult

@activity.defn
async def test_client_server_connectivity(test_phase: str) -> dict:
    """Simula test de conectividad"""
    print(f"🔍 [{test_phase}] Simulando test de conectividad...")
    await asyncio.sleep(1)
    
    return {
        "phase": test_phase,
        "status": "simulated",
        "tests": [
            {"test_type": "ping", "source": "client", "destination": "server", "success": True},
            {"test_type": "http", "source": "client", "destination": "server", "success": True}
        ],
        "successful_tests": 2,
        "total_tests": 2
    }

@activity.defn
async def provision_router_via_ansible_runner(request: NetworkDeploymentRequest) -> str:
    """Simula despliegue de router"""
    print(f"🚀 Simulando despliegue de router {request.router_id} para tenant {request.tenant_id}...")
    await asyncio.sleep(2)
    return f"Router {request.router_id} deployed (simulated)"

@activity.defn
async def deploy_router_software(request: NetworkDeploymentRequest) -> str:
    """Simula configuración de software"""
    print(f"⚙️  Simulando configuración de software para {request.router_id}...")
    await asyncio.sleep(1)
    return f"Software configured on {request.router_id} (simulated)"

@activity.defn
async def generate_deployment_report(data: dict) -> DeploymentResult:
    """Genera reporte final"""
    print(f"📊 Generando reporte para tenant {data.get('tenant_id', 'unknown')}...")
    await asyncio.sleep(0.5)
    
    request_data = data["request"]
    
    tests = [
        ConnectivityTest(
            test_type="ping",
            source="client",
            destination="server",
            success=True
        ),
        ConnectivityTest(
            test_type="http",
            source="client",
            destination="server",
            success=True
        )
    ]
    
    return DeploymentResult(
        status="success",
        router_deployed=True,
        connectivity_established=True,
        tests=tests,
        summary=f"✅ Deployment exitoso para {request_data['router_id']} (simulado)"
    )

@activity.defn
async def cleanup_failed_deployment(request: NetworkDeploymentRequest) -> str:
    """Simula cleanup"""
    print(f"🧹 Simulando cleanup para {request.router_id}...")
    await asyncio.sleep(0.5)
    return f"Cleanup completed for {request.router_id} (simulated)"
