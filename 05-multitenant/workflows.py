import asyncio
from datetime import timedelta
from temporalio import workflow
from models import NetworkDeploymentRequest, DeploymentResult

@workflow.defn
class NetworkDeploymentWorkflow:
    """Workflow de deployment con soporte multitenant"""
    
    def __init__(self) -> None:
        self._continue_deployment = False
    
    @workflow.signal
    def approve_deployment(self) -> None:
        """Signal para aprobar y continuar con el despliegue"""
        self._continue_deployment = True
    
    @workflow.run
    async def run(self, request: NetworkDeploymentRequest) -> DeploymentResult:
        """
        Workflow multitenant de deployment de routers.
        
        Características multitenant:
        - Ejecuta en task queue específica del tenant
        - Workflow ID incluye tenant_id para evitar colisiones
        - Search attributes permiten filtrar por tenant
        - Retry inteligente basado en tipo de fallo
        """
        
        tenant_id = request.tenant_id
        workflow.logger.info(f"🏢 Tenant: {tenant_id} | Router: {request.router_id}")
        
        try:
            # Step 1: Test inicial de conectividad
            initial_test = await workflow.execute_activity(
                "test_client_server_connectivity",
                "initial_test",
                start_to_close_timeout=timedelta(minutes=5)
            )
            
            # Step 2: Deploy router con retry inteligente
            max_router_retries = 3
            for router_attempt in range(max_router_retries):
                try:
                    infra_result = await workflow.execute_activity(
                        "provision_router_via_ansible_runner",
                        request,
                        start_to_close_timeout=timedelta(minutes=10)
                    )
                    
                    # Test post-router (debe tener PING)
                    post_router_test = await workflow.execute_activity(
                        "test_client_server_connectivity",
                        "post_router_test",
                        start_to_close_timeout=timedelta(minutes=5)
                    )
                    
                    # Verificar si PING funciona
                    ping_works = any(test.get('test_type') == 'ping' and test.get('success', False) 
                                   for test in post_router_test.get('tests', []))
                    
                    if not ping_works:
                        workflow.logger.warning(f"❌ PING falló - Retry {router_attempt + 1}/{max_router_retries}")
                        if router_attempt < max_router_retries - 1:
                            continue
                        else:
                            raise Exception("Router deployment failed after all retries")
                    
                    workflow.logger.info("✅ Router OK - PING funciona")
                    break
                    
                except Exception as e:
                    if router_attempt < max_router_retries - 1:
                        workflow.logger.warning(f"Router deployment failed, retrying... {e}")
                        continue
                    raise
            
            # Step 3: Esperar aprobación manual (opcional)
            workflow.logger.info(f"⏸️  Esperando aprobación para tenant {tenant_id}...")
            await workflow.wait_condition(
                lambda: self._continue_deployment,
                timeout=timedelta(minutes=30)
            )
            
            # Step 4: Configuración de software con retry
            max_airflow_retries = 3
            final_test = None
            for airflow_attempt in range(max_airflow_retries):
                try:
                    software_result = await workflow.execute_activity(
                        "deploy_router_software",
                        request,
                        start_to_close_timeout=timedelta(minutes=15)
                    )
                    
                    final_test = await workflow.execute_activity(
                        "test_client_server_connectivity",
                        "final_test",
                        start_to_close_timeout=timedelta(minutes=5)
                    )
                    
                    # Verificar conectividad completa
                    ping_works = any(test.get('test_type') == 'ping' and test.get('success', False) 
                                   for test in final_test.get('tests', []))
                    http_works = any(test.get('test_type') == 'http' and test.get('success', False) 
                                   for test in final_test.get('tests', []))
                    
                    if ping_works and not http_works:
                        workflow.logger.warning(f"❌ HTTP falló - Retry {airflow_attempt + 1}/{max_airflow_retries}")
                        if airflow_attempt < max_airflow_retries - 1:
                            await asyncio.sleep(60)
                            continue
                        else:
                            workflow.logger.error("Airflow configuration failed after all retries")
                            break
                    
                    workflow.logger.info("✅ Conectividad completa")
                    break
                    
                except Exception as e:
                    if airflow_attempt < max_airflow_retries - 1:
                        workflow.logger.warning(f"Airflow deployment failed, retrying... {e}")
                        await asyncio.sleep(60)
                        continue
                    workflow.logger.error(f"Airflow failed: {e}")
                    final_test = await workflow.execute_activity(
                        "test_client_server_connectivity",
                        "final_test_after_failure",
                        start_to_close_timeout=timedelta(minutes=5)
                    )
            
            # Step 5: Reporte final
            report_data = {
                "tenant_id": tenant_id,
                "request": {
                    "router_id": request.router_id,
                    "router_ip": request.router_ip,
                    "software_version": request.software_version
                },
                "initial_test": initial_test,
                "final_test": final_test
            }
            
            deployment_report = await workflow.execute_activity(
                "generate_deployment_report",
                report_data,
                start_to_close_timeout=timedelta(minutes=2)
            )
            
            return deployment_report
            
        except Exception as e:
            workflow.logger.error(f"❌ Deployment failed for tenant {tenant_id}: {e}")
            await workflow.execute_activity(
                "cleanup_failed_deployment",
                request,
                start_to_close_timeout=timedelta(minutes=5)
            )
            raise