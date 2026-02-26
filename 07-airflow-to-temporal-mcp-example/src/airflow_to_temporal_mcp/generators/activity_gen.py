"""
Generador de Activities de Temporal
"""

from ..parsers.dag_parser import DagInfo


class ActivityGenerator:
    """Genera código de Activities de Temporal"""
    
    def __init__(self, platform_rules):
        self.platform_rules = platform_rules
    
    def generate(
        self,
        dag_info: DagInfo,
        migration_phase: str = "hybrid",
        force_custom: bool = False
    ) -> str:
        """
        Genera código de Activities
        
        Args:
            dag_info: Información del DAG
            migration_phase: Fase de migración
            force_custom: Forzar generación de Activities personalizadas
        
        Returns:
            Código Python de activities
        """
        
        if migration_phase == "wrapper":
            return self._generate_wrapper_activities(dag_info)
        else:
            return self._generate_custom_activities(dag_info, force_custom)
    
    def _generate_wrapper_activities(self, dag_info: DagInfo) -> str:
        """Genera Activities para fase wrapper"""
        
        return f'''"""
Activities para Workflow: {dag_info.dag_id}
Fase: WRAPPER

Contiene el adapter para ejecutar DAG en Airflow.
"""

from temporalio import activity
import httpx
import asyncio
from typing import Dict, Any


class AirflowAdapterActivities:
    """Activities para integración con Airflow durante migración"""
    
    def __init__(self, airflow_url: str = "http://localhost:8080"):
        self.airflow_url = airflow_url
        self.auth = ("admin", "admin")  # TODO: Usar credenciales seguras
    
    @activity.defn
    async def trigger_airflow_dag(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispara DAG en Airflow y espera finalización
        
        Args:
            params: {{
                "dag_id": str,
                "conf": dict,
                "execution_id": str
            }}
        
        Returns:
            Resultado de la ejecución del DAG
        """
        
        dag_id = params["dag_id"]
        conf = params.get("conf", {{}})
        execution_id = params.get("execution_id", "unknown")
        
        activity.logger.info(f"Triggering Airflow DAG: {{dag_id}}")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Trigger DAG
            trigger_url = f"{{self.airflow_url}}/api/v1/dags/{{dag_id}}/dagRuns"
            
            trigger_data = {{
                "conf": conf,
                "dag_run_id": f"temporal-{{execution_id}}"
            }}
            
            response = await client.post(
                trigger_url,
                json=trigger_data,
                auth=self.auth,
                headers={{"Content-Type": "application/json"}}
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to trigger DAG: {{response.status_code}} - {{response.text}}")
            
            dag_run_info = response.json()
            dag_run_id = dag_run_info["dag_run_id"]
            
            activity.logger.info(f"DAG triggered: {{dag_run_id}}")
            
            # Esperar finalización
            final_state = await self._wait_for_dag_completion(
                client, dag_id, dag_run_id
            )
            
            if final_state == "success":
                activity.logger.info(f"DAG completed successfully: {{dag_run_id}}")
                return {{
                    "status": "success",
                    "dag_run_id": dag_run_id
                }}
            else:
                raise Exception(f"DAG failed with state: {{final_state}}")
    
    async def _wait_for_dag_completion(
        self,
        client: httpx.AsyncClient,
        dag_id: str,
        dag_run_id: str,
        max_wait_minutes: int = 30
    ) -> str:
        """Espera a que el DAG complete"""
        
        status_url = f"{{self.airflow_url}}/api/v1/dags/{{dag_id}}/dagRuns/{{dag_run_id}}"
        max_attempts = max_wait_minutes * 6  # Check every 10 seconds
        
        for attempt in range(max_attempts):
            response = await client.get(status_url, auth=self.auth)
            
            if response.status_code == 200:
                dag_run = response.json()
                state = dag_run.get("state")
                
                activity.logger.info(f"DAG state: {{state}} (attempt {{attempt + 1}}/{{max_attempts}})")
                
                if state in ["success", "failed"]:
                    return state
                elif state in ["running", "queued"]:
                    await asyncio.sleep(10)
                    continue
            
            await asyncio.sleep(10)
        
        return "timeout"


# Instanciar activities
activities = AirflowAdapterActivities()
trigger_airflow_dag = activities.trigger_airflow_dag
'''
    
    def _generate_custom_activities(self, dag_info: DagInfo, force_custom: bool) -> str:
        """Genera Activities personalizadas"""
        
        # Generar imports de Activities centralizadas
        centralized_imports = []
        custom_activities = []
        
        for task in dag_info.tasks:
            if task.is_centralized and not force_custom:
                # Usar Activity centralizada
                activity = self.platform_rules.get_centralized_activity(task.suggested_activity)
                if activity:
                    module = activity["module"]
                    function = activity["function"]
                    centralized_imports.append(f"from {module} import {function}")
            else:
                # Generar Activity personalizada
                custom_activities.append(self._generate_custom_activity(task))
        
        imports_code = "\n".join(sorted(set(centralized_imports))) if centralized_imports else ""
        custom_code = "\n\n".join(custom_activities) if custom_activities else ""
        
        header = f'''"""
Activities para Workflow: {dag_info.dag_id}
Fase: HYBRID/NATIVE

Combina Activities centralizadas del SDK con Activities personalizadas.
"""

from temporalio import activity
from typing import Dict, Any

{imports_code}
'''
        
        if custom_activities:
            header += f'''

class CustomActivities:
    """Activities personalizadas para {dag_info.dag_id}"""
    
{custom_code}


# Instanciar activities personalizadas
custom_activities = CustomActivities()
'''
        
        return header
    
    def _generate_custom_activity(self, task) -> str:
        """Genera una Activity personalizada"""
        
        activity_name = task.task_id
        
        # Generar implementación básica según el operator
        if task.operator_type == "BashOperator":
            bash_command = task.operator_args.get("bash_command", "echo 'TODO'")
            implementation = f'''
        # TODO: Implementar lógica de: {bash_command}
        activity.logger.info(f"Executing bash command: {bash_command}")
        
        # Placeholder implementation
        result = "Command executed successfully"
        
        return result
'''
        elif task.operator_type == "PythonOperator":
            implementation = f'''
        # TODO: Implementar lógica de PythonOperator
        activity.logger.info(f"Executing Python callable")
        
        # Placeholder implementation
        result = "Python callable executed successfully"
        
        return result
'''
        else:
            implementation = f'''
        # TODO: Implementar lógica de {task.operator_type}
        activity.logger.info(f"Executing {{params}}")
        
        # Placeholder implementation
        result = "Activity executed successfully"
        
        return result
'''
        
        return f'''    @activity.defn
    async def {activity_name}(self, params: Dict[str, Any]) -> str:
        """
        Activity migrada desde Airflow task: {task.task_id}
        Operator original: {task.operator_type}
        """
        
        activity.logger.info(f"Executing {activity_name} with params: {{params}}")
        
        try:
{implementation}
            activity.logger.info(f"{activity_name} completed successfully")
            return result
            
        except Exception as e:
            activity.logger.error(f"{activity_name} failed: {{str(e)}}")
            raise
'''
