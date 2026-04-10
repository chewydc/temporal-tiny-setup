import asyncio
import httpx
import subprocess
from datetime import datetime
from temporalio import activity
from models import NetworkDeploymentRequest, ConnectivityTest, DeploymentResult

class NetworkActivitiesWithConnectivity:
    
    @activity.defn
    async def test_client_server_connectivity(self, test_phase: str) -> dict:
        """Prueba conectividad entre cliente y servidor"""
        
        print(f"\n{'='*80}")
        print(f"CONNECTIVITY TEST: {test_phase.upper()}")
        print(f"{'='*80}")


        tests = []
        
        # Test 1: Ping desde cliente a servidor
        ping_test = await self._test_ping("192.168.100.10", "192.168.200.10")
        tests.append(ping_test)
        
        # Test 2: HTTP desde cliente a servidor
        http_test = await self._test_http("192.168.100.10", "192.168.200.10")
        tests.append(http_test)
        
        successful_tests = sum(1 for test in tests if test["success"])
        
        print(f"Resultados: {successful_tests}/{len(tests)} tests exitosos")
        
        if test_phase == "initial_test":
            if successful_tests == 0:
                print("PERFECTO: Sin conectividad inicial (como esperado)")
                status = "expected_no_connectivity"
            else:
                print("INESPERADO: Hay conectividad inicial")
                status = "unexpected_connectivity"
        else:  # final_test
            if successful_tests > 0:
                print("EXCELENTE: Conectividad establecida despues del despliegue")
                status = "connectivity_established"
            else:
                print("PROBLEMA: Sin conectividad despues del despliegue")
                status = "no_connectivity_after_deployment"
        
        print(f"{'='*80}")
        
        return {
            "phase": test_phase,
            "status": status,
            "tests": tests,
            "successful_tests": successful_tests,
            "total_tests": len(tests)
        }
    
    async def _test_ping(self, source_ip: str, dest_ip: str) -> dict:
        """Test de ping desde cliente a servidor"""
        
        print(f"Testing ping: {source_ip} -> {dest_ip}")
        
        try:
            result = subprocess.run([
                "docker", "exec", "test-client", 
                "ping", "-c", "2", "-W", "2", dest_ip
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"   Ping exitoso")
                return {
                    "test_type": "ping",
                    "source": source_ip,
                    "destination": dest_ip,
                    "success": True,
                    "output": result.stdout
                }
            else:
                print(f"   Ping fallo: {result.stderr}")
                return {
                    "test_type": "ping",
                    "source": source_ip,
                    "destination": dest_ip,
                    "success": False,
                    "error": result.stderr
                }
                
        except Exception as e:
            print(f"   Error en ping: {str(e)}")
            return {
                "test_type": "ping",
                "source": source_ip,
                "destination": dest_ip,
                "success": False,
                "error": str(e)
            }
    
    async def _test_http(self, source_ip: str, dest_ip: str) -> dict:
        """Test HTTP desde cliente a servidor"""
        
        print(f"Testing HTTP: {source_ip} -> http://{dest_ip}")
        
        try:
            result = subprocess.run([
                "docker", "exec", "test-client",
                "wget", "-q", "-O", "-", f"http://{dest_ip}", "--timeout=5"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and "Servidor Test" in result.stdout:
                print(f"   HTTP exitoso")
                return {
                    "test_type": "http",
                    "source": source_ip,
                    "destination": f"http://{dest_ip}",
                    "success": True,
                    "response": result.stdout[:100] + "..." if len(result.stdout) > 100 else result.stdout
                }
            else:
                print(f"   HTTP fallo")
                return {
                    "test_type": "http",
                    "source": source_ip,
                    "destination": f"http://{dest_ip}",
                    "success": False,
                    "error": result.stderr or "No response"
                }
                
        except Exception as e:
            print(f"   Error en HTTP: {str(e)}")
            return {
                "test_type": "http",
                "source": source_ip,
                "destination": f"http://{dest_ip}",
                "success": False,
                "error": str(e)
            }
    
    @activity.defn
    async def provision_router_via_ansible_runner(self, request: NetworkDeploymentRequest) -> str:
        """Despliega router usando Ansible Runner (basado en Caso 3)"""
        
        print("\n" + "="*80)
        print("ANSIBLE RUNNER: Desplegando Router Virtual")
        print("="*80)
        
        deployment_result = await self._deploy_via_ansible_runner(request)
        
        if deployment_result["success"]:
            print("ROUTER DESPLEGADO VIA ANSIBLE RUNNER!")
            print(f"Container: {request.router_id}")
            print("="*80)
            return f"Router {request.router_id} deployed at {request.router_ip}"
        else:
            print("ANSIBLE RUNNER FALLO")
            print("="*80)
            raise Exception(f"Ansible Runner deployment failed: {deployment_result['error']}")
    
    async def _deploy_via_ansible_runner(self, request: NetworkDeploymentRequest) -> dict:
        """Despliega via Ansible Runner (copiado del Caso 3)"""
        
        try:
            print("Ejecutando Ansible Runner...")
            
            # Forzar el uso del contexto desktop-linux para evitar problemas de conexión
            check_cmd = ["docker", "--context", "desktop-linux", "ps", "--filter", "name=ansible-runner", "--format", "{{.Names}}"]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            print(f"DEBUG: Container check - RC: {check_result.returncode}, STDOUT: '{check_result.stdout.strip()}', STDERR: '{check_result.stderr.strip()}'")
            
            if check_result.returncode != 0:
                return {"success": False, "error": f"Docker command failed: {check_result.stderr}"}
            
            if "ansible-runner" not in check_result.stdout:
                return {"success": False, "error": f"ansible-runner container not found. Available containers: {check_result.stdout.strip()}"}
            
            print("Contenedor ansible-runner encontrado")
            
            # Verificar si el router ya existe y eliminarlo
            cleanup_cmd = ["docker", "--context", "desktop-linux", "rm", "-f", request.router_id]
            subprocess.run(cleanup_cmd, capture_output=True)
            print(f"Limpieza previa del router {request.router_id}")
            
            ansible_cmd = [
                "docker", "--context", "desktop-linux", "exec", "ansible-runner",
                "ansible-playbook", "/runner/project/deploy_router.yml",
                "-i", "/runner/project/inventory.ini",
                "-e", f"router_id={request.router_id}",
                "-e", f"router_ip={request.router_ip}",
                "-v"
            ]
            
            print(f"Ejecutando: {' '.join(ansible_cmd)}")
            
            result = subprocess.run(
                ansible_cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                print("Ansible playbook ejecutado exitosamente")
                print(f"STDOUT: {result.stdout}")
                return {"success": True, "output": result.stdout}
            else:
                print(f"Ansible playbook fallo con codigo: {result.returncode}")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                return {"success": False, "error": f"RC:{result.returncode} STDOUT:{result.stdout} STDERR:{result.stderr}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @activity.defn
    async def configure_client_server_routes(self, request: NetworkDeploymentRequest) -> str:
        """Configura rutas estaticas en cliente y servidor"""
        
        print(f"\n{'='*80}")
        print("CONFIGURANDO RUTAS CLIENTE-SERVIDOR")
        print(f"{'='*80}")
        
        try:
            # Configurar ruta en cliente
            print("Configurando ruta en cliente...")
            client_route_cmd = [
                "docker", "exec", "test-client", 
                "ip", "route", "add", "192.168.200.0/24", "via", "192.168.100.2"
            ]
            client_result = subprocess.run(client_route_cmd, capture_output=True, text=True)
            
            # Configurar ruta en servidor
            print("Configurando ruta en servidor...")
            server_route_cmd = [
                "docker", "exec", "test-server", 
                "ip", "route", "add", "192.168.100.0/24", "via", "192.168.200.2"
            ]
            server_result = subprocess.run(server_route_cmd, capture_output=True, text=True)
            
            # Returncode 2 significa que la ruta ya existe, lo cual es OK
            client_ok = client_result.returncode == 0 or client_result.returncode == 2
            server_ok = server_result.returncode == 0 or server_result.returncode == 2
            
            if client_ok and server_ok:
                print("Rutas configuradas exitosamente")
                return f"Routes configured: client and server can reach each other via {request.router_id}"
            else:
                print(f"Error: client={client_result.returncode}, server={server_result.returncode}")
                print(f"Client stderr: {client_result.stderr}")
                print(f"Server stderr: {server_result.stderr}")
                raise Exception(f"Route configuration failed: client={client_result.returncode}, server={server_result.returncode}")
                
        except Exception as e:
            print(f"Error configurando rutas: {str(e)}")
            raise Exception(f"Route configuration failed: {str(e)}")
    
    @activity.defn
    async def wait_for_manual_verification(self, message: str) -> str:
        """Pausa el workflow para verificación manual"""
        
        print(f"\n{'='*80}")
        print("PAUSA PARA VERIFICACION MANUAL")
        print(f"{'='*80}")
        print(message)
        print("\nPuedes probar ahora:")
        print("  docker exec test-client ping -c 2 -W 2 192.168.200.10")
        print("  docker exec vrouter-connectivity-001 vtysh -c 'show ip route'")
        print("\nPresiona ENTER para continuar...")
        
        input()  # Espera input del usuario
        
        print("Continuando workflow...")
        print(f"{'='*80}")
        return "Manual verification completed"
    
    @activity.defn
    async def deploy_router_software(self, request: NetworkDeploymentRequest) -> str:
        """Despliega software usando Airflow API y espera finalización"""
        
        print("\n" + "="*80)
        print("AIRFLOW: Configurando Software en Router")
        print("="*80)
        
        try:
            airflow_url = "http://localhost:8081"
            dag_id = "temporal_router_config"
            
            dag_config = {
                "router_id": request.router_id,
                "router_ip": request.router_ip,
                "software_version": request.software_version
            }
            
            print(f"Conectando a Airflow: {airflow_url}")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                trigger_url = f"{airflow_url}/api/v1/dags/{dag_id}/dagRuns"
                
                trigger_data = {
                    "conf": dag_config,
                    "dag_run_id": f"temporal-{request.router_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                }
                
                print(f"TRIGGERING AIRFLOW DAG")
                
                response = await client.post(
                    trigger_url,
                    json=trigger_data,
                    auth=("admin", "admin"),
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    dag_run_info = response.json()
                    dag_run_id = dag_run_info["dag_run_id"]
                    
                    print(f"DAG TRIGGERED: {dag_run_id}")
                    print("⏳ Esperando finalización del DAG...")
                    
                    # NUEVO: Esperar finalización del DAG
                    final_state = await self._wait_for_dag_completion(client, airflow_url, dag_id, dag_run_id)
                    
                    if final_state == "success":
                        print(f"✅ DAG completado exitosamente: {dag_run_id}")
                        print("="*80)
                        return f"Software {request.software_version} configured on {request.router_id} via DAG {dag_run_id}"
                    else:
                        error_msg = f"DAG failed with state: {final_state}"
                        print(f"❌ {error_msg}")
                        print("="*80)
                        raise Exception(error_msg)
                else:
                    error_msg = f"Airflow DAG trigger failed: {response.status_code} - {response.text}"
                    print(f"{error_msg}")
                    print("="*80)
                    raise Exception(error_msg)
                    
        except Exception as e:
            print(f"AIRFLOW FALLO: {str(e)}")
            print("="*80)
            raise Exception(f"Airflow integration failed: {str(e)}")
    
    async def _wait_for_dag_completion(self, client, airflow_url: str, dag_id: str, dag_run_id: str, max_wait_minutes: int = 10) -> str:
        """Espera a que el DAG complete y retorna el estado final"""
        
        status_url = f"{airflow_url}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}"
        max_attempts = max_wait_minutes * 6  # Check every 10 seconds
        
        for attempt in range(max_attempts):
            try:
                response = await client.get(
                    status_url,
                    auth=("admin", "admin")
                )
                
                if response.status_code == 200:
                    dag_run = response.json()
                    state = dag_run.get("state")
                    
                    print(f"📊 DAG State: {state} (attempt {attempt + 1}/{max_attempts})")
                    
                    if state in ["success", "failed"]:
                        return state
                    elif state in ["running", "queued"]:
                        await asyncio.sleep(10)  # Wait 10 seconds
                        continue
                    else:
                        print(f"⚠️ Unknown DAG state: {state}")
                        await asyncio.sleep(10)
                        continue
                else:
                    print(f"❌ Error checking DAG status: {response.status_code}")
                    await asyncio.sleep(10)
                    continue
                    
            except Exception as e:
                print(f"⚠️ Error polling DAG status: {str(e)}")
                await asyncio.sleep(10)
                continue
        
        # Timeout reached
        print(f"⏰ Timeout waiting for DAG completion after {max_wait_minutes} minutes")
        return "timeout"
    
    @activity.defn
    async def generate_deployment_report(self, data: dict) -> DeploymentResult:
        """Genera reporte final del despliegue"""
        
        request_data = data["request"]
        initial_test = data["initial_test"]
        final_test = data["final_test"]
        
        all_tests = []
        
        for test in initial_test["tests"]:
            all_tests.append(ConnectivityTest(
                test_type=f"initial_{test['test_type']}",
                source=test["source"],
                destination=test["destination"],
                success=test["success"],
                error_message=test.get("error")
            ))
        
        for test in final_test["tests"]:
            all_tests.append(ConnectivityTest(
                test_type=f"final_{test['test_type']}",
                source=test["source"],
                destination=test["destination"],
                success=test["success"],
                error_message=test.get("error")
            ))
        
        router_deployed = True
        connectivity_established = final_test["successful_tests"] > 0
        
        if connectivity_established and initial_test["successful_tests"] == 0:
            status = "success"
            summary = f"EXITO COMPLETO: Router {request_data['router_id']} desplegado y conectividad establecida"
        elif connectivity_established:
            status = "success"
            summary = f"EXITO: Router {request_data['router_id']} desplegado y conectividad funcional"
        else:
            status = "partial"
            summary = f"PARCIAL: Router {request_data['router_id']} desplegado pero sin conectividad"
        
        return DeploymentResult(
            status=status,
            router_deployed=router_deployed,
            connectivity_established=connectivity_established,
            tests=all_tests,
            summary=summary
        )
    
    @activity.defn
    async def cleanup_failed_deployment(self, request: NetworkDeploymentRequest) -> str:
        """Limpia recursos en caso de fallo"""
        
        print(f"\nCLEANUP: Limpiando recursos para {request.router_id}")
        
        try:
            subprocess.run([
                "docker", "rm", "-f", request.router_id
            ], capture_output=True)
            
            print(f"Cleanup completado para {request.router_id}")
            return f"Cleanup completed for {request.router_id}"
        except Exception as e:
            print(f"Cleanup fallo: {str(e)}")
            return f"Cleanup failed for {request.router_id}: {str(e)}"

# Instanciar activities
activities = NetworkActivitiesWithConnectivity()
test_client_server_connectivity = activities.test_client_server_connectivity
provision_router_via_ansible_runner = activities.provision_router_via_ansible_runner
configure_client_server_routes = activities.configure_client_server_routes
wait_for_manual_verification = activities.wait_for_manual_verification
deploy_router_software = activities.deploy_router_software
generate_deployment_report = activities.generate_deployment_report
cleanup_failed_deployment = activities.cleanup_failed_deployment