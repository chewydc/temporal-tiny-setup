import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from workflows import NetworkDeploymentWorkflow
from activities import (
    provision_router_infrastructure,
    deploy_router_software,
    validate_router_deployment,
    cleanup_failed_deployment
)

TASK_QUEUE_NAME = "network-deployment-queue"

async def main():
    # Conectar al servidor Temporal local
    client = await Client.connect("localhost:7233", namespace="default")
    
    # Crear worker
    worker = Worker(
        client,
        task_queue=TASK_QUEUE_NAME,
        workflows=[NetworkDeploymentWorkflow],
        activities=[
            provision_router_infrastructure,
            deploy_router_software,
            validate_router_deployment,
            cleanup_failed_deployment
        ]
    )
    
    print("Network Deployment Worker started...")
    print("Listening for workflows on queue:", TASK_QUEUE_NAME)
    
    # Ejecutar worker
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())