"""
Generador de Workers de Temporal
"""

from typing import List


class WorkerGenerator:
    """Genera configuración de Workers de Temporal"""
    
    def __init__(self, platform_rules):
        self.platform_rules = platform_rules
    
    def generate(
        self,
        workflow_name: str,
        activities: List[str],
        tenant: str = "default-tenant",
        namespace: str = "default"
    ) -> str:
        """
        Genera código de Worker
        
        Args:
            workflow_name: Nombre del workflow
            activities: Lista de nombres de activities
            tenant: Tenant propietario
            namespace: Namespace de Temporal
        
        Returns:
            Código Python del worker
        """
        
        worker_config = self.platform_rules.get_worker_config()
        task_queue_pattern = worker_config.get("task_queue_pattern", "{tenant}-{workflow_type}")
        task_queue = task_queue_pattern.format(tenant=tenant, workflow_type=workflow_name)
        
        # Generar imports de activities
        activities_import = ", ".join(activities) if activities else "# No activities"
        
        return f'''"""
Worker para Workflow: {workflow_name}
Tenant: {tenant}
Namespace: {namespace}
Task Queue: {task_queue}

Este worker registra todas las Activities necesarias para el workflow.
"""

import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker

# Imports de workflows
from workflows import {self._to_class_name(workflow_name)}

# Imports de activities
from activities import (
    {activities_import}
)


async def main():
    """Inicia el worker de Temporal"""
    
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Conectar a Temporal
    logger.info(f"Connecting to Temporal server...")
    client = await Client.connect(
        "localhost:7233",
        namespace="{namespace}"
    )
    
    logger.info(f"Connected to namespace: {namespace}")
    
    # Crear worker
    logger.info(f"Creating worker for task queue: {task_queue}")
    worker = Worker(
        client,
        task_queue="{task_queue}",
        workflows=[{self._to_class_name(workflow_name)}],
        activities=[
            {activities_import}
        ],
        max_concurrent_activities={worker_config.get("resources", {}).get("max_concurrent_activities", 100)},
        max_concurrent_workflow_tasks={worker_config.get("resources", {}).get("max_concurrent_workflows", 50)}
    )
    
    logger.info(f"Worker started for tenant: {tenant}")
    logger.info(f"Listening on task queue: {task_queue}")
    logger.info(f"Registered workflows: {self._to_class_name(workflow_name)}")
    logger.info(f"Registered activities: {len(activities)} activities")
    
    # Ejecutar worker
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
'''
    
    def _to_class_name(self, workflow_name: str) -> str:
        """Convierte workflow_name a nombre de clase"""
        parts = workflow_name.replace("-", "_").split("_")
        return "".join(word.capitalize() for word in parts) + "Workflow"
