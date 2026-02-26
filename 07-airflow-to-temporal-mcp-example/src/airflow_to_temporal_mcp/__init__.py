"""
Airflow to Temporal MCP Server

MCP Server para migración automatizada de DAGs de Airflow a Workflows de Temporal.
Alineado con la arquitectura de plataforma de automatización.
"""

__version__ = "0.1.0"

from .server import serve

__all__ = ["serve"]
