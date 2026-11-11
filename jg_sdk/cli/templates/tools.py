# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Plantilla de generación de código para tools.py."""

from __future__ import annotations


def get_tools_template(template: str, pkg_name: str, raw_slug: str) -> str:
    """Genera el código de tools.py según la plantilla seleccionada."""
    if template == "minimal":
        return f'''"""Definición de herramientas para {pkg_name}."""

from pydantic import BaseModel, Field
from jg_sdk import AgentTool, RiskLevel, ToolResult, ToolType


class QueryArgs(BaseModel):
    query: str = Field(..., description="Término o parámetro de consulta")


def execute_query(query: str) -> ToolResult:
    """Función de ejecución para la herramienta básica."""
    return ToolResult(
        success=True,
        output=f"Consulta procesada exitosamente para: {{query}}",
        metadata={{"query": query}},
    )


query_tool = AgentTool(
    name="{raw_slug}_query",
    description="Ejecuta una consulta básica en el plugin {raw_slug}.",
    category="{raw_slug}",
    args_schema=QueryArgs,
    func=execute_query,
    risk_level=RiskLevel.LOW,
    tool_type=ToolType.READ,
    read_only=True,
)
'''
    elif template == "standard":
        return f'''"""Definición de herramientas para {pkg_name}."""

from pydantic import BaseModel, Field
from jg_sdk import AgentTool, RiskLevel, ToolResult, ToolType


class InspectArgs(BaseModel):
    target: str = Field(..., description="Elemento o recurso a inspeccionar")


class ActionArgs(BaseModel):
    resource_id: str = Field(..., description="Identificador del recurso a modificar")
    parameters: dict = Field(default_factory=dict, description="Parámetros de la acción")


def execute_inspect(target: str) -> ToolResult:
    """Inspecciona el estado de un recurso."""
    return ToolResult(
        success=True,
        output=f"Inspección completada para {{target}} (estado: normal).",
        metadata={{"target": target, "status": "healthy"}},
    )


def execute_action(resource_id: str, parameters: dict | None = None) -> ToolResult:
    """Ejecuta una acción con soporte de reversibilidad."""
    params = parameters or {{}}
    return ToolResult(
        success=True,
        output=f"Acción aplicada sobre {{resource_id}} con parámetros {{params}}",
        metadata={{"resource_id": resource_id}},
        rollback_context={{"resource_id": resource_id, "previous_state": "active"}},
    )


def rollback_action(rollback_context: dict) -> ToolResult:
    """Función de compensación invocada automáticamente si falla el plan."""
    res_id = rollback_context.get("resource_id", "unknown")
    prev = rollback_context.get("previous_state", "unknown")
    return ToolResult(
        success=True,
        output=f"Compensación ejecutada: {{res_id}} restaurado a {{prev}}.",
    )


inspect_tool = AgentTool(
    name="{raw_slug}_inspect",
    description="Inspecciona el estado actual de un recurso.",
    category="{raw_slug}",
    args_schema=InspectArgs,
    func=execute_inspect,
    risk_level=RiskLevel.LOW,
    tool_type=ToolType.OBSERVER,
    read_only=True,
)

action_tool = AgentTool(
    name="{raw_slug}_action",
    description="Aplica una acción reversible sobre un recurso.",
    category="{raw_slug}",
    args_schema=ActionArgs,
    func=execute_action,
    risk_level=RiskLevel.MEDIUM,
    tool_type=ToolType.MUTATION,
    read_only=False,
    reversible=True,
    rollback_func=rollback_action,
)
'''
    else:  # full
        return f'''"""Definición de herramientas completas para {pkg_name}."""

from pydantic import BaseModel, Field
from jg_sdk import AgentTool, RiskLevel, ToolResult, ToolType


class TelemetryArgs(BaseModel):
    metric: str = Field(default="system_health", description="Métrica a recolectar")


class ApplyConfigArgs(BaseModel):
    service_id: str = Field(..., description="ID del servicio a configurar")
    config_key: str = Field(..., description="Clave de configuración")
    new_value: str = Field(..., description="Nuevo valor a aplicar")


def execute_telemetry(metric: str = "system_health") -> ToolResult:
    return ToolResult(
        success=True,
        output=f"Telemetría recolectada para {{metric}}.",
        metadata={{"metric": metric, "value": 100}},
    )


def execute_apply_config(service_id: str, config_key: str, new_value: str) -> ToolResult:
    return ToolResult(
        success=True,
        output=f"Configuración {{config_key}}={{new_value}} aplicada a {{service_id}}.",
        metadata={{"service_id": service_id, "key": config_key}},
        rollback_context={{"service_id": service_id, "key": config_key, "old_value": "default"}},
    )


def rollback_apply_config(rollback_context: dict) -> ToolResult:
    svc = rollback_context.get("service_id", "unknown")
    k = rollback_context.get("key", "unknown")
    old = rollback_context.get("old_value", "default")
    return ToolResult(
        success=True,
        output=f"Rollback exitoso: {{svc}} restaurado a {{k}}={{old}}.",
    )


telemetry_tool = AgentTool(
    name="{raw_slug}_telemetry",
    description="Recolecta métricas de observabilidad.",
    category="{raw_slug}",
    args_schema=TelemetryArgs,
    func=execute_telemetry,
    risk_level=RiskLevel.LOW,
    tool_type=ToolType.OBSERVER,
    read_only=True,
)

apply_config_tool = AgentTool(
    name="{raw_slug}_apply_config",
    description="Aplica una mutación de configuración crítica con compensación.",
    category="{raw_slug}",
    args_schema=ApplyConfigArgs,
    func=execute_apply_config,
    risk_level=RiskLevel.HIGH,
    tool_type=ToolType.MUTATION,
    read_only=False,
    reversible=True,
    rollback_func=rollback_apply_config,
)
'''
