# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Enums de control de flujo, contexto de identidad de usuario y persistencia."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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

__all__ = [
    "ApprovalStatus",
    "GoalStatus",
    "PersistenceMetadata",
    "PersistenceStatus",
    "PolicyDecision",
    "UserContext",
    "VerificationStatus",
]
