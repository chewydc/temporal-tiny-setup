#!/usr/bin/env python3

import asyncio
import subprocess
from models import NetworkDeploymentRequest

async def test_ansible_direct():
    """Test directo de la función de Ansible sin Temporal"""
    
    print("=" * 80)
    print("TEST DIRECTO DE ANSIBLE (SIN TEMPORAL)")
    print("=" * 80)
    
    # Simular el request
    request = NetworkDeploymentRequest(
        router_id="vrouter-connectivity-001",
        router_ip="192.168.1.1",
        software_version="frr-8.0",
        network_config={
            "client_network": "192.168.100.0/24",
            "server_network": "192.168.200.0/24"
        }
    )
    
    # Importar la función directamente
    from activities import NetworkActivitiesWithConnectivity
    activities = NetworkActivitiesWithConnectivity()
    
    try:
        print("Ejecutando _deploy_via_ansible_runner directamente...")
        result = await activities._deploy_via_ansible_runner(request)
        
        print(f"\nResultado: {result}")
        
        if result["success"]:
            print("\n✅ ANSIBLE DEPLOYMENT EXITOSO!")
            
            # Verificar que el router esté corriendo
            check_cmd = ["docker", "ps", "--filter", "name=vrouter-connectivity-001"]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)
            print(f"\nRouter status:\n{check_result.stdout}")
            
        else:
            print(f"\n❌ ANSIBLE DEPLOYMENT FALLO: {result['error']}")
            
    except Exception as e:
        print(f"\n💥 EXCEPCION: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_ansible_direct())