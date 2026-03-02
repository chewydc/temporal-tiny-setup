"""
Worker para el Workflow Despertar TR
"""
import asyncio
import os
from temporalio.client import Client
from temporalio.worker import Worker

from despertar_tr_workflow import DespertarTRWorkflow
from despertar_tr_activities import (
    nombrar_csv_activity,
    obtener_equipos_bigquery_activity,
    verificar_reproceso_mongodb_activity,
    reiniciar_tr_haas_activity,
    verificar_status_haas_activity,
    escribir_log_csv_activity,
    cargar_logs_mongodb_activity,
    cargar_logs_bigquery_activity,
    enviar_email_activity
)


async def main():
    """Inicializa y ejecuta el worker"""
    
    # Configuración de conexión a Temporal
    temporal_host = os.getenv('TEMPORAL_HOST', 'localhost:7233')
    temporal_namespace = os.getenv('TEMPORAL_NAMESPACE', 'default')
    
    # Conectar al servidor Temporal
    client = await Client.connect(
        temporal_host,
        namespace=temporal_namespace
    )
    
    # Configurar proxy si es necesario
    os.environ["https_proxy"] = "http://proxyappl.telecom.arg.telecom.com.ar:8080"
    
    # Crear el worker
    worker = Worker(
        client,
        task_queue='despertar-tr-queue',
        workflows=[DespertarTRWorkflow],
        activities=[
            nombrar_csv_activity,
            obtener_equipos_bigquery_activity,
            verificar_reproceso_mongodb_activity,
            reiniciar_tr_haas_activity,
            verificar_status_haas_activity,
            escribir_log_csv_activity,
            cargar_logs_mongodb_activity,
            cargar_logs_bigquery_activity,
            enviar_email_activity
        ],
        max_concurrent_activities=10,  # Controla concurrencia de activities
        max_concurrent_workflow_tasks=100
    )
    
    print("Worker iniciado. Escuchando en task queue: despertar-tr-queue")
    print(f"Conectado a Temporal: {temporal_host}")
    print(f"Namespace: {temporal_namespace}")
    
    # Ejecutar el worker
    await worker.run()


if __name__ == '__main__':
    asyncio.run(main())
