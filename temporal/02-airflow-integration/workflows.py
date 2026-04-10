from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from models import NetworkDeploymentRequest

# Import activities properly
with workflow.unsafe.imports_passed_through():
    from activities import (
        provision_router_infrastructure,
        deploy_router_software,
        validate_router_deployment,
        cleanup_failed_deployment
    )

@workflow.defn
class NetworkDeploymentWorkflow:
    @workflow.run
    async def run(self, request: NetworkDeploymentRequest) -> str:
        """
        Workflow que orquesta:
        1. Provisioning con Semaphore/Ansible
        2. Software deployment con Airflow
        3. Validación final
        """
        
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            maximum_interval=timedelta(seconds=30)
        )
        
        try:
            # 1. Provisionar infraestructura con Semaphore
            workflow.logger.info(f"Starting provisioning for {request.router_id}")
            provision_result = await workflow.execute_activity(
                provision_router_infrastructure,
                request,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=retry_policy
            )
            
            # 2. Desplegar software con Airflow
            workflow.logger.info(f"Starting software deployment for {request.router_id}")
            deployment_result = await workflow.execute_activity(
                deploy_router_software,
                request,
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=retry_policy
            )
            
            # 3. Validación final
            workflow.logger.info(f"Validating deployment for {request.router_id}")
            validation_result = await workflow.execute_activity(
                validate_router_deployment,
                request,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=retry_policy
            )
            
            return f"Router {request.router_id} deployed successfully: {provision_result} -> {deployment_result} -> {validation_result}"
            
        except Exception as e:
            # Rollback en caso de error
            workflow.logger.error(f"Deployment failed for {request.router_id}: {e}")
            
            try:
                await workflow.execute_activity(
                    cleanup_failed_deployment,
                    request,
                    start_to_close_timeout=timedelta(minutes=3)
                )
            except Exception as cleanup_error:
                workflow.logger.error(f"Cleanup failed: {cleanup_error}")
            
            raise e