import asyncio
from temporalio.client import Client
from workflows import NetworkDeploymentWorkflow
from models import NetworkDeploymentRequest

TASK_QUEUE_NAME = "network-deployment-queue"

async def main():
    # Conectar al servidor Temporal
    client = await Client.connect("localhost:7233", namespace="default")
    
    # Crear request de despliegue
    deployment_request = NetworkDeploymentRequest(
        router_id="router-lab-001",
        router_ip="192.168.100.11",
        software_version="IOS-XE-17.3.4"
    )
    
    print(f"Starting deployment for router: {deployment_request.router_id}")
    print(f"IP: {deployment_request.router_ip}")
    print(f"Software: {deployment_request.software_version}")
    
    try:
        # Ejecutar workflow
        result = await client.execute_workflow(
            NetworkDeploymentWorkflow.run,
            deployment_request,
            id=f"deploy-{deployment_request.router_id}",
            task_queue=TASK_QUEUE_NAME
        )
        
        print(f"Deployment completed: {result}")
        
    except Exception as e:
        print(f"Deployment failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())