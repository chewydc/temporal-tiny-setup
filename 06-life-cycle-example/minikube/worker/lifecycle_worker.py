"""
Worker principal para el lifecycle demo en Kubernetes.
"""

import asyncio
import logging
import os
import signal
import sys
from typing import Optional

from temporalio.client import Client
from temporalio.worker import Worker

# Importar workflows y activities
from workflows.lifecycle_workflows import LifecycleWorkflow, QuickTestWorkflow
from activities.lifecycle_activities import (
    get_worker_info,
    process_chunk,
    validate_processing,
    generate_lifecycle_report,
    quick_test,
    simulate_failure,
    version_specific_feature
)


class LifecycleWorker:
    """
    Worker que demuestra lifecycle completo en Kubernetes.
    """
    
    def __init__(self):
        self.worker: Optional[Worker] = None
        self.client: Optional[Client] = None
        self.running = False
        
        # Configuración desde environment
        self.temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
        self.task_queue = os.getenv("TASK_QUEUE", "lifecycle-queue")
        self.worker_version = os.getenv("WORKER_VERSION", "v1.0.0-local")
        self.namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
        
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """
        Inicia el worker con configuración completa.
        """
        self.logger.info(f"🚀 Starting Lifecycle Worker {self.worker_version}")
        self.logger.info(f"   Temporal Host: {self.temporal_host}")
        self.logger.info(f"   Task Queue: {self.task_queue}")
        self.logger.info(f"   Namespace: {self.namespace}")
        
        try:
            # Conectar a Temporal
            self.client = await Client.connect(
                self.temporal_host,
                namespace=self.namespace
            )
            self.logger.info("✅ Connected to Temporal Server")
            
            # Crear worker con versioning opcional
            worker_kwargs = {
                'client': self.client,
                'task_queue': self.task_queue,
                'workflows': [LifecycleWorkflow, QuickTestWorkflow],
                'activities': [
                    get_worker_info,
                    process_chunk,
                    validate_processing,
                    generate_lifecycle_report,
                    quick_test,
                    simulate_failure,
                    version_specific_feature
                ],
                'max_concurrent_activities': 10,
                'max_concurrent_workflow_tasks': 5
            }
            
            # Si USE_VERSIONING=true, habilitar worker versioning
            use_versioning = os.getenv("USE_VERSIONING", "false").lower() == "true"
            if use_versioning:
                worker_kwargs['build_id'] = self.worker_version
                worker_kwargs['use_worker_versioning'] = True
                self.logger.info(f"🔒 Worker versioning ENABLED with build_id={self.worker_version}")
            
            self.worker = Worker(**worker_kwargs)
            
            self.logger.info(f"🔧 Worker configured:")
            self.logger.info(f"   Max concurrent activities: 10")
            self.logger.info(f"   Max concurrent workflow tasks: 5")
            self.logger.info(f"   Workflows: LifecycleWorkflow, QuickTestWorkflow")
            self.logger.info(f"   Activities: 6 activities registered")
            
            # Configurar signal handlers para graceful shutdown
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            
            self.running = True
            self.logger.info(f"⚡ Worker {self.worker_version} ready and listening...")
            
            # Ejecutar worker
            await self.worker.run()
            
        except Exception as e:
            self.logger.error(f"❌ Worker failed to start: {str(e)}")
            raise
    
    def _signal_handler(self, signum, frame):
        """
        Maneja signals para graceful shutdown.
        """
        self.logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
        self.running = False
        
        if self.worker:
            asyncio.create_task(self._graceful_shutdown())
    
    async def _graceful_shutdown(self):
        """
        Graceful shutdown del worker.
        """
        self.logger.info("🔄 Graceful shutdown in progress...")
        
        if self.worker:
            try:
                # Temporal worker se encarga del graceful shutdown automáticamente
                self.logger.info("✅ Worker shutdown completed")
            except Exception as e:
                self.logger.error(f"❌ Error during shutdown: {str(e)}")
    
    async def health_check(self) -> bool:
        """
        Health check para Kubernetes probes.
        """
        try:
            if self.client:
                # Verificar conexión con Temporal
                await self.client.list_namespaces()
                return True
        except Exception as e:
            self.logger.error(f"❌ Health check failed: {str(e)}")
        
        return False


async def main():
    """
    Función principal del worker.
    """
    worker = LifecycleWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        print("\n🛑 Worker interrupted by user")
    except Exception as e:
        print(f"\n❌ Worker failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # Verificar variables de entorno críticas
    required_env = ["TEMPORAL_HOST", "TASK_QUEUE"]
    missing_env = [env for env in required_env if not os.getenv(env)]
    
    if missing_env:
        print(f"❌ Missing required environment variables: {missing_env}")
        sys.exit(1)
    
    # Ejecutar worker
    asyncio.run(main())