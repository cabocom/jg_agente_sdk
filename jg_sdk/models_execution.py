# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Modelos de trazabilidad de ejecución, planificación y auditoría de seguridad."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from jg_sdk.contracts import ExecutionStatus, RiskLevel, StepStatus
from jg_sdk.models_context import (
    ApprovalStatus,
    PolicyDecision,
)

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


__all__ = [
    "ApprovalRecord",
    "AuditRecord",
    "ExecutionPlan",
    "ExecutionThreadDetail",
    "IntentModel",
    "PlanStep",
    "SecurityEvaluationResult",
    "StepExecutionRecord",
]
