# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez <contacto@javiergalvez.com>
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Contratos públicos, metadatos y especificaciones de capacidades para el ecosistema jg_agente.

Este módulo define las interfaces base y modelos necesarios para desarrollar
plugins, herramientas ejecutables y motores de dominio cognitivos, manteniendo
un desacoplamiento absoluto de cualquier orquestador interno (cero dependencias
de LangGraph, LangChain, bases de datos o frameworks web).
"""

import concurrent.futures
import re
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# =====================================================================
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
# 2. Contratos de Herramientas y Resultados
# =====================================================================


class ToolResult(BaseModel):
    """Resultado normalizado devuelto tras la invocación de una herramienta."""

    model_config = ConfigDict(extra="allow")

    success: bool = Field(..., description="Indica si la ejecución concluyó exitosamente.")
    output: Any = Field(
        default="", description="Salida, datos o texto producido por la herramienta."
    )
    error: str | None = Field(default=None, description="Mensaje de error si la ejecución falló.")
    duration_ms: float = Field(
        default=0.0, ge=0.0, description="Tiempo de ejecución de la herramienta en milisegundos."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadatos de auditoría, contexto o telemetría de ejecución.",
    )
    rollback_context: dict[str, Any] | None = Field(
        default=None,
        description="Datos de estado requeridos para compensar o revertir los efectos.",
    )

    def __str__(self) -> str:
        """Representación textual estándar del resultado para consumidores y LLMs."""
        if self.success:
            return str(self.output)
        return f"Error: {self.error or self.output}"


class AgentTool(BaseModel):
    """Contrato definitivo y descriptor de capacidades de una herramienta ejecutable."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = Field(..., min_length=1, description="Identificador único de la herramienta.")
    description: str = Field(
        ...,
        min_length=1,
        description="Descripción funcional clara para el function calling del LLM.",
    )
    category: str = Field(
        default="general", min_length=1, description="Categoría lógica de la herramienta."
    )
    version: str = Field(default="1.0.0", description="Versión semántica de la herramienta.")

    args_schema: type[BaseModel] | None = Field(
        default=None,
        description="Esquema Pydantic BaseModel de argumentos esperado por la herramienta.",
    )
    func: Callable[..., Any] = Field(
        ...,
        description="Función ejecutable (síncrona o callable) que implementa la herramienta.",
    )

    risk_level: RiskLevel = Field(
        default=RiskLevel.LOW,
        description="Nivel de riesgo operativo evaluado por el SecurityGuard.",
    )
    required_permissions: list[str] = Field(
        default_factory=list,
        description="Permisos RBAC requeridos para ejecutar la herramienta.",
    )

    tool_type: ToolType = Field(
        default=ToolType.OBSERVER,
        description="Rol funcional de la herramienta (observer, actuator, verifier, read, mutation).",
    )
    read_only: bool = Field(
        default=True,
        description="Indica si la herramienta carece de efectos secundarios en el entorno.",
    )
    reversible: bool = Field(
        default=False,
        description="Indica si la herramienta puede compensar sus cambios ante fallos.",
    )
    idempotent: bool = Field(
        default=True,
        description="Indica si ejecutarla múltiples veces con los mismos argumentos produce el mismo resultado.",
    )
    makes_http_requests: bool = Field(
        default=False,
        description="Indica si realiza peticiones de red salientes (sujeto a SSRF protection).",
    )
    allow_failure: bool = Field(
        default=False,
        description="Indica si fallos operacionales de la herramienta son no fatales por defecto.",
    )

    timeout_sec: float = Field(
        default=30.0,
        gt=0.0,
        description="Tiempo límite de ejecución en segundos.",
    )
    rollback_func: Callable[[dict[str, Any]], ToolResult] | None = Field(
        default=None,
        description="Función de compensación invocable ante fallos del flujo o reversión.",
    )

    @field_validator("func")
    @classmethod
    def validate_func_callable(cls, v: Any) -> Any:
        if not callable(v):
            raise ValueError("El campo 'func' debe ser un invocable (función o método).")
        return v

    @field_validator("rollback_func")
    @classmethod
    def validate_rollback_func_callable(cls, v: Any) -> Any:
        if v is not None and not callable(v):
            raise ValueError("El campo 'rollback_func' debe ser un invocable o None.")
        return v

    @field_validator("args_schema")
    @classmethod
    def validate_args_schema_type(cls, v: Any) -> Any:
        if v is not None and not (isinstance(v, type) and issubclass(v, BaseModel)):
            raise ValueError(
                "El campo 'args_schema' debe ser una subclase de Pydantic BaseModel o None."
            )
        return v

    @model_validator(mode="after")
    def validate_reversible_and_rollback(self) -> Self:
        if self.reversible and self.rollback_func is None:
            raise ValueError(
                "Las herramientas configuradas como reversibles (reversible=True) "
                "deben proporcionar obligatoriamente un 'rollback_func' válido para compensación."
            )
        if self.rollback_func is not None:
            self.reversible = True
        return self

    def run(self, *args: Any, **kwargs: Any) -> ToolResult:
        """Ejecuta la herramienta de forma síncrona controlando el timeout asignado."""
        start_time = time.perf_counter()
        timeout = self.timeout_sec or 30.0

        def _exec() -> Any:
            return self.func(*args, **kwargs)

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_exec)
                res = future.result(timeout=timeout)

            duration = (time.perf_counter() - start_time) * 1000

            if isinstance(res, ToolResult):
                if res.duration_ms <= 0.0:
                    res.duration_ms = round(duration, 2)
                return res
            elif isinstance(res, str):
                return ToolResult(
                    success=True,
                    output=res,
                    duration_ms=round(duration, 2),
                )
            elif isinstance(res, bool):
                return ToolResult(
                    success=res,
                    output="Operación exitosa" if res else "Operación fallida",
                    duration_ms=round(duration, 2),
                )
            else:
                return ToolResult(
                    success=True,
                    output=res,
                    duration_ms=round(duration, 2),
                )
        except TimeoutError:
            duration = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                success=False,
                output="",
                error=f"TimeoutError: La herramienta '{self.name}' superó el tiempo límite de {timeout}s",
                duration_ms=round(duration, 2),
                metadata={"timeout_sec": timeout, "timed_out": True},
            )
        except Exception as exc:
            duration = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                success=False,
                output="",
                error=str(exc),
                duration_ms=round(duration, 2),
            )

    def rollback(self, rollback_context: dict[str, Any]) -> ToolResult:
        """Ejecuta la función de compensación si la herramienta es reversible."""
        if not self.reversible or self.rollback_func is None:
            return ToolResult(
                success=False,
                error="NO_ROLLBACK_AVAILABLE",
                output="Operación no reversible: la herramienta no dispone de compensador registrado.",
                metadata={"reversible": False},
            )

        start_time = time.perf_counter()
        try:
            res = self.rollback_func(rollback_context)
            duration = (time.perf_counter() - start_time) * 1000

            if isinstance(res, ToolResult):
                if res.duration_ms <= 0.0:
                    res.duration_ms = round(duration, 2)
                res.metadata.setdefault("rollback_executed", True)
                return res
            elif isinstance(res, bool):
                return ToolResult(
                    success=res,
                    output="Compensación completada exitosamente."
                    if res
                    else "Compensación fallida.",
                    duration_ms=round(duration, 2),
                    metadata={"rollback_executed": True},
                )
            elif isinstance(res, str):
                return ToolResult(
                    success=True,
                    output=res,
                    duration_ms=round(duration, 2),
                    metadata={"rollback_executed": True},
                )
            else:
                return ToolResult(
                    success=True,
                    output=str(res) if res is not None else "Compensación completada.",
                    duration_ms=round(duration, 2),
                    metadata={"rollback_executed": True},
                )
        except Exception as exc:
            duration = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                success=False,
                output="",
                error=f"Error durante la compensación: {exc}",
                duration_ms=round(duration, 2),
                metadata={"rollback_executed": False, "exception": str(exc)},
            )


