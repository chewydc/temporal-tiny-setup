import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from workflows import NetworkDeploymentWithAnsibleRunner
from activities import (
    provision_router_via_ansible_runner,
    deploy_router_software,
    validate_router_deployment,
    cleanup_failed_deployment
)

async def main():
    """Worker para caso 03: Ansible Runner + Airflow"""
    
    print("🚀 Iniciando Temporal Worker - Caso 03: Ansible Runner Integration")
    print("="*70)
    print("🔧 Ansible Runner: Despliegue de infraestructura (router containers)")
    print("🌊 Airflow: Configuración de software (DAGs)")
    print("⚡ Temporal: Orquestación unificada")
    print("="*70)
    
    # Conectar a Temporal
    print("🔌 Conectando a Temporal server...")
    client = await Client.connect("localhost:7233", namespace="default")
    print("✅ Conectado a Temporal server")
    
    # Crear worker con activities como strings para evitar imports en workflow
    worker = Worker(
        client,
        task_queue="network-deployment-queue",
        workflows=[NetworkDeploymentWithAnsibleRunner],
        activities=[
            provision_router_via_ansible_runner,
            deploy_router_software,
            validate_router_deployment,
            cleanup_failed_deployment
        ]
    )
    
    print("✅ Worker configurado con:")
    print("   • Workflow: NetworkDeploymentWithAnsibleRunner")
    print("   • Activities: Ansible Runner + Airflow + Validation")
    print("   • Task Queue: network-deployment-awx")
    print()
    print("🔄 Worker corriendo... (Ctrl+C para detener)")
    print("📋 Esperando workflows...")
    print(f"🔍 Polling task queue: network-deployment-awx")
    print(f"🌐 Namespace: default")
    
    # Ejecutar worker
    print("⏳ Iniciando worker...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())