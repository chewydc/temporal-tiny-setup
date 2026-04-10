"""
Monitor de Workflows - Consulta Externa de Estado
==================================================

Este script demuestra cómo consultar el estado de workflows desde fuera,
útil para:
- Integración con sistemas de monitoreo
- Enviar info a IA para diagnóstico automático
- Dashboards externos
- Alertas personalizadas
"""

import asyncio
import json
from datetime import datetime
from temporalio.client import Client

async def get_workflow_status(workflow_id: str) -> dict:
    """
    Consulta el estado de un workflow específico.
    
    Retorna info completa para análisis externo (ej: IA)
    """
    
    client = await Client.connect("localhost:7233")
    
    try:
        # Obtener handle del workflow
        handle = client.get_workflow_handle(workflow_id)
        
        # Describe (no bloquea, retorna estado actual)
        desc = await handle.describe()
        
        # Construir respuesta estructurada
        status_info = {
            "workflow_id": workflow_id,
            "status": str(desc.status),  # Running, Completed, Failed, etc.
            "workflow_type": desc.workflow_type,
            "start_time": desc.start_time.isoformat() if desc.start_time else None,
            "execution_time": desc.execution_time.isoformat() if desc.execution_time else None,
            "close_time": desc.close_time.isoformat() if desc.close_time else None,
            "task_queue": getattr(desc, 'task_queue_name', 'N/A'),  # Compatible con versiones antiguas
            "history_length": desc.history_length
        }
        
        # Si está completado o fallado, obtener resultado/error
        if desc.status.name in ["COMPLETED", "FAILED", "TERMINATED", "CANCELED"]:
            try:
                result = await handle.result()
                status_info["result"] = str(result)
                status_info["error"] = None
            except Exception as e:
                status_info["result"] = None
                status_info["error"] = str(e)
                status_info["error_type"] = type(e).__name__
        else:
            status_info["result"] = None
            status_info["error"] = None
        
        return status_info
        
    except Exception as e:
        return {
            "workflow_id": workflow_id,
            "status": "NOT_FOUND",
            "error": str(e)
        }

async def list_failed_workflows(limit: int = 10) -> list:
    """
    Lista workflows fallidos para análisis.
    
    Útil para enviar a IA y obtener diagnóstico automático.
    """
    
    client = await Client.connect("localhost:7233")
    
    failed_workflows = []
    
    try:
        # Query para workflows fallidos
        query = 'ExecutionStatus = "Failed"'
        
        count = 0
        async for workflow in client.list_workflows(query):
            if count >= limit:
                break
            
            # Obtener detalles de cada workflow fallido
            status = await get_workflow_status(workflow.id)
            failed_workflows.append(status)
            count += 1
            
    except Exception as e:
        print(f"Error listando workflows: {e}")
    
    return failed_workflows

async def monitor_workflow_realtime(workflow_id: str, interval_seconds: int = 5):
    """
    Monitorea un workflow en tiempo real.
    
    Útil para seguir el progreso de un deployment.
    """
    
    print(f"\n{'='*80}")
    print(f"MONITOREANDO WORKFLOW: {workflow_id}")
    print(f"{'='*80}\n")
    
    client = await Client.connect("localhost:7233")
    
    try:
        handle = client.get_workflow_handle(workflow_id)
        
        while True:
            desc = await handle.describe()
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Estado: {desc.status.name}")
            
            # Si terminó (completado o fallado), salir
            if desc.status.name in ["COMPLETED", "FAILED", "TERMINATED", "CANCELED"]:
                print(f"\n✅ Workflow terminó con estado: {desc.status.name}")
                
                # Obtener resultado o error
                try:
                    result = await handle.result()
                    print(f"\n📊 Resultado:\n{json.dumps(result, indent=2, default=str)}")
                except Exception as e:
                    print(f"\n❌ Error:\n{e}")
                
                break
            
            # Esperar antes de la siguiente consulta
            await asyncio.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Monitoreo detenido por el usuario")
    except Exception as e:
        print(f"\n❌ Error monitoreando workflow: {e}")

async def export_for_ai_analysis(workflow_id: str) -> str:
    """
    Exporta info del workflow en formato para análisis de IA.
    
    Retorna JSON con toda la info relevante para diagnóstico.
    """
    
    status = await get_workflow_status(workflow_id)
    
    # Formato optimizado para IA
    ai_prompt = {
        "context": "Workflow de deployment de router de red falló",
        "workflow_info": {
            "id": status["workflow_id"],
            "type": status["workflow_type"],
            "status": status["status"],
            "duration": f"Started: {status['start_time']}, Ended: {status['close_time']}"
        },
        "error": status.get("error"),
        "error_type": status.get("error_type"),
        "question": "¿Cuál es la causa del error y cómo solucionarlo?"
    }
    
    return json.dumps(ai_prompt, indent=2)

async def main():
    """Demo de consultas de estado"""
    
    print("\n" + "="*80)
    print("MONITOR DE WORKFLOWS - CONSULTA EXTERNA")
    print("="*80)
    print("\nOpciones:")
    print("  1. Consultar estado de un workflow específico")
    print("  2. Listar workflows fallidos (para análisis de IA)")
    print("  3. Monitorear workflow en tiempo real")
    print("  4. Export data")
    print()
    
    opcion = input("Selecciona opción (1-4): ").strip()
    
    if opcion == "1":
        workflow_id = input("\nIngresa Workflow ID: ").strip()
        status = await get_workflow_status(workflow_id)
        print(f"\n📊 Estado del Workflow:\n")
        print(json.dumps(status, indent=2, default=str))
        
    elif opcion == "2":
        print("\n🔍 Buscando workflows fallidos...\n")
        failed = await list_failed_workflows(limit=5)
        
        if failed:
            print(f"Encontrados {len(failed)} workflows fallidos:\n")
            for wf in failed:
                print(f"  - {wf['workflow_id']}: {wf.get('error', 'No error info')}")
            
            print("\n💡 Esta info puede enviarse a una IA para diagnóstico automático")
        else:
            print("✅ No hay workflows fallidos")
    
    elif opcion == "3":
        workflow_id = input("\nIngresa Workflow ID: ").strip()
        await monitor_workflow_realtime(workflow_id, interval_seconds=3)
    
    elif opcion == "4":
        workflow_id = input("\nIngresa Workflow ID: ").strip()
        status = await get_workflow_status(workflow_id)
        print("\n📤 Export data:\n")
        print(json.dumps(status, indent=2, default=str))
    
    else:
        print("❌ Opción inválida")

if __name__ == "__main__":
    print("\n" + "="*80)
    print("PREREQUISITOS:")
    print("="*80)
    print("  1. Temporal Server corriendo: docker-compose up -d")
    print("  2. Al menos un workflow ejecutado")
    print()
    print("Para obtener Workflow IDs:")
    print("  - Temporal UI: http://localhost:8233")
    print("  - CLI: temporal workflow list")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Programa terminado\n")
