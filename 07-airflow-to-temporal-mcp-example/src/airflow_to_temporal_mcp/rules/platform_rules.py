"""
Reglas de plataforma cargadas desde configuración
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List


class PlatformRules:
    """Gestiona reglas y configuración de la plataforma"""
    
    def __init__(self, config_path: Path):
        """
        Inicializa reglas desde archivo de configuración
        
        Args:
            config_path: Path al archivo platform_config.yaml
        """
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración desde YAML"""
        
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def get_centralized_activities(self) -> List[Dict[str, Any]]:
        """Retorna lista de Activities centralizadas"""
        return self.config.get("centralized_activities", [])
    
    def get_centralized_activity(self, name: str) -> Optional[Dict[str, Any]]:
        """Busca una Activity centralizada por nombre"""
        
        for activity in self.get_centralized_activities():
            if activity["name"] == name:
                return activity
        return None
    
    def find_centralized_activity_by_trigger(self, trigger: str) -> Optional[Dict[str, Any]]:
        """Busca Activity centralizada por trigger keyword"""
        
        trigger_lower = trigger.lower()
        
        for activity in self.get_centralized_activities():
            triggers = activity.get("triggers", [])
            if any(trigger_lower in t.lower() for t in triggers):
                return activity
        
        return None
    
    def get_operator_mapping(self, operator_type: str) -> Optional[Dict[str, Any]]:
        """Obtiene mapeo para un tipo de operator"""
        
        operator_mapping = self.config.get("operator_mapping", {})
        return operator_mapping.get(operator_type)
    
    def get_custom_activity_config(self) -> Dict[str, Any]:
        """Retorna configuración de Activities personalizadas"""
        return self.config.get("custom_activities", {})
    
    def get_workflow_config(self) -> Dict[str, Any]:
        """Retorna configuración de Workflows"""
        return self.config.get("workflow_config", {})
    
    def get_worker_config(self) -> Dict[str, Any]:
        """Retorna configuración de Workers"""
        return self.config.get("worker_config", {})
    
    def get_migration_phase_config(self, phase: str) -> Dict[str, Any]:
        """Retorna configuración de una fase de migración"""
        
        phases = self.config.get("migration_phases", {})
        return phases.get(phase, {})
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Retorna configuración de validaciones"""
        return self.config.get("validation", {})
    
    def get_sdk_config(self) -> Dict[str, Any]:
        """Retorna configuración del SDK de plataforma"""
        return self.config.get("platform", {}).get("sdk", {})
    
    def is_activity_name_allowed(self, name: str) -> bool:
        """Verifica si un nombre de Activity es permitido"""
        
        custom_config = self.get_custom_activity_config()
        allowed_patterns = custom_config.get("allowed_patterns", [])
        
        if not allowed_patterns:
            return True
        
        import re
        for pattern in allowed_patterns:
            # Convertir patrón glob a regex
            regex_pattern = pattern.replace("*", ".*")
            if re.match(f"^{regex_pattern}$", name):
                return True
        
        return False
    
    def get_activity_template(self) -> str:
        """Retorna template para Activities personalizadas"""
        
        custom_config = self.get_custom_activity_config()
        return custom_config.get("template", "")
    
    def should_enforce_centralized_activities(self) -> bool:
        """Verifica si se debe forzar uso de Activities centralizadas"""
        
        validation_config = self.get_validation_config()
        return validation_config.get("enforce_centralized_activities", True)
