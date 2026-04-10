import asyncio
from datetime import timedelta
from temporalio import workflow
from models import NetworkDeploymentRequest

@workflow.defn
class NetworkDeploymentWithAnsibleRunner:
    
    @workflow.run
    async def run(self, request: NetworkDeploymentRequest) -> str:
        """
        Workflow simple que orquesta Ansible Runner + Airflow
        """
        
        try:
            # Step 1: Provisionar router via Ansible Runner
            infra_result = await workflow.execute_activity(
                "provision_router_via_ansible_runner",
                request,
                start_to_close_timeout=timedelta(minutes=10)
            )
            
            # Step 2: Configurar software via Airflow
            software_result = await workflow.execute_activity(
                "deploy_router_software",
                request,
                start_to_close_timeout=timedelta(minutes=15)
            )
            
            # Step 3: Validar despliegue
            validation_result = await workflow.execute_activity(
                "validate_router_deployment",
                request,
                start_to_close_timeout=timedelta(minutes=5)
            )
            
            return f"Router {request.router_id} deployed: {infra_result} -> {software_result} -> {validation_result}"
            
        except Exception as e:
            # Cleanup en caso de fallo
            await workflow.execute_activity(
                "cleanup_failed_deployment",
                request,
                start_to_close_timeout=timedelta(minutes=5)
            )
            raise