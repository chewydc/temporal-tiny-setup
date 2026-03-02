"""
Script para ejecutar el Workflow Despertar TR
Este script simula cómo el Control Plane iniciaría el workflow
"""
import asyncio
from datetime import datetime
from temporalio.client import Client


async def ejecutar_despertar_tr():
    """Ejecuta el workflow de Despertar TR"""
    
    # Conectar al servidor Temporal
    client = await Client.connect('localhost:7233', namespace='default')
    
    # Configuración del workflow
    config = {
        'path': '/io/cel_chogar/per/confiabilidad/despertar_tr',
        'project_id': 'teco-dev-cdh-e926',
        'dataset_id': 'scripts_tambo',
        'table_id': 'despertar_tr',
        'mongo_uri': 'mongodb://localhost:27017',  # Ajustar según tu configuración
        'mongo_database': 'chogar_prod',
        'mongo_collection': 'logs_despertar_tr',
        'destinatarios_email': ['yairfernandez@teco.com.ar'],
        'max_workers': 10,
        'max_results': 1000
    }
    
    # Generar workflow_id único basado en timestamp
    workflow_id = f"despertar-tr-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    print(f"Iniciando workflow: {workflow_id}")
    
    # Ejecutar el workflow
    handle = await client.start_workflow(
        'DespertarTRWorkflow',
        config,
        id=workflow_id,
        task_queue='despertar-tr-queue',
        # Configurar como cron si se desea ejecución programada
        # cron_schedule='50 * * * *'  # Cada hora en el minuto 50
    )
    
    print(f"Workflow iniciado con ID: {handle.id}")
    print(f"Run ID: {handle.result_run_id}")
    print("Esperando resultado...")
    
    # Esperar el resultado (opcional, puede ser asíncrono)
    resultado = await handle.result()
    
    print("\n=== Resultado del Workflow ===")
    print(f"Total equipos procesados: {resultado['total_equipos']}")
    print(f"Exitosos: {resultado['exitosos']}")
    print(f"Fallidos: {resultado['fallidos']}")
    print(f"Archivo log: {resultado['archivo_log']}")
    print(f"Fecha: {resultado['fecha']}")
    
    return resultado


async def consultar_estado_workflow(workflow_id: str):
    """Consulta el estado de un workflow en ejecución"""
    
    client = await Client.connect('localhost:7233', namespace='default')
    
    handle = client.get_workflow_handle(workflow_id)
    
    # Obtener estado
    descripcion = await handle.describe()
    
    print(f"\n=== Estado del Workflow {workflow_id} ===")
    print(f"Estado: {descripcion.status}")
    print(f"Inicio: {descripcion.start_time}")
    
    # Si está completado, obtener resultado
    if descripcion.status.name == 'COMPLETED':
        resultado = await handle.result()
        print(f"Resultado: {resultado}")
    
    return descripcion


async def cancelar_workflow(workflow_id: str):
    """Cancela un workflow en ejecución"""
    
    client = await Client.connect('localhost:7233', namespace='default')
    
    handle = client.get_workflow_handle(workflow_id)
    
    await handle.cancel()
    print(f"Workflow {workflow_id} cancelado")


if __name__ == '__main__':
    # Ejecutar el workflow
    asyncio.run(ejecutar_despertar_tr())
    
    # Ejemplos de uso:
    # asyncio.run(consultar_estado_workflow('despertar-tr-20240827-105000'))
    # asyncio.run(cancelar_workflow('despertar-tr-20240827-105000'))
