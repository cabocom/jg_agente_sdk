# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""SDK público desacoplado y contratos para el ecosistema jg_agente.

Proporciona contratos estables, interfaces base y utilidades de integración
para desarrolladores de plugins y servicios clientes, con cero dependencias del
orquestador interno (LangGraph/LangChain) o almacenamiento persistente.
"""

from jg_sdk.cli import generate_plugin_scaffold, main
from jg_sdk.client import (
    DEFAULT_MAX_TIMESTAMP_SKEW_SECONDS,
    AgentAuthError,
    AgentClient,
    AgentClientError,
    AgentResponseError,
    JGAgentClient,
    compute_body_sha256,
    compute_canonical_string,
    compute_hmac_signature,
    verify_hmac_signature,
    verify_request_signature,
)
from jg_sdk.contracts import (
    AgentTool,
    BaseEngine,
    BasePlugin,
    ExecutionStatus,
    ObserverEngine,
    PlannerEngine,
    PluginMetadata,
    RiskLevel,
    StepStatus,
    ToolResult,
    ToolType,
    VerifierEngine,
)
from jg_sdk.models import (
    AgentInput,
    AgentOutput,
    ApprovalRecord,
    ApprovalStatus,
    AuditRecord,
    ExecutionPlan,
    ExecutionThreadDetail,
    GoalStatus,
    IntentModel,
    PersistenceMetadata,
    PersistenceStatus,
    PlanStep,
    PolicyDecision,
    SecurityEvaluationResult,
    StepExecutionRecord,
    UserContext,
    VerificationStatus,
)
from jg_sdk.testing import MockPluginRunner

__version__ = "1.3.0"

__all__ = [
    # Version
    "__version__",
    # CLI y Scaffolding
    "main",
    "generate_plugin_scaffold",
    # Enums y Clasificaciones
    "RiskLevel",
    "ToolType",
    "ExecutionStatus",
    "StepStatus",
    "ApprovalStatus",
    "VerificationStatus",
    "PolicyDecision",
    "GoalStatus",
    "PersistenceStatus",
    # Contratos de Herramientas y Plugins
    "ToolResult",
    "AgentTool",
    "PluginMetadata",
    "BaseEngine",
    "ObserverEngine",
    "PlannerEngine",
    "VerifierEngine",
    "BasePlugin",
    # Modelos de Entrada, Salida y Trazabilidad
    "UserContext",
    "AgentInput",
    "AgentOutput",
    "StepExecutionRecord",
    "PlanStep",
    "ExecutionPlan",
    "ApprovalRecord",
    "SecurityEvaluationResult",
    "AuditRecord",
    "ExecutionThreadDetail",
    "PersistenceMetadata",
    "IntentModel",
    # Cliente Criptográfico e Inter-Servicio
    "JGAgentClient",
    "AgentClient",
    "AgentClientError",
    "AgentAuthError",
    "AgentResponseError",
    "DEFAULT_MAX_TIMESTAMP_SKEW_SECONDS",
    "compute_body_sha256",
    "compute_canonical_string",
    "compute_hmac_signature",
    "verify_hmac_signature",
    "verify_request_signature",
    # Harness de Testing
    "MockPluginRunner",
]
