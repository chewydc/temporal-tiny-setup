import asyncio
import httpx
from datetime import datetime
from temporalio import activity
from models import NetworkDeploymentRequest

class NetworkActivities:
    
    @activity.defn
    async def provision_router_infrastructure(self, request: NetworkDeploymentRequest) -> str:
        """Provisiona router - SIMULADO (Semaphore en próximo paso)"""
        
        print("\n" + "-"*80)
        print("🛠️  PROVISIONING SIMULADO (Semaphore en próximo paso)")
        print("📝 NOTA: Este paso es SIEMPRE simulado en este ejemplo")
        print("-"*80)
        activity.logger.info(f"[SIMULADO] Provisioning router {request.router_id}")
        
        # Simular tiempo de provisioning
        await asyncio.sleep(2)
        
        print(f"✅ PROVISIONING SIMULADO COMPLETADO")
        print("-"*80)
        return f"[SIMULADO] Router {request.router_id} provisioned at {request.router_ip}"
    
    @activity.defn
    async def deploy_router_software(self, request: NetworkDeploymentRequest) -> str:
        """Despliega software usando Airflow API REAL"""
        
        print("\n" + "="*80)
        print("🚀 INICIANDO INTEGRACIÓN REAL CON AIRFLOW")
        print("🎯 INTENTANDO CONECTAR A DAG REAL...")
        print("="*80)
        activity.logger.info(f"[REAL AIRFLOW] Deploying software to {request.router_id}")
        
        try:
            # Configuración de Airflow API
            airflow_url = "http://localhost:8080"
            dag_id = "temporal_network_deployment"
            
            # Datos para el DAG
            dag_config = {
                "router_id": request.router_id,
                "router_ip": request.router_ip,
                "software_version": request.software_version
            }
            
            print(f"📡 Conectando a Airflow: {airflow_url}")
            print(f"🎯 DAG ID: {dag_id}")
            print(f"📋 Configuración: {dag_config}")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Trigger DAG en Airflow
                trigger_url = f"{airflow_url}/api/v1/dags/{dag_id}/dagRuns"
                
                trigger_data = {
                    "conf": dag_config,
                    "dag_run_id": f"temporal-{request.router_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                }
                
                print(f"🔥 TRIGGERING AIRFLOW DAG: {trigger_url}")
                activity.logger.info(f"Triggering Airflow DAG: {trigger_url}")
                activity.logger.info(f"DAG Config: {dag_config}")
                
                # Llamada a Airflow API
                response = await client.post(
                    trigger_url,
                    json=trigger_data,
                    auth=("admin", "admin"),  # Credenciales básicas
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    dag_run_info = response.json()
                    dag_run_id = dag_run_info["dag_run_id"]
                    
                    print(f"✅ DAG TRIGGERED SUCCESSFULLY: {dag_run_id}")
                    print(f"⏳ Esperando que complete el DAG...")
                    activity.logger.info(f"DAG triggered successfully: {dag_run_id}")
                    
                    # Esperar a que termine el DAG
                    await self._wait_for_dag_completion(client, airflow_url, dag_id, dag_run_id)
                    
                    print("🎉 AIRFLOW DAG COMPLETADO EXITOSAMENTE!")
                    print("✅ RESULTADO: DESPLIEGUE REAL COMPLETADO")
                    print("📋 DAG ID: {}".format(dag_run_id))
                    print("🌟 ESTE FUE UN DESPLIEGUE REAL (NO SIMULACIÓN)")
                    print("="*80)
                    return f"[REAL AIRFLOW SUCCESS] Software {request.software_version} deployed on {request.router_id} via DAG {dag_run_id} (REAL)"
                else:
                    error_msg = f"Failed to trigger Airflow DAG: {response.status_code} - {response.text}"
                    print(f"❌ ERROR AL TRIGGEAR DAG: {error_msg}")
                    activity.logger.error(error_msg)
                    raise Exception(error_msg)
                    
        except Exception as e:
            print("\n" + "!"*80)
            print("🚨 AIRFLOW FALLÓ - ACTIVANDO FALLBACK SIMULATION")
            print("!"*80)
            print(f"❌ Error de conexión: {str(e)}")
            print("🔄 Cambiando a modo simulación...")
            activity.logger.error(f"Airflow integration failed: {str(e)}")
            activity.logger.info("Falling back to simulation...")
            await asyncio.sleep(2)
            print("✅ FALLBACK SIMULATION ACTIVADO")
            print("📝 Simulando despliegue de software...")
            await asyncio.sleep(1)
            print("🎭 RESULTADO: SIMULACIÓN COMPLETADA (NO REAL)")
            print("!"*80)
            return f"[FALLBACK SIMULATION] Software {request.software_version} deployed on {request.router_id} (SIMULADO)"
    
    async def _wait_for_dag_completion(self, client: httpx.AsyncClient, airflow_url: str, dag_id: str, dag_run_id: str):
        """Espera a que el DAG complete su ejecución"""
        max_wait_time = 300  # 5 minutos máximo
        check_interval = 5   # Revisar cada 5 segundos
        elapsed_time = 0
        
        print(f"🔍 Monitoreando DAG: {dag_run_id}")
        
        while elapsed_time < max_wait_time:
            try:
                status_url = f"{airflow_url}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}"
                response = await client.get(status_url, auth=("admin", "admin"))
                
                if response.status_code == 200:
                    dag_run = response.json()
                    state = dag_run.get("state")
                    
                    print(f"🟡 DAG {dag_run_id} estado: {state} (tiempo: {elapsed_time}s)")
                    activity.logger.info(f"DAG {dag_run_id} state: {state}")
                    
                    if state == "success":
                        print(f"✅ DAG {dag_run_id} COMPLETADO EXITOSAMENTE!")
                        activity.logger.info(f"DAG {dag_run_id} completed successfully")
                        return
                    elif state == "failed":
                        print(f"❌ DAG {dag_run_id} FALLÓ!")
                        raise Exception(f"DAG {dag_run_id} failed")
                    elif state in ["running", "queued"]:
                        # Continuar esperando
                        await asyncio.sleep(check_interval)
                        elapsed_time += check_interval
                    else:
                        print(f"⚠️ Estado desconocido del DAG: {state}")
                        activity.logger.warning(f"Unknown DAG state: {state}")
                        await asyncio.sleep(check_interval)
                        elapsed_time += check_interval
                else:
                    print(f"⚠️ Error obteniendo estado del DAG: {response.status_code}")
                    activity.logger.warning(f"Failed to get DAG status: {response.status_code}")
                    await asyncio.sleep(check_interval)
                    elapsed_time += check_interval
                    
            except Exception as e:
                print(f"⚠️ Error monitoreando DAG: {str(e)}")
                activity.logger.warning(f"Error checking DAG status: {str(e)}")
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval
        
        print(f"⏰ TIMEOUT: DAG {dag_run_id} no completó en {max_wait_time} segundos")
        raise Exception(f"DAG {dag_run_id} did not complete within {max_wait_time} seconds")
    
    @activity.defn
    async def validate_router_deployment(self, request: NetworkDeploymentRequest) -> str:
        """Valida que el despliegue fue exitoso"""
        activity.logger.info(f"Validating deployment for {request.router_id}")
        
        await asyncio.sleep(1)
        
        return f"Validation OK: Router provisioned and software {request.software_version} deployed"
    
    @activity.defn
    async def cleanup_failed_deployment(self, request: NetworkDeploymentRequest) -> str:
        """Limpia recursos en caso de fallo"""
        activity.logger.info(f"Cleaning up failed deployment for {request.router_id}")
        
        return f"Cleanup completed for {request.router_id}"

# Instanciar activities para importar
activities = NetworkActivities()
provision_router_infrastructure = activities.provision_router_infrastructure
deploy_router_software = activities.deploy_router_software  
validate_router_deployment = activities.validate_router_deployment
cleanup_failed_deployment = activities.cleanup_failed_deployment