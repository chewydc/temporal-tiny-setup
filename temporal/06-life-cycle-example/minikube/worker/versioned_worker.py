"""
Worker con versioning estricto usando Worker Versioning de Temporal.
"""

import asyncio
import logging
import os
import signal
import sys
from typing import Optional

from temporalio.client import Client
from temporalio.worker import Worker

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


class VersionedWorker:
    """Worker con build_id para versioning estricto."""
    
    def __init__(self):
        self.worker: Optional[Worker] = None
        self.client: Optional[Client] = None
        self.running = False
        
        self.temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
        self.task_queue = os.getenv("TASK_QUEUE", "lifecycle-versioned-queue")
        self.worker_version = os.getenv("WORKER_VERSION", "v1.0.0-local")
        self.namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Inicia worker con build_id para versioning."""
        self.logger.info(f"🚀 Starting VERSIONED Worker {self.worker_version}")
        self.logger.info(f"   Build ID: {self.worker_version}")
        self.logger.info(f"   Task Queue: {self.task_queue}")
        
        try:
            self.client = await Client.connect(
                self.temporal_host,
                namespace=self.namespace
            )
            self.logger.info("✅ Connected to Temporal Server")
            
            # Worker con build_id para versioning estricto
            self.worker = Worker(
                self.client,
                task_queue=self.task_queue,
                workflows=[LifecycleWorkflow, QuickTestWorkflow],
                activities=[
                    get_worker_info,
                    process_chunk,
                    validate_processing,
                    generate_lifecycle_report,
                    quick_test,
                    simulate_failure,
                    version_specific_feature
                ],
                build_id=self.worker_version,  # 🔑 Clave para versioning
                use_worker_versioning=True,     # 🔑 Habilitar versioning
                max_concurrent_activities=10,
                max_concurrent_workflow_tasks=5
            )
            
            self.logger.info(f"🔒 Worker versioning ENABLED with build_id={self.worker_version}")
            
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            
            self.running = True
            self.logger.info(f"⚡ Versioned Worker ready and listening...")
            
            await self.worker.run()
            
        except Exception as e:
            self.logger.error(f"❌ Worker failed: {str(e)}")
            raise
    
    def _signal_handler(self, signum, frame):
        self.logger.info(f"🛑 Received signal {signum}, shutting down...")
        self.running = False


async def main():
    worker = VersionedWorker()
    try:
        await worker.start()
    except KeyboardInterrupt:
        print("\n🛑 Worker interrupted")
    except Exception as e:
        print(f"\n❌ Worker failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    required_env = ["TEMPORAL_HOST", "TASK_QUEUE"]
    missing_env = [env for env in required_env if not os.getenv(env)]
    
    if missing_env:
        print(f"❌ Missing environment variables: {missing_env}")
        sys.exit(1)
    
    asyncio.run(main())
