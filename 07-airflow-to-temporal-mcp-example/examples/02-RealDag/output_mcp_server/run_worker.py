"""
Worker para Workflow: chogar_despertar_tr
Tenant: chogar
Namespace: default
Task Queue: chogar-despertar-tr

Este worker registra todas las Activities necesarias para el workflow.
"""

import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker

# Imports de workflows
from workflows import ChogarDespertarTrWorkflow

# Imports de activities personalizadas
from activities import custom_activities

# Imports de activities centralizadas del SDK
# from platform_sdk.bigquery import bigquery_get_data, bigquery_execute_query
# from platform_sdk.mongodb import mongodb_find, mongodb_insert_many
# from platform_sdk.notifications import send_email


async def main():
    """Inicia el worker de Temporal"""
    
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Conectar a Temporal
    logger.info(f"Connecting to Temporal server...")
    client = await Client.connect(
        "localhost:7233",
        namespace="default"
    )
    
    logger.info(f"Connected to namespace: default")
    
    # Crear worker
    logger.info(f"Creating worker for task queue: chogar-despertar-tr")
    worker = Worker(
        client,
        task_queue="chogar-despertar-tr",
        workflows=[ChogarDespertarTrWorkflow],
        activities=[
            # Activities personalizadas
            custom_activities.nombrar_csv,
            custom_activities.tr_implementacion_task,
            custom_activities.tr_correo_finalizacion,
            custom_activities.load_csv_to_db,
            
            # Activities centralizadas del SDK (descomentar cuando estén disponibles)
            # bigquery_get_data,
            # bigquery_execute_query,
            # mongodb_find,
            # mongodb_insert_many,
            # send_email,
        ],
        max_concurrent_activities=100,
        max_concurrent_workflow_tasks=50
    )
    
    logger.info(f"Worker started for tenant: chogar")
    logger.info(f"Listening on task queue: chogar-despertar-tr")
    logger.info(f"Registered workflows: ChogarDespertarTrWorkflow")
    logger.info(f"Registered activities: 4 custom activities")
    
    # Ejecutar worker
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