# =====================================================================
# 3. Metadatos de Plugin y Motores Cognitivos
# =====================================================================


class PluginMetadata(BaseModel):
    """Metadatos descriptivos y requerimientos de compatibilidad del plugin."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(
        ...,
        min_length=2,
        max_length=64,
        description="Identificador único del plugin (slug alfanumérico en minúsculas con guiones o guiones bajos).",
    )
    version: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="Versión del plugin siguiendo Versionado Semántico (e.g. '1.0.0').",
    )
    description: str = Field(
        default="",
        max_length=512,
        description="Descripción legible del propósito y dominio del plugin.",
    )
    author: str = Field(
        default="",
        max_length=128,
        description="Autor u organización responsable del plugin.",
    )
    jg_agente_version_min: str = Field(
        default="1.0.0",
        description="Versión mínima del Core de jg_agente requerida para compatibilidad.",
    )
    enabled: bool = Field(
        default=True,
        description="Indica si el plugin se encuentra activo y listo para ser utilizado.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Etiquetas clasificatorias del plugin (e.g. ['network', 'devops']).",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Nombres de otros plugins requeridos por este plugin.",
    )
    config_schema: type[BaseModel] | None = Field(
        default=None,
        description="Esquema Pydantic opcional para validar la configuración/env vars del plugin.",
    )
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadatos o configuraciones adicionales no estructuradas.",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Valida que el identificador del plugin sea un slug normalizado."""
        clean = v.strip().lower()
        if not clean:
            raise ValueError("El nombre del plugin no puede estar vacío.")
        if not re.match(r"^[a-z0-9_-]+$", clean):
            raise ValueError(
                f"El nombre del plugin '{v}' debe contener únicamente caracteres alfanuméricos, guiones o guiones bajos."
            )
        return clean


