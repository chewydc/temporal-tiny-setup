"""
Parser de DAGs de Airflow usando AST
"""

import ast
from dataclasses import dataclass, field
from typing import List, Optional, Any


@dataclass
class TaskInfo:
    """Información de un task de Airflow"""
    task_id: str
    operator_type: str
    operator_args: dict = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    suggested_activity: Optional[str] = None
    is_centralized: bool = False


@dataclass
class DagInfo:
    """Información de un DAG de Airflow"""
    dag_id: str
    description: Optional[str] = None
    schedule_interval: Optional[str] = None
    default_args: dict = field(default_factory=dict)
    tasks: List[TaskInfo] = field(default_factory=list)
    task_dependencies: dict = field(default_factory=dict)


class DagParser:
    """Parser de DAGs de Airflow"""
    
    def __init__(self, platform_rules):
        self.platform_rules = platform_rules
    
    def parse(self, dag_content: str, file_path: str = "unknown.py") -> DagInfo:
        """
        Parsea un DAG de Airflow y extrae información estructural
        
        Args:
            dag_content: Contenido del archivo Python del DAG
            file_path: Path del archivo (para contexto)
        
        Returns:
            DagInfo con toda la información extraída
        """
        
        try:
            tree = ast.parse(dag_content)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax in DAG: {str(e)}")
        
        dag_info = DagInfo(dag_id="unknown")
        
        # Primero, extraer todas las funciones definidas
        function_definitions = self._extract_function_definitions(tree, dag_content)
        
        # Extraer información del DAG
        for node in ast.walk(tree):
            # Buscar definición del DAG
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "dag":
                        dag_info = self._extract_dag_info(node.value)
            
            # Buscar definiciones de tasks (operators)
            if isinstance(node, ast.Assign):
                task_info = self._extract_task_info(node, function_definitions)
                if task_info:
                    dag_info.tasks.append(task_info)
        
        # Extraer dependencias entre tasks
        dag_info.task_dependencies = self._extract_dependencies(tree)
        
        # Actualizar dependencias en cada task
        for task in dag_info.tasks:
            task.dependencies = dag_info.task_dependencies.get(task.task_id, [])
        
        # Sugerir Activities basadas en reglas de plataforma
        self._suggest_activities(dag_info)
        
        return dag_info
    
    def _extract_function_definitions(self, tree: ast.AST, source_code: str) -> dict:
        """Extrae definiciones de funciones del código fuente"""
        
        functions = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                
                # Extraer el código fuente de la función
                try:
                    func_code = ast.get_source_segment(source_code, node)
                    if func_code:
                        functions[func_name] = func_code
                except:
                    # Fallback: marcar que existe pero sin código
                    functions[func_name] = f"# Function {func_name} exists but code extraction failed"
        
        return functions
    
    def _extract_dag_info(self, dag_node: ast.Call) -> DagInfo:
        """Extrae información del objeto DAG"""
        
        dag_info = DagInfo(dag_id="unknown")
        
        if not isinstance(dag_node, ast.Call):
            return dag_info
        
        # Extraer argumentos del DAG
        for keyword in dag_node.keywords:
            if keyword.arg == "dag_id" or (not keyword.arg and len(dag_node.args) > 0):
                dag_info.dag_id = self._extract_string_value(
                    keyword.value if keyword.arg else dag_node.args[0]
                )
            elif keyword.arg == "description":
                dag_info.description = self._extract_string_value(keyword.value)
            elif keyword.arg == "schedule_interval":
                dag_info.schedule_interval = self._extract_string_value(keyword.value)
            elif keyword.arg == "default_args":
                dag_info.default_args = self._extract_dict_value(keyword.value)
        
        # Si dag_id es el primer argumento posicional
        if dag_info.dag_id == "unknown" and len(dag_node.args) > 0:
            dag_info.dag_id = self._extract_string_value(dag_node.args[0])
        
        return dag_info
    
    def _extract_task_info(self, node: ast.Assign, function_definitions: dict) -> Optional[TaskInfo]:
        """Extrae información de un task (operator)"""
        
        if not isinstance(node.value, ast.Call):
            return None
        
        # Verificar si es un Operator
        operator_type = self._get_operator_type(node.value.func)
        if not operator_type or not operator_type.endswith("Operator"):
            return None
        
        # Extraer task_id
        task_id = None
        if node.targets and isinstance(node.targets[0], ast.Name):
            task_id = node.targets[0].id
        
        # Extraer argumentos del operator
        operator_args = {}
        nested_operators = []
        
        for keyword in node.value.keywords:
            if keyword.arg == "task_id":
                task_id = self._extract_string_value(keyword.value)
            elif keyword.arg == "python_callable":
                # Extraer nombre de la función
                func_name = self._extract_callable_name(keyword.value)
                operator_args["python_callable"] = func_name
                
                # Si tenemos el código de la función, agregarlo
                if func_name in function_definitions:
                    operator_args["function_code"] = function_definitions[func_name]
                    
                    # NUEVO: Analizar operadores anidados dentro de la función
                    nested_operators = self._extract_nested_operators(function_definitions[func_name])
                    if nested_operators:
                        operator_args["nested_operators"] = nested_operators
            else:
                operator_args[keyword.arg] = self._extract_value(keyword.value)
        
        if not task_id:
            return None
        
        task_info = TaskInfo(
            task_id=task_id,
            operator_type=operator_type,
            operator_args=operator_args
        )
        
        # Agregar información de operadores anidados
        if nested_operators:
            task_info.operator_args["has_nested_operators"] = True
            task_info.operator_args["nested_operator_types"] = [op["type"] for op in nested_operators]
        
        return task_info
    
    def _extract_nested_operators(self, function_code: str) -> List[dict]:
        """
        Extrae operadores de Airflow que se usan DENTRO de una función Python
        
        Args:
            function_code: Código fuente de la función
        
        Returns:
            Lista de operadores encontrados con sus argumentos
        """
        
        nested_operators = []
        
        try:
            func_tree = ast.parse(function_code)
        except:
            return nested_operators
        
        for node in ast.walk(func_tree):
            # Buscar llamadas a operadores dentro de la función
            if isinstance(node, ast.Call):
                operator_type = self._get_operator_type(node.func)
                
                if operator_type and operator_type.endswith("Operator"):
                    # Extraer argumentos del operador anidado
                    operator_info = {
                        "type": operator_type,
                        "args": {}
                    }
                    
                    for keyword in node.keywords:
                        operator_info["args"][keyword.arg] = self._extract_value(keyword.value)
                    
                    nested_operators.append(operator_info)
        
        return nested_operators
    
    def _extract_callable_name(self, node: ast.AST) -> str:
        """Extrae el nombre de un callable"""
        
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return "unknown_callable"
    
    def _extract_dependencies(self, tree: ast.AST) -> dict:
        """Extrae dependencias entre tasks (>> y <<)"""
        
        dependencies = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.BinOp):
                if isinstance(node.value.op, ast.RShift):  # >>
                    left = self._get_task_name(node.value.left)
                    right = self._get_task_name(node.value.right)
                    if left and right:
                        if right not in dependencies:
                            dependencies[right] = []
                        dependencies[right].append(left)
                
                elif isinstance(node.value.op, ast.LShift):  # <<
                    left = self._get_task_name(node.value.left)
                    right = self._get_task_name(node.value.right)
                    if left and right:
                        if left not in dependencies:
                            dependencies[left] = []
                        dependencies[left].append(right)
        
        return dependencies
    
    def _suggest_activities(self, dag_info: DagInfo):
        """Sugiere Activities basadas en reglas de plataforma"""
        
        for task in dag_info.tasks:
            # Buscar en mapeo de operators
            operator_mapping = self.platform_rules.get_operator_mapping(task.operator_type)
            
            # NUEVO: Si el task tiene operadores anidados, sugerirlos también
            if task.operator_args.get("has_nested_operators"):
                nested_types = task.operator_args.get("nested_operator_types", [])
                nested_operators_info = task.operator_args.get("nested_operators", [])
                
                # Marcar que este task debe descomponerse
                task.operator_args["should_decompose"] = True
                task.operator_args["decomposed_activities"] = []
                
                # Sugerir Activities para cada operador anidado
                for nested_op in nested_operators_info:
                    nested_type = nested_op["type"]
                    nested_mapping = self.platform_rules.get_operator_mapping(nested_type)
                    
                    if nested_mapping:
                        # Si tiene activity centralizada, usarla
                        if "activity" in nested_mapping:
                            task.operator_args["decomposed_activities"].append({
                                "operator": nested_type,
                                "activity": nested_mapping["activity"],
                                "is_centralized": nested_mapping.get("centralized", False),
                                "args": nested_op["args"]
                            })
                        else:
                            # Usar default
                            task.operator_args["decomposed_activities"].append({
                                "operator": nested_type,
                                "activity": nested_mapping.get("default", f"custom_{nested_type.lower()}"),
                                "is_centralized": False,
                                "args": nested_op["args"]
                            })
            
            if operator_mapping:
                # Analizar patrones en los argumentos
                for pattern_rule in operator_mapping.get("patterns", []):
                    pattern = pattern_rule["pattern"]
                    
                    # Buscar patrón en bash_command, python_callable, etc.
                    for arg_value in task.operator_args.values():
                        if isinstance(arg_value, str) and pattern.lower() in arg_value.lower():
                            task.suggested_activity = pattern_rule["activity"]
                            task.is_centralized = pattern_rule.get("centralized", False)
                            break
                    
                    if task.suggested_activity:
                        break
                
                # Si no hay match, usar default
                if not task.suggested_activity:
                    # Si tiene activity centralizada directa
                    if "activity" in operator_mapping:
                        task.suggested_activity = operator_mapping["activity"]
                        task.is_centralized = operator_mapping.get("centralized", False)
                    else:
                        task.suggested_activity = operator_mapping.get("default", task.task_id)
            else:
                task.suggested_activity = task.task_id
    
    def _get_operator_type(self, func_node: ast.AST) -> Optional[str]:
        """Obtiene el tipo de operator"""
        
        if isinstance(func_node, ast.Name):
            return func_node.id
        elif isinstance(func_node, ast.Attribute):
            return func_node.attr
        return None
    
    def _get_task_name(self, node: ast.AST) -> Optional[str]:
        """Obtiene el nombre de un task desde un nodo AST"""
        
        if isinstance(node, ast.Name):
            return node.id
        return None
    
    def _extract_string_value(self, node: ast.AST) -> str:
        """Extrae valor string de un nodo AST"""
        
        if isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Str):  # Python < 3.8
            return node.s
        return ""
    
    def _extract_dict_value(self, node: ast.AST) -> dict:
        """Extrae valor dict de un nodo AST"""
        
        if isinstance(node, ast.Dict):
            result = {}
            for key, value in zip(node.keys, node.values):
                if key:
                    key_str = self._extract_string_value(key)
                    result[key_str] = self._extract_value(value)
            return result
        return {}
    
    def _extract_value(self, node: ast.AST) -> Any:
        """Extrae valor genérico de un nodo AST"""
        
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Dict):
            return self._extract_dict_value(node)
        elif isinstance(node, ast.List):
            return [self._extract_value(item) for item in node.elts]
        else:
            return str(node)
