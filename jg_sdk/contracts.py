# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Contratos canónicos y protocolos públicos del ecosistema jg_agente_sdk.

Re-exporta en un único punto de entrada:
- Enums operacionales (RiskLevel, ToolType, ExecutionStatus, StepStatus)
- Contratos de herramientas (ToolResult, AgentTool)
- Metadatos de plugins y motores cognitivos (PluginMetadata, BaseEngine, BasePlugin)
"""

from jg_sdk.contracts_enums import (
    ExecutionStatus,
    RiskLevel,
    StepStatus,
    ToolType,
)
from jg_sdk.contracts_plugins import (
    BaseEngine,
    BasePlugin,
    ObserverEngine,
    PlannerEngine,
    PluginMetadata,
    VerifierEngine,
)
from jg_sdk.contracts_tools import (
    AgentTool,
    ToolResult,
)

__all__ = [
    "AgentTool",
    "BaseEngine",
    "BasePlugin",
    "ExecutionStatus",
    "ObserverEngine",
    "PlannerEngine",
    "PluginMetadata",
    "RiskLevel",
    "StepStatus",
    "ToolResult",
    "ToolType",
    "VerifierEngine",
]
