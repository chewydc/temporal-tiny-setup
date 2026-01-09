import asyncio
from datetime import timedelta
from temporalio import workflow
from models import NetworkDeploymentRequest, DeploymentResult

@workflow.defn
class NetworkDeploymentWithConnectivity:
    
    def __init__(self) -> None:
        self._continue_deployment = False
    
    @workflow.signal
    def enter(self) -> None:
        """Signal para continuar con el despliegue desde la web UI"""
        self._continue_deployment = True
    
    @workflow.run
    async def run(self, request: NetworkDeploymentRequest) -> DeploymentResult:
        """
        Workflow con retry inteligente basado en tipo de fallo:
        - Si falla PING: retry router deployment
        - Si falla HTTP: retry Airflow DAG
        """
        
        try:
            # Step 1: Test inicial
            initial_test = await workflow.execute_activity(
                "test_client_server_connectivity",
                "initial_test",
                start_to_close_timeout=timedelta(minutes=5)
            )
            
            # Step 2: Deploy router con retry inteligente
            max_router_retries = 3
            for router_attempt in range(max_router_retries):
                try:
                    # Provisionar router
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
                    
                    # Si PING falla, retry router deployment
                    if not post_router_test.get('ping_success', False):
                        workflow.logger.warning(f"❌ PING falló - Retry router {router_attempt + 1}/{max_router_retries}")
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
            
            # Step 3: PAUSA
            workflow.logger.info("🔄 ROUTER OK - Esperando signal para continuar...")
            await workflow.wait_condition(
                lambda: self._continue_deployment,
                timeout=timedelta(minutes=30)
            )
            
            # Step 4: Airflow con retry inteligente
            max_airflow_retries = 3
            final_test = None
            for airflow_attempt in range(max_airflow_retries):
                try:
                    # Configurar via Airflow
                    software_result = await workflow.execute_activity(
                        "deploy_router_software",
                        request,
                        start_to_close_timeout=timedelta(minutes=15)
                    )
                    
                    # Test final
                    final_test = await workflow.execute_activity(
                        "test_client_server_connectivity",
                        "final_test",
                        start_to_close_timeout=timedelta(minutes=5)
                    )
                    
                    # Si HTTP falla pero PING funciona, retry solo Airflow
                    if final_test.get('ping_success', False) and not final_test.get('http_success', False):
                        workflow.logger.warning(f"❌ HTTP falló - Retry Airflow {airflow_attempt + 1}/{max_airflow_retries}")
                        if airflow_attempt < max_airflow_retries - 1:
                            continue
                        else:
                            workflow.logger.error("Airflow configuration failed after all retries")
                            break
                    
                    workflow.logger.info("✅ Conectividad completa")
                    break
                    
                except Exception as e:
                    if airflow_attempt < max_airflow_retries - 1:
                        workflow.logger.warning(f"Airflow deployment failed, retrying... {e}")
                        continue
                    workflow.logger.error(f"Airflow failed after all retries: {e}")
                    # Hacer un test final para el reporte
                    final_test = await workflow.execute_activity(
                        "test_client_server_connectivity",
                        "final_test_after_failure",
                        start_to_close_timeout=timedelta(minutes=5)
                    )
            
            # Step 5: Reporte final
            report_data = {
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
            # Cleanup en caso de fallo
            await workflow.execute_activity(
                "cleanup_failed_deployment",
                request,
                start_to_close_timeout=timedelta(minutes=5)
            )
            raise