# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Modelos de dominio canónicos y esquemas de datos serializables para jg_sdk.

Re-exporta en un único punto de entrada:
- Enums de control (ApprovalStatus, VerificationStatus, PolicyDecision, GoalStatus, PersistenceStatus)
- Contexto de usuario y persistencia (UserContext, PersistenceMetadata)
- Entrada/Salida canónica (AgentInput, AgentOutput)
- Planes y trazabilidad (IntentModel, StepExecutionRecord, PlanStep, ExecutionPlan, ApprovalRecord, SecurityEvaluationResult, AuditRecord, ExecutionThreadDetail)
"""

from jg_sdk.contracts import (
    ExecutionStatus,
    RiskLevel,
    StepStatus,
)
from jg_sdk.models_context import (
    ApprovalStatus,
    GoalStatus,
    PersistenceMetadata,
    PersistenceStatus,
    PolicyDecision,
    UserContext,
    VerificationStatus,
)
from jg_sdk.models_execution import (
    ApprovalRecord,
    AuditRecord,
    ExecutionPlan,
    ExecutionThreadDetail,
    IntentModel,
    PlanStep,
    SecurityEvaluationResult,
    StepExecutionRecord,
)
from jg_sdk.models_io import (
    AgentInput,
    AgentOutput,
)

__all__ = [
    "AgentInput",
    "AgentOutput",
    "ApprovalRecord",
    "ApprovalStatus",
    "AuditRecord",
    "ExecutionPlan",
    "ExecutionStatus",
    "ExecutionThreadDetail",
    "GoalStatus",
    "IntentModel",
    "PersistenceMetadata",
    "PersistenceStatus",
    "PlanStep",
    "PolicyDecision",
    "RiskLevel",
    "SecurityEvaluationResult",
    "StepExecutionRecord",
    "StepStatus",
    "UserContext",
    "VerificationStatus",
]
