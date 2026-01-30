"""
Workflow de ejemplo para demostrar lifecycle completo en Kubernetes.
"""

import asyncio
from datetime import timedelta
from typing import Dict, Any

from temporalio import workflow
from temporalio.common import RetryPolicy


@workflow.defn
class LifecycleWorkflow:
    """
    Workflow que demuestra el lifecycle completo:
    - Versionado de código
    - Rollouts de workers
    - Coexistencia de versiones
    - Replay automático
    """

    def __init__(self):
        self.state = {
            "step": 0,
            "version": "unknown",
            "worker_info": {},
            "start_time": None
        }

    @workflow.run
    async def run(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta un workflow largo para demostrar lifecycle.
        """
        workflow.logger.info(f"🚀 Starting lifecycle workflow: {request.get('workflow_id')}")
        
        self.state["start_time"] = workflow.now()
        self.state["workflow_id"] = request.get("workflow_id", "unknown")
        
        result = {
            "workflow_id": request.get("workflow_id"),
            "status": "IN_PROGRESS",
            "steps": [],
            "worker_versions": []
        }

        try:
            # PASO 1: Obtener información del worker
            result = await self._step_1_worker_info(result)
            
            # PASO 2: Procesamiento largo (para ver rollouts)
            result = await self._step_2_long_processing(result)
            
            # PASO 3: Validación final
            result = await self._step_3_validation(result)
            
            # PASO 4: Reporte final
            result = await self._step_4_final_report(result)
            
            result["status"] = "COMPLETED"
            workflow.logger.info(f"✅ Lifecycle workflow completed: {result['workflow_id']}")
            return result
            
        except Exception as e:
            workflow.logger.error(f"❌ Lifecycle workflow failed: {str(e)}")
            result["status"] = "FAILED"
            result["error"] = str(e)
            return result

    async def _step_1_worker_info(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        PASO 1: Obtener información del worker que ejecuta.
        """
        workflow.logger.info("📋 PASO 1: Getting worker information...")
        self.state["step"] = 1
        
        worker_info = await workflow.execute_activity(
            "get_worker_info",
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3)
        )
        
        result["steps"].append({
            "step": 1,
            "name": "get_worker_info",
            "status": "COMPLETED",
            "worker_info": worker_info,
            "timestamp": workflow.now().isoformat()
        })
        
        result["worker_versions"].append(worker_info.get("version", "unknown"))
        
        workflow.logger.info(f"✅ PASO 1: Worker info - Version: {worker_info.get('version')}")
        return result

    async def _step_2_long_processing(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        PASO 2: Procesamiento largo para demostrar rollouts.
        """
        workflow.logger.info("⏳ PASO 2: Long processing (5 minutes)...")
        self.state["step"] = 2
        
        # Procesar en chunks de 1 minuto para ver rollouts
        for minute in range(5):
            workflow.logger.info(f"⏰ Processing minute {minute + 1}/5...")
            
            chunk_result = await workflow.execute_activity(
                "process_chunk",
                {"minute": minute + 1, "total": 5},
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(maximum_attempts=5)
            )
            
            # Obtener info del worker en cada chunk
            worker_info = await workflow.execute_activity(
                "get_worker_info",
                start_to_close_timeout=timedelta(seconds=30)
            )
            
            result["worker_versions"].append(worker_info.get("version", "unknown"))
            
            # Sleep 1 minuto
            await asyncio.sleep(60)
        
        result["steps"].append({
            "step": 2,
            "name": "long_processing",
            "status": "COMPLETED",
            "duration_minutes": 5,
            "timestamp": workflow.now().isoformat()
        })
        
        workflow.logger.info("✅ PASO 2: Long processing completed")
        return result

    async def _step_3_validation(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        PASO 3: Validación final.
        """
        workflow.logger.info("🔍 PASO 3: Final validation...")
        self.state["step"] = 3
        
        validation_result = await workflow.execute_activity(
            "validate_processing",
            {"workflow_id": result["workflow_id"]},
            start_to_close_timeout=timedelta(seconds=60)
        )
        
        result["steps"].append({
            "step": 3,
            "name": "validation",
            "status": "COMPLETED",
            "validation_result": validation_result,
            "timestamp": workflow.now().isoformat()
        })
        
        workflow.logger.info("✅ PASO 3: Validation completed")
        return result

    async def _step_4_final_report(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        PASO 4: Reporte final con análisis de versiones.
        """
        workflow.logger.info("📊 PASO 4: Generating final report...")
        self.state["step"] = 4
        
        report = await workflow.execute_activity(
            "generate_lifecycle_report",
            {
                "workflow_id": result["workflow_id"],
                "worker_versions": result["worker_versions"],
                "steps": result["steps"],
                "start_time": self.state["start_time"].isoformat()
            },
            start_to_close_timeout=timedelta(seconds=60)
        )
        
        result["steps"].append({
            "step": 4,
            "name": "final_report",
            "status": "COMPLETED",
            "report": report,
            "timestamp": workflow.now().isoformat()
        })
        
        workflow.logger.info("✅ PASO 4: Final report generated")
        return result

    @workflow.query
    def get_current_state(self) -> Dict[str, Any]:
        """
        Query para obtener el estado actual del workflow.
        """
        return {
            "current_step": self.state["step"],
            "workflow_id": self.state.get("workflow_id"),
            "start_time": self.state["start_time"].isoformat() if self.state["start_time"] else None,
            "version": self.state["version"]
        }

    @workflow.signal
    def update_version(self, version: str) -> None:
        """
        Signal para actualizar la versión (para testing).
        """
        workflow.logger.info(f"🔄 Version updated to: {version}")
        self.state["version"] = version


@workflow.defn
class QuickTestWorkflow:
    """
    Workflow rápido para testing de deployments.
    """

    @workflow.run
    async def run(self, test_id: str) -> Dict[str, Any]:
        """
        Test rápido de 30 segundos.
        """
        workflow.logger.info(f"🧪 Quick test workflow: {test_id}")
        
        # Test básico
        worker_info = await workflow.execute_activity(
            "get_worker_info",
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        # Test de procesamiento
        result = await workflow.execute_activity(
            "quick_test",
            {"test_id": test_id},
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        return {
            "test_id": test_id,
            "status": "SUCCESS",
            "worker_version": worker_info.get("version"),
            "result": result,
            "timestamp": workflow.now().isoformat()
        }