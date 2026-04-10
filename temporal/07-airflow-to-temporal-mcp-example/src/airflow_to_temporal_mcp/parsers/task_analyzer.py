"""
Analizador de tasks de Airflow
"""

from typing import Dict, Any
from .dag_parser import DagInfo


class TaskAnalyzer:
    """Analiza tasks y proporciona recomendaciones de migración"""
    
    def __init__(self, platform_rules):
        self.platform_rules = platform_rules
    
    def analyze(self, dag_info: DagInfo) -> Dict[str, Any]:
        """
        Analiza un DAG y proporciona métricas y recomendaciones
        
        Args:
            dag_info: Información del DAG parseado
        
        Returns:
            Diccionario con análisis y recomendaciones
        """
        
        total_tasks = len(dag_info.tasks)
        centralized_count = sum(1 for task in dag_info.tasks if task.is_centralized)
        custom_count = total_tasks - centralized_count
        
        # Calcular complejidad
        complexity_score = self._calculate_complexity(dag_info)
        
        # Generar recomendación
        recommendation = self._generate_recommendation(
            total_tasks=total_tasks,
            centralized_count=centralized_count,
            complexity_score=complexity_score
        )
        
        return {
            "total_tasks": total_tasks,
            "centralized_count": centralized_count,
            "custom_count": custom_count,
            "complexity_score": complexity_score,
            "recommendation": recommendation,
            "task_breakdown": self._get_task_breakdown(dag_info)
        }
    
    def _calculate_complexity(self, dag_info: DagInfo) -> int:
        """
        Calcula score de complejidad del DAG
        
        Factores:
        - Número de tasks
        - Número de dependencias
        - Tipos de operators
        """
        
        score = 0
        
        # Complejidad por número de tasks
        score += len(dag_info.tasks) * 2
        
        # Complejidad por dependencias
        total_deps = sum(len(deps) for deps in dag_info.task_dependencies.values())
        score += total_deps * 3
        
        # Complejidad por tipos de operators
        operator_types = set(task.operator_type for task in dag_info.tasks)
        score += len(operator_types) * 5
        
        return score
    
    def _generate_recommendation(
        self,
        total_tasks: int,
        centralized_count: int,
        complexity_score: int
    ) -> str:
        """Genera recomendación de estrategia de migración"""
        
        if complexity_score < 20:
            phase = "native"
            reason = "Baja complejidad, migración directa recomendada"
        elif centralized_count / total_tasks > 0.7 if total_tasks > 0 else False:
            phase = "hybrid"
            reason = "Alto uso de Activities centralizadas, migración híbrida eficiente"
        else:
            phase = "wrapper"
            reason = "Alta complejidad o bajo uso de Activities centralizadas, comenzar con wrapper"
        
        return f"Fase recomendada: {phase}. {reason}"
    
    def _get_task_breakdown(self, dag_info: DagInfo) -> Dict[str, Any]:
        """Obtiene desglose detallado de tasks"""
        
        breakdown = {
            "by_operator": {},
            "by_activity_type": {
                "centralized": [],
                "custom": []
            }
        }
        
        for task in dag_info.tasks:
            # Por operator
            if task.operator_type not in breakdown["by_operator"]:
                breakdown["by_operator"][task.operator_type] = 0
            breakdown["by_operator"][task.operator_type] += 1
            
            # Por tipo de activity
            if task.is_centralized:
                breakdown["by_activity_type"]["centralized"].append({
                    "task_id": task.task_id,
                    "activity": task.suggested_activity
                })
            else:
                breakdown["by_activity_type"]["custom"].append({
                    "task_id": task.task_id,
                    "activity": task.suggested_activity
                })
        
        return breakdown
