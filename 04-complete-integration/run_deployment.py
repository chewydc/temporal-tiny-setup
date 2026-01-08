import asyncio
from datetime import datetime
from temporalio.client import Client
from models import NetworkDeploymentRequest

async def run_connectivity_demo():
    """
    Demo completo que muestra:
    1. ANTES: Sin conectividad cliente-servidor
    2. Despliegue del router con Temporal + Ansible
    3. DESPUES: Con conectividad cliente-servidor
    """
    
    print("=" * 80)
    print("CASO 04: DEMOSTRACION DE CONECTIVIDAD CLIENTE-SERVIDOR")
    print("=" * 80)
    print("Escenario:")
    print("  Cliente: 192.168.100.10 (red aislada)")
    print("  Servidor: 192.168.200.10 (red aislada)")
    print("  Solucion: Router virtual que conecta ambas redes")
    print()
    
    try:
        # Conectar a Temporal
        client = await Client.connect("localhost:7233")
        print("Conectado a Temporal Server")
        
        # Crear request de despliegue
        deployment_id = f"connectivity_demo_{int(datetime.now().timestamp())}"
        
        deployment_request = NetworkDeploymentRequest(
            router_id="vrouter-connectivity-001",
            router_ip="192.168.1.1",  # IP de gestion
            software_version="frr-8.0",
            network_config={
                "client_network": "192.168.100.0/24",
                "server_network": "192.168.200.0/24"
            }
        )
        
        print(f"Iniciando demo de conectividad: {deployment_id}")
        print(f"   Router: {deployment_request.router_id}")
        print(f"   Cliente: 192.168.100.10")
        print(f"   Servidor: 192.168.200.10")
        print()
        
        # Ejecutar workflow
        print("Ejecutando workflow de conectividad...")
        result = await client.execute_workflow(
            "NetworkDeploymentWithConnectivity",
            deployment_request,
            id=f"connectivity-workflow-{deployment_id}",
            task_queue="caso04-connectivity-queue"
        )
        
        # Mostrar resultados
        print("\\n" + "=" * 80)
        print("RESULTADOS DE LA DEMOSTRACION")
        print("=" * 80)
        print(f"Estado: {result.status.upper()}")
        print(f"Router desplegado: {'SI' if result.router_deployed else 'NO'}")
        print(f"Conectividad establecida: {'SI' if result.connectivity_established else 'NO'}")
        print()
        
        # Mostrar tests detallados
        print("TESTS DE CONECTIVIDAD:")
        initial_tests = [t for t in result.tests if t.test_type.startswith("initial_")]
        final_tests = [t for t in result.tests if t.test_type.startswith("final_")]
        
        print("\\n   ANTES del despliegue:")
        for test in initial_tests:
            status = "OK" if test.success else "FAIL"
            test_name = test.test_type.replace("initial_", "").upper()
            print(f"      {status} {test_name}: {test.source} -> {test.destination}")
            if not test.success and test.error_message:
                print(f"         Error: {test.error_message}")
        
        print("\\n   DESPUES del despliegue:")
        for test in final_tests:
            status = "OK" if test.success else "FAIL"
            test_name = test.test_type.replace("final_", "").upper()
            print(f"      {status} {test_name}: {test.source} -> {test.destination}")
            if not test.success and test.error_message:
                print(f"         Error: {test.error_message}")
        
        print(f"\\nResumen: {result.summary}")
        
        if result.connectivity_established:
            print("\\nDEMOSTRACION EXITOSA!")
            print("   El router virtual conecto exitosamente las redes aisladas")
            print("   Puedes verificar manualmente:")
            print("   - docker exec test-client ping 192.168.200.10")
            print("   - docker exec test-client wget -q -O - http://192.168.200.10")
            print("   - Servidor web: http://localhost:8080")
        else:
            print("\\nLa conectividad no se establecio completamente")
            print("   Revisa los logs para mas detalles")
        
        return result
        
    except Exception as e:
        print(f"Error ejecutando demo: {str(e)}")
        print("   Verifica que:")
        print("   - Docker Compose este corriendo: docker-compose ps")
        print("   - Temporal Worker este activo: python run_worker.py")
        print("   - Los containers cliente y servidor existan")
        return None

async def manual_connectivity_test():
    """
    Test manual rapido de conectividad (sin workflow)
    """
    
    print("=" * 80)
    print("TEST MANUAL DE CONECTIVIDAD")
    print("=" * 80)
    
    import subprocess
    
    print("Probando conectividad cliente -> servidor...")
    
    # Test ping
    try:
        result = subprocess.run([
            "docker", "exec", "test-client", 
            "ping", "-c", "3", "192.168.200.10"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("PING: Cliente puede alcanzar servidor")
        else:
            print("PING: Cliente NO puede alcanzar servidor")
            print(f"   Error: {result.stderr}")
    except Exception as e:
        print(f"Error en test de ping: {str(e)}")
    
    # Test HTTP
    try:
        result = subprocess.run([
            "docker", "exec", "test-client",
            "wget", "-q", "-O", "-", "http://192.168.200.10", "--timeout=5"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and "Servidor Test" in result.stdout:
            print("HTTP: Cliente puede acceder al servidor web")
        else:
            print("HTTP: Cliente NO puede acceder al servidor web")
    except Exception as e:
        print(f"Error en test HTTP: {str(e)}")

if __name__ == "__main__":
    # Ejecutar directamente el demo completo
    asyncio.run(run_connectivity_demo())