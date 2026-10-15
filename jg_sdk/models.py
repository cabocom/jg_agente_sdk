# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Modelos de datos canónicos para estímulos de entrada, resultados y estado.

Este módulo define los esquemas canónicos Pydantic que garantizan un contrato
estable de comunicación entre consumidores, el plano de control (Dashboard) y
el motor cognitivo de jg_agente, sin acoplamiento a detalles de persistencia ni
dependencias internas del orquestador.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from jg_sdk.contracts import (
    ExecutionStatus as ExecutionStatus,
)
from jg_sdk.contracts import (
    RiskLevel as RiskLevel,
)
from jg_sdk.contracts import (
    StepStatus as StepStatus,
)

# =====================================================================
# 1. Enums Operacionales Adicionales
# =====================================================================


class ApprovalStatus(StrEnum):
    """Estados de aprobación humana (HITL - Human in the Loop)."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"
    TIMEOUT = "timeout"


class VerificationStatus(StrEnum):
    """Estados de comprobación activa post-operación."""

    NOT_STARTED = "not_started"
    PASS = "pass"
    FAIL = "fail"
    DEGRADED = "degraded"
    SKIPPED = "skipped"


class PolicyDecision(StrEnum):
    """Decisiones tomadas por la evaluación de seguridad."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_HUMAN_APPROVAL = "require_human_approval"


class GoalStatus(StrEnum):
    """Estados semánticos de satisfacción del objetivo del agente."""

    SATISFIED = "satisfied"
    NEEDS_MORE_INFO = "needs_more_info"
    BLOCKED_MISSING_CAPABILITY = "blocked_missing_capability"
    FAILED = "failed"


class PersistenceStatus(StrEnum):
    """Estados de almacenamiento durable en el Execution Plane."""

    PERSISTED = "persisted"
    DEGRADED = "degraded"
    FAILED = "failed"


# =====================================================================
# 2. Contexto de Usuario y Metadatos de Persistencia
# =====================================================================


class UserContext(BaseModel):
    """Contexto estructurado del usuario o entidad que solicita la ejecución."""

    model_config = ConfigDict(extra="allow")

    user_id: str | None = Field(
        default=None, description="Identificador único del usuario solicitante."
    )
    username: str | None = Field(
        default=None, description="Nombre de usuario o identificador visual."
    )
    email: str | None = Field(default=None, description="Correo electrónico del usuario.")
    role: str | None = Field(
        default=None, description="Rol RBAC del usuario (e.g. admin, operator, viewer)."
    )
    permissions: list[str] = Field(
        default_factory=list,
        description="Lista de permisos o scopes concedidos al usuario.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadatos contextuales adicionales del usuario.",
    )


class PersistenceMetadata(BaseModel):
    """Metadatos del estado de almacenamiento durable en la base de datos."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    status: PersistenceStatus = Field(
        default=PersistenceStatus.PERSISTED,
        description="Estado de la persistencia de la ejecución.",
    )
    persisted: bool = Field(
        default=True,
        description="Indica si el estado fue almacenado durablemente.",
    )
    error: str | None = Field(
        default=None,
        description="Mensaje descriptivo del error en caso de fallo o degradación.",
    )
    error_type: str | None = Field(
        default=None,
        description="Tipo de excepción o código del error de persistencia.",
    )


# =====================================================================
# 3. Modelos de Entrada y Salida Canónicos (I/O)
# =====================================================================


class AgentInput(BaseModel):
    """Contrato formal de entrada para el ciclo cognitivo del agente."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    execution_id: str = Field(
        ...,
        description="Identificador único de la ejecución asignado por el invocador.",
    )
    thread_id: str = Field(
        ...,
        validation_alias=AliasChoices("thread_id", "session_id"),
        description="Identificador de la sesión o hilo conversacional persistente.",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Identificador único de correlación distribuida (X-Correlation-ID).",
    )
    prompt: str = Field(
        ...,
        validation_alias=AliasChoices("prompt", "message"),
        description="Texto o instrucción principal normalizada para el agente.",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Parámetros parametrizados adicionales de la invocación.",
    )
    user_context: UserContext | None = Field(
        default=None,
        description="Contexto opcional de identidad y permisos del usuario solicitante.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadatos arbitrarios complementarios de la solicitud.",
    )
    callback_url: str | None = Field(
        default=None,
        description="URL opcional de webhook HTTP para notificar finalizaciones asíncronas.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp UTC de generación o recepción de la solicitud.",
    )