class BaseEngine(ABC):
    """Contrato base para motores de dominio cognitivos o de infraestructura."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre identificador único del motor."""
        ...

    @property
    @abstractmethod
    def engine_type(self) -> str:
        """Tipo o rol del motor (e.g. 'observer', 'planner', 'verifier', 'discovery', 'custom')."""
        ...

    async def startup(self) -> None:  # noqa: B027
        """Hook opcional de inicio del motor para adquirir recursos o conexiones."""

    async def shutdown(self) -> None:  # noqa: B027
        """Hook opcional de finalización del motor para liberar recursos o conexiones."""


class ObserverEngine(BaseEngine, ABC):
    """Motor de observación de entorno o captura de telemetría previa al razonamiento."""

    @property
    def engine_type(self) -> str:
        return "observer"


class PlannerEngine(BaseEngine, ABC):
    """Motor de formulación y descomposición de planes de acción."""

    @property
    def engine_type(self) -> str:
        return "planner"


class VerifierEngine(BaseEngine, ABC):
    """Motor de verificación activa de resultados tras la ejecución de herramientas."""

    @property
    def engine_type(self) -> str:
        return "verifier"


# =====================================================================
# 4. Clase Base Abstracta de Plugins
# =====================================================================


class BasePlugin(ABC):
    """Clase base abstracta obligatoria para todos los plugins del ecosistema jg_agente.

    Define los contratos de registro de capacidades (tools, engines, modelos)
    así como los hooks de ciclo de vida e inspección de salud.
    """

    @abstractmethod
    def get_plugin_metadata(self) -> PluginMetadata:
        """Retorna los metadatos canónicos del plugin."""
        ...

    @abstractmethod
    def register_tools(self) -> list[AgentTool]:
        """Retorna la lista de AgentTool provistas por el plugin para su integración."""
        ...

    @abstractmethod
    def register_engines(self) -> dict[str, BaseEngine]:
        """Retorna los motores de dominio registrados por el plugin, mapeados por nombre."""
        ...

    def register_models(self) -> dict[str, type[BaseModel]]:
        """Hook opcional para declarar modelos Pydantic o extensiones de esquema del dominio."""
        return {}

    async def startup(self) -> None:  # noqa: B027
        """Hook asíncrono ejecutado durante el arranque del agente para inicializar el plugin."""

    async def shutdown(self) -> None:  # noqa: B027
        """Hook asíncrono ejecutado durante el apagado del agente para liberar recursos."""

    async def health_check(self) -> dict[str, Any]:
        """Verifica la operatividad del plugin y sus dependencias externas."""
        return {"status": "ok", "plugin": self.name}

    @property
    def name(self) -> str:
        """Acceso directo al nombre del plugin desde sus metadatos."""
        return self.get_plugin_metadata().name

    @property
    def version(self) -> str:
        """Acceso directo a la versión del plugin desde sus metadatos."""
        return self.get_plugin_metadata().version

    async def __aenter__(self) -> Self:
        """Soporte para gestor de contexto asíncrono con startup automático."""
        await self.startup()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Soporte para gestor de contexto asíncrono con shutdown automático."""
        await self.shutdown()
