"""
Generador de Activities de Temporal
"""

from ..parsers.dag_parser import DagInfo


class ActivityGenerator:
    """Genera código de Activities de Temporal"""
    
    def __init__(self, platform_rules):
        self.platform_rules = platform_rules
    
    def _indent_code(self, code: str, spaces: int) -> str:
        """Indenta código con el número de espacios especificado"""
        indent = " " * spaces
        lines = code.split("\n")
        return "\n".join(indent + line if line.strip() else "" for line in lines)
    
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
        all_activities_list = []  # Para el export final
        
        for task in dag_info.tasks:
            # NUEVO: Si el task tiene operadores anidados, generar Activities descompuestas
            if task.operator_args.get("should_decompose"):
                decomposed = task.operator_args.get("decomposed_activities", [])
                
                for decomp_activity in decomposed:
                    activity_name = decomp_activity["activity"]
                    is_centralized = decomp_activity.get("is_centralized", False)
                    
                    if is_centralized and not force_custom:
                        # Usar Activity centralizada
                        activity_info = self.platform_rules.get_centralized_activity(activity_name)
                        if activity_info:
                            module = activity_info["module"]
                            function = activity_info["function"]
                            centralized_imports.append(f"from {module} import {function}")
                            all_activities_list.append(function)
                    else:
                        # Generar Activity personalizada para el operador anidado
                        custom_act = self._generate_decomposed_activity(
                            decomp_activity,
                            task.task_id
                        )
                        custom_activities.append(custom_act)
                        all_activities_list.append(activity_name)
            
            # Generar Activity principal del task
            if task.is_centralized and not force_custom:
                # Usar Activity centralizada
                activity = self.platform_rules.get_centralized_activity(task.suggested_activity)
                if activity:
                    module = activity["module"]
                    function = activity["function"]
                    centralized_imports.append(f"from {module} import {function}")
                    all_activities_list.append(function)
            else:
                # Generar Activity personalizada
                custom_activities.append(self._generate_custom_activity(task))
                all_activities_list.append(task.task_id)
        
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
    
    def _generate_decomposed_activity(self, decomp_info: dict, parent_task_id: str) -> str:
        """
        Genera una Activity descompuesta desde un operador anidado
        
        Args:
            decomp_info: Información del operador anidado
            parent_task_id: ID del task padre
        
        Returns:
            Código de la Activity
        """
        
        operator_type = decomp_info["operator"]
        activity_name = decomp_info["activity"]
        args = decomp_info.get("args", {})
        
        # Generar implementación según el tipo de operador
        if operator_type == "BigQueryGetDataOperator":
            dataset = args.get("dataset_id", "dataset")
            table = args.get("table_id", "table")
            max_results = args.get("max_results", 1000)
            
            implementation = f'''
        # Activity descompuesta desde {parent_task_id}
        # Operador original: {operator_type}
        
        activity.logger.info(f"Querying BigQuery: {{params}}")
        
        # TODO: Usar Activity centralizada del SDK
        # from platform_sdk.bigquery import bigquery_get_data
        # result = await bigquery_get_data(params)
        
        # Implementación temporal:
        dataset_id = params.get("dataset_id", "{dataset}")
        table_id = params.get("table_id", "{table}")
        max_results = params.get("max_results", {max_results})
        
        activity.logger.info(f"Would query: {{dataset_id}}.{{table_id}}")
        
        return {{"status": "success", "dataset": dataset_id, "table": table_id}}
'''
        elif operator_type == "BigQueryExecuteQueryOperator":
            sql = args.get("sql", "")
            
            implementation = f'''
        # Activity descompuesta desde {parent_task_id}
        # Operador original: {operator_type}
        
        activity.logger.info(f"Executing BigQuery query")
        
        # TODO: Usar Activity centralizada del SDK
        # from platform_sdk.bigquery import bigquery_execute_query
        # result = await bigquery_execute_query(params)
        
        sql = params.get("sql", "")
        activity.logger.info(f"Would execute SQL: {{sql[:100]}}...")
        
        return {{"status": "success", "query_executed": True}}
'''
        elif operator_type == "EmailOperator":
            to = args.get("to", [])
            subject = args.get("subject", "")
            
            implementation = f'''
        # Activity descompuesta desde {parent_task_id}
        # Operador original: {operator_type}
        
        activity.logger.info(f"Sending email")
        
        # TODO: Usar Activity centralizada del SDK
        # from platform_sdk.notifications import send_email
        # result = await send_email(params)
        
        to_addresses = params.get("to", {to})
        subject = params.get("subject", "{subject}")
        
        activity.logger.info(f"Would send email to: {{to_addresses}}")
        
        return {{"status": "success", "recipients": to_addresses}}
'''
        else:
            implementation = f'''
        # Activity descompuesta desde {parent_task_id}
        # Operador original: {operator_type}
        
        activity.logger.info(f"Executing decomposed activity: {{params}}")
        
        # TODO: Implementar lógica para {operator_type}
        
        return {{"status": "success", "operator": "{operator_type}"}}
'''
        
        return f'''    @activity.defn
    async def {activity_name}(self, params: Dict[str, Any]) -> str:
        """
        Activity descompuesta desde task: {parent_task_id}
        Operador anidado original: {operator_type}
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
    
    def _generate_custom_activity(self, task) -> str:
        """Genera una Activity personalizada"""
        
        activity_name = task.task_id
        
        # Generar implementación según el operator
        if task.operator_type == "BashOperator":
            bash_command = task.operator_args.get("bash_command", "echo 'TODO'")
            implementation = f'''
        import subprocess
        
        bash_command = "{bash_command}"
        activity.logger.info(f"Executing bash command: {{bash_command}}")
        
        result = subprocess.run(
            bash_command,
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"Command failed: {{result.stderr}}")
        
        return result.stdout
