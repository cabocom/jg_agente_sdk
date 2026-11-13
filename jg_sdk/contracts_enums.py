# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Enums operacionales y clasificaciones canónicas de dominio para jg_sdk."""

from enum import StrEnum

# 1. Enums Operacionales y Clasificaciones de Dominio
# =====================================================================


class RiskLevel(StrEnum):
    """Nivel de riesgo operativo asignado a una herramienta o paso."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ToolType(StrEnum):
    """Clasificación funcional de herramientas."""

    OBSERVER = "observer"
    ACTUATOR = "actuator"
    VERIFIER = "verifier"
    READ = "read"
    MUTATION = "mutation"


class ExecutionStatus(StrEnum):
    """Estados canónicos de una ejecución de agente."""

    COMPLETED = "completed"
    WAITING_APPROVAL = "waiting_approval"
    FAILED = "failed"
    CANCELLED = "cancelled"
    IN_PROGRESS = "in_progress"
    TIMEOUT = "timeout"


class StepStatus(StrEnum):
    """Estados de ejecución de un paso individual del plan."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"


# =====================================================================

__all__ = [
    "ExecutionStatus",
    "RiskLevel",
    "StepStatus",
    "ToolType",
]