class AgentOutput(BaseModel):
    """Contrato formal de salida emitido por el ciclo cognitivo del agente."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    execution_id: str = Field(
        ...,
        description="Identificador único de la ejecución a la que corresponde la salida.",
    )
    thread_id: str = Field(
        ...,
        validation_alias=AliasChoices("thread_id", "session_id"),
        description="Identificador de la sesión o hilo conversacional asociado.",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Identificador único de correlación distribuida (X-Correlation-ID).",
    )
    status: ExecutionStatus = Field(
        default=ExecutionStatus.COMPLETED,
        description="Estado final o actual de la ejecución.",
    )
    response: str = Field(
        ...,
        validation_alias=AliasChoices("response", "answer"),
        description="Respuesta textual final o mensaje generado por el agente.",
    )
    data: dict[str, Any] | None = Field(
        default=None,
        description="Carga de datos estructurados o artefactos producidos.",
    )
    execution_time_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Duración total de la ejecución en milisegundos.",
    )
    requires_approval: bool = Field(
        default=False,
        description="Flag que indica si la ejecución se pausó requiriendo aprobación humana (HITL).",
    )
    pending_approval_id: str | None = Field(
        default=None,
        description="Identificador de la acción pendiente que requiere confirmación.",
    )
    error: str | None = Field(
        default=None,
        description="Mensaje descriptivo del error en caso de que status sea FAILED.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadatos adicionales de auditoría o ejecución.",
    )
    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp UTC de conclusión o emisión del resultado.",
    )


# =====================================================================
# 4. Traza de Pasos, Planes y Observabilidad
# =====================================================================


class IntentModel(BaseModel):
    """Intención procesada a partir de un estímulo de entrada."""

    model_config = ConfigDict(extra="allow")

    goal: str = Field(..., description="Objetivo principal formulado para el agente.")
    action_type: str = Field(default="general", description="Categoría de acción a ejecutar.")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Parámetros extraídos.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Nivel de certidumbre.")
    reasoning: str | None = Field(default=None, description="Justificación cognitiva del LLM.")


class StepExecutionRecord(BaseModel):
    """Traza auditable de ejecución de un paso individual o herramienta."""

    model_config = ConfigDict(extra="allow")

    step_id: str = Field(..., description="Identificador único del paso ejecutado.")
    tool_name: str = Field(..., description="Nombre de la herramienta ejecutada.")
    tool_args: dict[str, Any] = Field(
        default_factory=dict, description="Argumentos suministrados a la herramienta."
    )
    status: StepStatus = Field(
        default=StepStatus.COMPLETED, description="Resultado de la ejecución del paso."
    )
    output: Any = Field(default="", description="Salida producida por la herramienta.")
    error: str | None = Field(default=None, description="Mensaje de error si la herramienta falló.")
    duration_ms: float = Field(
        default=0.0, ge=0.0, description="Duración de la invocación en milisegundos."
    )
    rollback_context: dict[str, Any] | None = Field(
        default=None, description="Contexto capturado para eventual compensación."
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp UTC de ejecución.",
    )


class PlanStep(BaseModel):
    """Definición unitaria de un paso dentro de un plan de acción."""

    model_config = ConfigDict(extra="allow")

    step_id: str = Field(..., description="Identificador único del paso.")
    tool_name: str = Field(..., description="Nombre de la herramienta a invocar.")
    tool_args: dict[str, Any] = Field(
        default_factory=dict, description="Argumentos para la herramienta."
    )
    description: str = Field(default="", description="Descripción legible del paso.")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="Nivel de riesgo del paso.")
    reversible: bool = Field(default=False, description="Indica si el paso es compensable.")
    allow_failure: bool = Field(
        default=False,
        description="Indica si un fallo en este paso es no fatal.",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Lista de step_ids requeridos previamente.",
    )
    status: StepStatus = Field(default=StepStatus.PENDING, description="Estado del paso.")


class ExecutionPlan(BaseModel):
    """Plan de ejecución estructurado compuesto por pasos ordenados."""

    model_config = ConfigDict(extra="allow")

    plan_id: str = Field(..., description="Identificador único del plan.")
    goal: str = Field(..., description="Objetivo general que persigue el plan.")
    steps: list[PlanStep] = Field(default_factory=list, description="Secuencia de pasos.")
    estimated_risk: RiskLevel = Field(default=RiskLevel.LOW, description="Riesgo máximo estimado.")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp UTC de formulación del plan.",
    )


class ApprovalRecord(BaseModel):
    """Registro de autorización humana para operaciones de riesgo (HITL)."""

    model_config = ConfigDict(extra="allow")

    status: ApprovalStatus = Field(
        default=ApprovalStatus.PENDING, description="Estado de la aprobación."
    )
    approver: str | None = Field(default=None, description="Usuario o identidad que autorizó.")
    requested_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp UTC de solicitud.",
    )
    decided_at: datetime | None = Field(default=None, description="Timestamp UTC de decisión.")
    notes: str | None = Field(default=None, description="Comentarios u observaciones.")
    rejection_reason: str | None = Field(default=None, description="Motivo de rechazo.")
    approved_step_ids: list[str] = Field(
        default_factory=list,
        description="Lista de identificadores de pasos explícitamente autorizados.",
    )
    approved_tool_names: list[str] = Field(
        default_factory=list,
        description="Lista de herramientas explícitamente autorizadas.",
    )


class SecurityEvaluationResult(BaseModel):
    """Resultado formal de la evaluación de seguridad de una operación."""

    model_config = ConfigDict(extra="allow")

    decision: PolicyDecision = Field(
        default=PolicyDecision.ALLOW, description="Decisión de política de seguridad."
    )
    operation: str = Field(default="", description="Nombre de la operación evaluada.")
    target_resource: str = Field(default="", description="Recurso o parámetro objetivo evaluado.")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="Nivel de riesgo determinado.")
    reason: str = Field(default="", description="Motivo o justificación de la decisión.")
    required_permissions: list[str] = Field(
        default_factory=list, description="Permisos necesarios requeridos."
    )
    is_reversible: bool = Field(default=True, description="Indica si la acción es compensable.")
    can_cause_data_loss: bool = Field(
        default=False, description="Indica si la acción puede ocasionar pérdida de datos."
    )
    evaluated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp UTC de la evaluación.",
    )


class AuditRecord(BaseModel):
    """Registro inmutable de auditoría para trazabilidad."""

    model_config = ConfigDict(extra="allow")

    event_type: str = Field(..., description="Tipo de evento registrado.")
    actor: str = Field(default="agent", description="Entidad o componente emisor.")
    details: dict[str, Any] = Field(default_factory=dict, description="Detalles del evento.")
    correlation_id: str | None = Field(
        default=None,
        description="Identificador único de correlación distribuida (X-Correlation-ID).",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp UTC del evento.",
    )


class ExecutionThreadDetail(BaseModel):
    """Detalle consolidado del estado actual y trazas de un hilo de ejecución."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    thread_id: str = Field(
        ...,
        description="Identificador del hilo o sesión conversacional.",
    )
    execution_id: str | None = Field(
        default=None,
        description="Identificador de la última ejecución asociada al hilo.",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Identificador de correlación distribuida.",
    )
    status: ExecutionStatus | str = Field(
        default=ExecutionStatus.IN_PROGRESS,
        description="Estado operacional o final de la ejecución.",
    )
    prompt: str | None = Field(
        default=None,
        description="Instrucción de entrada o prompt del usuario.",
    )
    response: str | None = Field(
        default=None,
        description="Respuesta generada o mensaje de síntesis.",
    )
    current_step: int = Field(
        default=0,
        description="Índice del paso actual.",
    )
    next_nodes: list[str] = Field(
        default_factory=list,
        description="Lista de nombres de nodos pendientes de ejecución.",
    )
    plan: dict[str, Any] | None = Field(
        default=None,
        description="Plan de ejecución estructurado activo.",
    )
    steps: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Historial cronológico de pasos y herramientas ejecutadas.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadatos globales del hilo de ejecución.",
    )
