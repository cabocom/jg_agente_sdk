# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Modelos canónicos de entrada y salida inter-servicio (AgentInput y AgentOutput)."""

from datetime import UTC, datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from jg_sdk.contracts import ExecutionStatus
from jg_sdk.models_context import UserContext

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
    locale: str = Field(
        default="es",
        description="Código de idioma de la ejecución ('es', 'en', 'fr', 'de', 'it').",
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

__all__ = [
    "AgentInput",
    "AgentOutput",
]
