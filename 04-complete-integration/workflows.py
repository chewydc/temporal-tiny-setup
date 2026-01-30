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
            
            # Step 2: Deploy router (sin retry loop)
            infra_result = await workflow.execute_activity(
                "provision_router_via_ansible_runner",
                request,
                start_to_close_timeout=timedelta(minutes=10)
            )
            
            # Step 3: PAUSA
            workflow.logger.info("🔄 ROUTER OK - Esperando signal para continuar...")
            await workflow.wait_condition(
                lambda: self._continue_deployment,
                timeout=timedelta(minutes=30)
            )
            
            # Step 4: Airflow (sin retry loop)
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