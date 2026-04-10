import asyncio
import httpx
import subprocess
from datetime import datetime
from temporalio import activity
from models import NetworkDeploymentRequest

class NetworkActivitiesWithSemaphore:
    
    @activity.defn
    async def provision_router_via_ansible_runner(self, request: NetworkDeploymentRequest) -> str:
        """Despliega router REAL usando SOLO Ansible Runner"""
        
        print("\n" + "="*80)
        print("🔧 ANSIBLE RUNNER: Desplegando Router Virtual REAL")
        print("="*80)
        activity.logger.info(f"[ANSIBLE RUNNER] Deploying router {request.router_id}")
        
        # SOLO usar Ansible Runner, sin fallback
        deployment_result = await self._deploy_via_ansible_runner(request)
        
        if deployment_result["success"]:
            print("✅ ROUTER DESPLEGADO VIA ANSIBLE RUNNER!")
            print(f"📋 Container: {request.router_id}")
            print("="*80)
            return f"[ANSIBLE RUNNER SUCCESS] Router {request.router_id} deployed at {request.router_ip}"
        else:
            print("❌ ANSIBLE RUNNER FALLÓ")
            print("="*80)
            raise Exception(f"Ansible Runner deployment failed: {deployment_result['error']}")
    
    async def _deploy_via_ansible_runner(self, request: NetworkDeploymentRequest) -> dict:
        """Despliega via Ansible Runner (SIN fallback)"""
        
        try:
            print(f"🔍 Ejecutando Ansible Runner...")
            
            # Verificar que el contenedor ansible-runner esté corriendo
            check_cmd = ["docker", "ps", "--filter", "name=ansible-runner", "--format", "{{.Names}}"]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            if "ansible-runner" not in check_result.stdout:
                return {"success": False, "error": "ansible-runner container not running"}
            
            print("✅ Contenedor ansible-runner encontrado")
            
            # Ejecutar ansible-playbook dentro del contenedor
            ansible_cmd = [
                "docker", "exec", "ansible-runner",
                "ansible-playbook", "/runner/project/deploy_router.yml",
                "-i", "/runner/project/inventory.ini",  # Agregar inventario
                "-e", f"router_id={request.router_id}",
                "-e", f"router_ip={request.router_ip}",
                "-v"  # verbose
            ]
            
            print(f"🚀 Ejecutando: {' '.join(ansible_cmd)}")
            
            result = subprocess.run(
                ansible_cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutos máximo
            )
            
            # Debug: Mostrar más información
            print(f"🔍 Debug - stdout: {result.stdout}")
            print(f"🔍 Debug - stderr: {result.stderr}")
            print(f"🔍 Debug - returncode: {result.returncode}")
            
            if result.returncode == 0:
                print("✅ Ansible playbook ejecutado exitosamente")
                print(f"Output: {result.stdout}")
                return {"success": True, "output": result.stdout}
            else:
                print(f"❌ Ansible playbook falló: {result.stderr}")
                return {"success": False, "error": f"Ansible failed: {result.stderr}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    

    async def _verify_router_container(self, router_id: str) -> dict:
        """Verifica que el container router existe y está corriendo"""
        
        try:
            print(f"🔍 Verificando container: {router_id}")
            
            result = subprocess.run([
                "docker", "ps", "--filter", f"name={router_id}", "--format", "{{.Names}}"
            ], capture_output=True, text=True)
            
            container_exists = router_id in result.stdout
            
            if container_exists:
                print(f"✅ Container {router_id} está corriendo")
                return {"exists": True, "status": "running"}
            else:
                print(f"❌ Container {router_id} no encontrado")
                return {"exists": False, "status": "not_found"}
                
        except Exception as e:
            return {"exists": False, "status": "error", "error": str(e)}
    
    @activity.defn
    async def deploy_router_software(self, request: NetworkDeploymentRequest) -> str:
        """Despliega software usando Airflow API REAL"""
        
        print("\n" + "="*80)
        print("🚀 AIRFLOW: Configurando Software en Router")
        print("="*80)
        activity.logger.info(f"[AIRFLOW] Configuring software on {request.router_id}")
        
        try:
            airflow_url = "http://localhost:8080"
            dag_id = "temporal_network_deployment"
            
            dag_config = {
                "router_id": request.router_id,
                "router_ip": request.router_ip,
                "software_version": request.software_version
            }
            
            print(f"📡 Conectando a Airflow: {airflow_url}")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                trigger_url = f"{airflow_url}/api/v1/dags/{dag_id}/dagRuns"
                
                trigger_data = {
                    "conf": dag_config,
                    "dag_run_id": f"temporal-{request.router_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                }
                
                print(f"🔥 TRIGGERING AIRFLOW DAG")
                
                response = await client.post(
                    trigger_url,
                    json=trigger_data,
                    auth=("admin", "admin"),
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    dag_run_info = response.json()
                    dag_run_id = dag_run_info["dag_run_id"]
                    
                    print(f"✅ DAG TRIGGERED: {dag_run_id}")
                    print("="*80)
                    return f"[AIRFLOW SUCCESS] Software {request.software_version} configured on {request.router_id} via DAG {dag_run_id}"
                else:
                    error_msg = f"Airflow DAG trigger failed: {response.status_code} - {response.text}"
                    print(f"❌ {error_msg}")
                    print("="*80)
                    raise Exception(error_msg)
                    
        except Exception as e:
            print(f"❌ AIRFLOW FALLÓ: {str(e)}")
            print("="*80)
            raise Exception(f"Airflow integration failed: {str(e)}")
    
    @activity.defn
    async def validate_router_deployment(self, request: NetworkDeploymentRequest) -> str:
        """Valida que el router esté desplegado y funcionando"""
        
        print("\n" + "="*80)
        print("🔍 VALIDACIÓN: Router Desplegado y Funcionando")
        print("="*80)
        activity.logger.info(f"Validating deployment for {request.router_id}")
        
        # Verificar container
        container_check = await self._verify_router_container(request.router_id)
        
        if not container_check["exists"]:
            error_msg = f"Router {request.router_id} container not found"
            print(f"❌ {error_msg}")
            print("="*80)
            raise Exception(error_msg)
        
        print(f"✅ Container {request.router_id} está corriendo")
        
        # Intentar ping desde el router
        try:
            ping_result = subprocess.run([
                "docker", "exec", request.router_id, "ping", "-c", "2", "8.8.8.8"
            ], capture_output=True, text=True, timeout=10)
            
            if ping_result.returncode == 0:
                print("✅ Router tiene conectividad de red")
                validation_status = "FULLY_OPERATIONAL"
            else:
                print("⚠️ Router sin conectividad externa")
                validation_status = "CONTAINER_ONLY"
                
        except Exception as e:
            print(f"⚠️ No se pudo verificar conectividad: {str(e)}")
            validation_status = "CONTAINER_ONLY"
        
        print("="*80)
        return f"Validation OK: Router {request.router_id} deployed and {validation_status}"
    
    @activity.defn
    async def cleanup_failed_deployment(self, request: NetworkDeploymentRequest) -> str:
        """Limpia recursos en caso de fallo"""
        
        print(f"\n🧹 CLEANUP: Limpiando recursos para {request.router_id}")
        activity.logger.info(f"Cleaning up failed deployment for {request.router_id}")
        
        try:
            # Remover container si existe
            subprocess.run([
                "docker", "rm", "-f", request.router_id
            ], capture_output=True)
            
            print(f"✅ Cleanup completado para {request.router_id}")
            return f"Cleanup completed for {request.router_id}"
        except Exception as e:
            print(f"❌ Cleanup falló: {str(e)}")
            return f"Cleanup failed for {request.router_id}: {str(e)}"

# Instanciar activities
activities = NetworkActivitiesWithSemaphore()
provision_router_via_ansible_runner = activities.provision_router_via_ansible_runner
deploy_router_software = activities.deploy_router_software
validate_router_deployment = activities.validate_router_deployment
cleanup_failed_deployment = activities.cleanup_failed_deployment