import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from activities import (
    test_client_server_connectivity,
    provision_router_via_ansible_runner,
    wait_for_manual_verification,
    deploy_router_software,
    generate_deployment_report,
    cleanup_failed_deployment
)
from workflows import NetworkDeploymentWithConnectivity

async def main():
    """
    Worker de Temporal para el Caso 04: Conectividad Cliente-Servidor
    """
    
    print("="*80)
    print("CASO 04: TEMPORAL WORKER - CONECTIVIDAD CLIENTE-SERVIDOR")
    print("="*80)
    print("Funcionalidades:")
    print("  - Despliegue de router via Ansible Runner")
    print("  - Configuracion via Airflow")
    print("  - Tests de conectividad cliente-servidor")
    print("  - Reportes de deployment")
    print()
    
    try:
        # Conectar a Temporal Server
        client = await Client.connect("localhost:7233")
        print("Conectado a Temporal Server (localhost:7233)")
        
        # Crear worker
        worker = Worker(
            client,
            task_queue="caso04-connectivity-queue",
            workflows=[NetworkDeploymentWithConnectivity],
            activities=[
                test_client_server_connectivity,
                provision_router_via_ansible_runner,
                wait_for_manual_verification,
                deploy_router_software,
                generate_deployment_report,
                cleanup_failed_deployment
            ]
        )
        
        print("Worker configurado para task_queue: caso04-connectivity-queue")
        print()
        print("Activities disponibles:")
        print("  - test_client_server_connectivity")
        print("  - provision_router_via_ansible_runner")
        print("  - deploy_router_software")
        print("  - generate_deployment_report")
        print("  - cleanup_failed_deployment")
        print()
        print("Workflows disponibles:")
        print("  - NetworkDeploymentWithConnectivity")
        print()
        print("="*80)
        print("WORKER INICIADO - Esperando workflows...")
        print("="*80)
        print("Para ejecutar un deployment:")
        print("  python run_deployment.py")
        print()
        
        # Ejecutar worker
        await worker.run()
        
    except KeyboardInterrupt:
        print("\nWorker detenido por el usuario")
    except Exception as e:
        print(f"Error en worker: {str(e)}")
        print("Verifica que:")
        print("  - Temporal Server este corriendo en localhost:7233")
        print("  - Docker Compose este activo: docker-compose ps")

if __name__ == "__main__":
    asyncio.run(main())