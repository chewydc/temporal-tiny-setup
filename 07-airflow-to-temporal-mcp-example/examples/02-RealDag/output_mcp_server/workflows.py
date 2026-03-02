"""
Workflow migrado desde Airflow DAG: chogar_despertar_tr
Fase de migración: HYBRID
Tenant: chogar
Namespace: default

Descripción: DAG Automatización Despertar TR
"""

from temporalio import workflow
from datetime import timedelta
from typing import Dict, Any


@workflow.defn
class ChogarDespertarTrWorkflow:
    """
    Workflow híbrido migrado desde: chogar_despertar_tr
    
    Combina Activities nativas de Temporal con ejecución en Airflow.
    """
    
    @workflow.run
    async def run(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta workflow con mix de Activities nativas y Airflow
        
        Args:
            request: Parámetros de entrada
        
        Returns:
            Resultado de la ejecución
        """
        
        workflow.logger.info(f"Starting hybrid execution for: chogar_despertar_tr")
        
        results = []

        # Step 1: nombrar_csv
        # Activity personalizada
        result_1 = await workflow.execute_activity(
            "custom_python_activity",
            {"task_id": "nombrar_csv", "params": request.get("nombrar_csv", {})},
            start_to_close_timeout=timedelta(minutes=10)
        )
        workflow.logger.info(f"Step 1 (nombrar_csv) completed: {result_1}")


        # Step 2: tr_implementacion_task  
        # Activity personalizada
        result_2 = await workflow.execute_activity(
            "custom_python_activity",
            {"task_id": "tr_implementacion_task", "params": request.get("tr_implementacion_task", {})},
            start_to_close_timeout=timedelta(minutes=10)
        )
        workflow.logger.info(f"Step 2 (tr_implementacion_task) completed: {result_2}")


        # Step 3: tr_correo_finalizacion
        # Activity personalizada
        result_3 = await workflow.execute_activity(
            "custom_python_activity",
            {"task_id": "tr_correo_finalizacion", "params": request.get("tr_correo_finalizacion", {})},
            start_to_close_timeout=timedelta(minutes=10)
        )
        workflow.logger.info(f"Step 3 (tr_correo_finalizacion) completed: {result_3}")


        # Step 4: load_csv_to_db
        # Activity personalizada
        result_4 = await workflow.execute_activity(
            "custom_python_activity",
            {"task_id": "load_csv_to_db", "params": request.get("load_csv_to_db", {})},
            start_to_close_timeout=timedelta(minutes=10)
        )
        workflow.logger.info(f"Step 4 (load_csv_to_db) completed: {result_4}")

        
        workflow.logger.info("Hybrid execution completed")
        
        return {
            "status": "success",
            "dag_id": "chogar_despertar_tr",
            "results": results,
            "migration_phase": "hybrid"
        }
