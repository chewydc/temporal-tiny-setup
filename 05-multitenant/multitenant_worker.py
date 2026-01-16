import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from activities import (
    test_client_server_connectivity,
    provision_router_via_ansible_runner,
    deploy_router_software,
    generate_deployment_report,
    cleanup_failed_deployment
)
from workflows import NetworkDeploymentWorkflow

async def main():
    """
    Worker multitenant que escucha múltiples task queues.
    
    Estrategias de workers multitenant:
    1. Worker compartido: Un worker escucha múltiples task queues (este ejemplo)
    2. Workers dedicados: Un worker por tenant (mejor aislamiento)
    3. Workers por pool: Grupos de tenants comparten workers
    """
    
    print("="*80)
    print("WORKER MULTITENANT - TEMPORAL")
    print("="*80)
    
    # Configuración de tenants
    tenants = ["chogar", "amovil", "afijo"]
    
    print(f"\n🏢 Tenants configurados: {', '.join(tenants)}")
    print("\nEstrategia: Worker compartido (escucha múltiples task queues)")
    print("Ventajas: Eficiente en recursos, fácil de escalar")
    print("Desventajas: Menos aislamiento entre tenants\n")
    
    try:
        client = await Client.connect("localhost:7233")
        print("✅ Conectado a Temporal Server (localhost:7233)\n")
        
        # Crear un worker por cada tenant
        workers = []
        for tenant_id in tenants:
            task_queue = f"tenant-{tenant_id}-deployments"
            
            worker = Worker(
                client,
                task_queue=task_queue,
                workflows=[NetworkDeploymentWorkflow],
                activities=[
                    test_client_server_connectivity,
                    provision_router_via_ansible_runner,
                    deploy_router_software,
                    generate_deployment_report,
                    cleanup_failed_deployment
                ]
            )
            workers.append(worker)
            print(f"   📋 Task Queue: {task_queue}")
        
        print("\n" + "="*80)
        print("WORKERS INICIADOS - Esperando workflows...")
        print("="*80)
        print("\nPara ejecutar deployments:")
        print("  python multitenant_demo.py")
        print("\nPara ver workflows en Temporal UI:")
        print("  http://localhost:8233")
        print()
        
        # Ejecutar todos los workers concurrentemente
        await asyncio.gather(*[worker.run() for worker in workers])
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Workers detenidos por el usuario")
    except Exception as e:
        print(f"\n❌ Error en workers: {str(e)}")
        print("\nVerifica que:")
        print("  - Temporal Server esté corriendo: docker-compose ps")
        print("  - Puerto 7233 esté disponible")

if __name__ == "__main__":
    asyncio.run(main())
