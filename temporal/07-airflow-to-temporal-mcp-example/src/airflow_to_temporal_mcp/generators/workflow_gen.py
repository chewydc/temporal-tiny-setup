"""
Generador de Workflows de Temporal
"""

from typing import Optional
from ..parsers.dag_parser import DagInfo


class WorkflowGenerator:
    """Genera código de Workflows de Temporal"""
    
    def __init__(self, platform_rules):
        self.platform_rules = platform_rules
    
    def generate(
        self,
        dag_info: DagInfo,
        migration_phase: str = "wrapper",
        tenant: str = "default-tenant",
        namespace: str = "default"
    ) -> str:
        """
        Genera código de Workflow de Temporal
        
        Args:
            dag_info: Información del DAG parseado
            migration_phase: Fase de migración (wrapper, hybrid, native)
            tenant: Tenant propietario
            namespace: Namespace de Temporal
        
        Returns:
            Código Python del workflow
        """
        
        if migration_phase == "wrapper":
            return self._generate_wrapper_workflow(dag_info, tenant, namespace)
        elif migration_phase == "hybrid":
            return self._generate_hybrid_workflow(dag_info, tenant, namespace)
        elif migration_phase == "native":
            return self._generate_native_workflow(dag_info, tenant, namespace)
        else:
            raise ValueError(f"Unknown migration phase: {migration_phase}")
    
    def _generate_wrapper_workflow(
        self,
        dag_info: DagInfo,
        tenant: str,
        namespace: str
    ) -> str:
        """Genera workflow wrapper (Fase 1)"""
        
        workflow_class = self._to_class_name(dag_info.dag_id)
        
        return f'''"""
Workflow migrado desde Airflow DAG: {dag_info.dag_id}
Fase de migración: WRAPPER
Tenant: {tenant}
Namespace: {namespace}

Descripción: {dag_info.description or "Sin descripción"}
"""

from temporalio import workflow
from datetime import timedelta
from typing import Dict, Any


@workflow.defn
class {workflow_class}:
    """
    Wrapper de Airflow DAG: {dag_info.dag_id}
    
    En esta fase, el DAG completo se ejecuta desde Temporal.
    Airflow actúa solo como ejecutor, Temporal controla el estado.
    """
    
    @workflow.run
    async def run(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta el DAG de Airflow como wrapper
        
        Args:
            request: Parámetros de entrada (se pasan como conf al DAG)
        
        Returns:
            Resultado de la ejecución del DAG
        """
        
        workflow.logger.info(f"Starting wrapper execution for DAG: {dag_info.dag_id}")
        
        # Ejecutar DAG completo en Airflow
        result = await workflow.execute_activity(
            "trigger_airflow_dag",
            {{
                "dag_id": "{dag_info.dag_id}",
                "conf": request,
                "execution_id": workflow.info().workflow_id
            }},
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=workflow.RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=100),
                backoff_coefficient=2.0,
                maximum_attempts=3
            )
        )
        
        workflow.logger.info(f"Wrapper execution completed: {{result}}")
        
        return {{
            "status": "success",
            "dag_id": "{dag_info.dag_id}",
            "result": result,
            "migration_phase": "wrapper"
        }}
'''
    
    def _generate_hybrid_workflow(
        self,
        dag_info: DagInfo,
        tenant: str,
        namespace: str
    ) -> str:
        """Genera workflow híbrido (Fase 2)"""
        
        workflow_class = self._to_class_name(dag_info.dag_id)
        
        # Generar steps para cada task
        steps = []
        for i, task in enumerate(dag_info.tasks, 1):
            activity_name = task.suggested_activity or task.task_id
            
            if task.is_centralized:
                comment = f"# Activity centralizada del SDK"
            else:
                comment = f"# Activity personalizada"
            
            step = f'''
        # Step {i}: {task.task_id}
        {comment}
        result_{i} = await workflow.execute_activity(
            "{activity_name}",
            {{"task_id": "{task.task_id}", "params": request.get("{task.task_id}", {{}})}},
            start_to_close_timeout=timedelta(minutes=10)
        )
        workflow.logger.info(f"Step {i} ({task.task_id}) completed: {{result_{i}}}")
'''
            steps.append(step)
        
        steps_code = "\n".join(steps)
        
        return f'''"""
Workflow migrado desde Airflow DAG: {dag_info.dag_id}
Fase de migración: HYBRID
Tenant: {tenant}
Namespace: {namespace}

Descripción: {dag_info.description or "Sin descripción"}
"""

from temporalio import workflow
from datetime import timedelta
from typing import Dict, Any


@workflow.defn
class {workflow_class}:
    """
    Workflow híbrido migrado desde: {dag_info.dag_id}
    
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
        
        workflow.logger.info(f"Starting hybrid execution for: {dag_info.dag_id}")
        
        results = []
{steps_code}
        
        workflow.logger.info("Hybrid execution completed")
        
        return {{
            "status": "success",
            "dag_id": "{dag_info.dag_id}",
            "results": results,
            "migration_phase": "hybrid"
        }}
'''
    
    def _generate_native_workflow(
        self,
        dag_info: DagInfo,
        tenant: str,
        namespace: str
    ) -> str:
        """Genera workflow nativo (Fase 3)"""
        
        workflow_class = self._to_class_name(dag_info.dag_id)
        
        # Generar imports de Activities centralizadas
        centralized_imports = set()
        for task in dag_info.tasks:
            if task.is_centralized and task.suggested_activity:
                activity = self.platform_rules.get_centralized_activity(task.suggested_activity)
                if activity:
                    module = activity["module"]
                    function = activity["function"]
                    centralized_imports.add(f"from {module} import {function}")
        
        imports_code = "\n".join(sorted(centralized_imports)) if centralized_imports else ""
        
        # Generar steps
        steps = []
        for i, task in enumerate(dag_info.tasks, 1):
            activity_name = task.suggested_activity or task.task_id
            
            step = f'''
        # Step {i}: {task.task_id}
        result_{i} = await workflow.execute_activity(
            "{activity_name}",
            {{"task_id": "{task.task_id}", "params": request.get("{task.task_id}", {{}})}},
            start_to_close_timeout=timedelta(minutes=10)
        )
        workflow.logger.info(f"Step {i} ({task.task_id}) completed: {{result_{i}}}")
'''
            steps.append(step)
        
        steps_code = "\n".join(steps)
        
        return f'''"""
Workflow migrado desde Airflow DAG: {dag_info.dag_id}
Fase de migración: NATIVE
Tenant: {tenant}
Namespace: {namespace}

Descripción: {dag_info.description or "Sin descripción"}
"""

from temporalio import workflow
from datetime import timedelta
from typing import Dict, Any

{imports_code}


@workflow.defn
class {workflow_class}:
    """
    Workflow nativo de Temporal migrado desde: {dag_info.dag_id}
    
    Completamente migrado, sin dependencia de Airflow.
    """
    
    @workflow.run
    async def run(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta workflow con Activities nativas
        
        Args:
            request: Parámetros de entrada
        
        Returns:
            Resultado de la ejecución
        """
        
        workflow.logger.info(f"Starting native execution for: {dag_info.dag_id}")
        
        results = []
{steps_code}
        
        workflow.logger.info("Native execution completed")
        
        return {{
            "status": "success",
            "dag_id": "{dag_info.dag_id}",
            "results": results,
            "migration_phase": "native"
        }}
'''
    
    def _to_class_name(self, dag_id: str) -> str:
        """Convierte dag_id a nombre de clase Python"""
        # router_config -> RouterConfigWorkflow
        parts = dag_id.replace("-", "_").split("_")
        return "".join(word.capitalize() for word in parts) + "Workflow"