'''
        elif task.operator_type == "PythonOperator":
            # Extraer información de la función si está disponible
            python_callable = task.operator_args.get("python_callable", "")
            function_code = task.operator_args.get("function_code", "")
            
            if function_code:
                # Si tenemos el código de la función, usarlo
                implementation = f'''
        # Código extraído del DAG original
        activity.logger.info(f"Executing Python function: {python_callable}")
        
        # TODO: Adaptar esta función para Temporal
        # Función original:
        {self._indent_code(function_code, 8)}
        
        # Ejecutar lógica
        result = {python_callable}(**params)
        return result
'''
            else:
                implementation = f'''
        # Función Python: {python_callable}
        activity.logger.info(f"Executing Python callable: {python_callable}")
        
        # TODO: Implementar la lógica de la función {python_callable}
        # Esta función debe ser extraída del DAG original y adaptada aquí
        
        result = {{"status": "success", "message": "Function executed"}}
        return result
'''
        elif task.operator_type == "BigQueryGetDataOperator":
            dataset = task.operator_args.get("dataset_id", "dataset")
            table = task.operator_args.get("table_id", "table")
            max_results = task.operator_args.get("max_results", 1000)
            
            implementation = f'''
        from google.cloud import bigquery
        
        activity.logger.info(f"Querying BigQuery: {{params}}")
        
        client = bigquery.Client()
        dataset_id = params.get("dataset_id", "{dataset}")
        table_id = params.get("table_id", "{table}")
        max_results = params.get("max_results", {max_results})
        
        query = f"SELECT * FROM `{{client.project}}.{{dataset_id}}.{{table_id}}` LIMIT {{max_results}}"
        
        query_job = client.query(query)
        results = query_job.result()
        
        data = [dict(row) for row in results]
        activity.logger.info(f"Retrieved {{len(data)}} rows from BigQuery")
        
        return data
'''
        elif task.operator_type == "BigQueryExecuteQueryOperator":
            sql = task.operator_args.get("sql", "SELECT 1")
            
            implementation = f'''
        from google.cloud import bigquery
        
        activity.logger.info(f"Executing BigQuery query")
        
        client = bigquery.Client()
        sql = params.get("sql", """{sql}""")
        
        query_job = client.query(sql)
        query_job.result()  # Wait for completion
        
        activity.logger.info(f"Query executed successfully")
        return {{"status": "success", "job_id": query_job.job_id}}
'''
        elif task.operator_type == "EmailOperator":
            to = task.operator_args.get("to", [])
            subject = task.operator_args.get("subject", "")
            
            implementation = f'''
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        activity.logger.info(f"Sending email")
        
        to_addresses = params.get("to", {to})
        subject = params.get("subject", "{subject}")
        html_content = params.get("html_content", "")
        files = params.get("files", [])
        
        # TODO: Configurar SMTP server y credenciales
        # msg = MIMEMultipart()
        # msg['From'] = "sender@example.com"
        # msg['To'] = ", ".join(to_addresses)
        # msg['Subject'] = subject
        # msg.attach(MIMEText(html_content, 'html'))
        
        activity.logger.info(f"Email would be sent to: {{to_addresses}}")
        return {{"status": "success", "recipients": to_addresses}}
'''
        else:
            implementation = f'''
        # Operator: {task.operator_type}
        activity.logger.info(f"Executing {{params}}")
        
        # TODO: Implementar lógica específica para {task.operator_type}
        # Consultar documentación del operator en Airflow
        
        result = {{"status": "success", "operator": "{task.operator_type}"}}
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
