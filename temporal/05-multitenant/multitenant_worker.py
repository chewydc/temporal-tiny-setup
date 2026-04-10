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
    Worker multitenant con namespaces separados.
    
    Cada tenant tiene su propio namespace:
    - chogar: namespace "chogar"
    - amovil: namespace "amovil"
    - afijo: namespace "afijo"
    
    Aislamiento REAL: cada tenant solo ve sus workflows.
    """
    
    print("="*80)
    print("WORKER MULTITENANT - NAMESPACES SEPARADOS")
    print("="*80)
    
    tenants = ["chogar", "amovil", "afijo"]
    
    print(f"\n🏢 Tenants configurados: {', '.join(tenants)}")
    print("\nEstrategia: Namespace por tenant (aislamiento completo)")
    print("Ventajas: Aislamiento total de datos, cada tenant ve solo sus workflows")
    print("Desventajas: Mayor complejidad operacional\n")
    
    try:
        workers = []
        
        for tenant_id in tenants:
            # Conectar al namespace específico del tenant
            client = await Client.connect(
                "localhost:7233",
                namespace=tenant_id  # ⭐ Namespace separado
            )
            
            # Task queue dentro del namespace
            task_queue = f"{tenant_id}-deployments"
            
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
            print(f"   📦 Namespace: {tenant_id}")
            print(f"      📋 Task Queue: {task_queue}")
        
        print("\n" + "="*80)
        print("WORKERS INICIADOS - Esperando workflows...")
        print("="*80)
        print("\nPara ejecutar deployments:")
        print("  python multitenant_demo.py")
        print("\nPara ver workflows en Temporal UI:")
        print("  http://localhost:8233")
        print("  Seleccioná el namespace del tenant en el dropdown")
        print()
        
        await asyncio.gather(*[worker.run() for worker in workers])
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Workers detenidos por el usuario")
    except Exception as e:
        print(f"\n❌ Error en workers: {str(e)}")
        print("\nVerifica que:")
        print("  - Temporal Server esté corriendo: docker-compose ps")
        print("  - Namespaces estén creados: python setup_namespaces.py")

if __name__ == "__main__":
    asyncio.run(main())
