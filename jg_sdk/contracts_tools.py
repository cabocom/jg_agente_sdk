# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Contratos de herramientas y resultados normalizados de ejecución."""

import asyncio
import concurrent.futures
import inspect
import time
from collections.abc import Callable
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from jg_sdk.contracts_enums import RiskLevel, ToolType


def _normalize_tool_result(res: Any, duration_ms: float) -> "ToolResult":
    """Normaliza cualquier retorno de ejecución en un ToolResult estándar."""
    d = round(duration_ms, 2)
    if isinstance(res, ToolResult):
        if res.duration_ms <= 0.0:
            res.duration_ms = d
        return res
    if isinstance(res, str):
        return ToolResult(success=True, output=res, duration_ms=d)
    if isinstance(res, bool):
        return ToolResult(
            success=res,
            output="Operación exitosa" if res else "Operación fallida",
            duration_ms=d,
        )
    return ToolResult(success=True, output=res, duration_ms=d)


def _handle_tool_error(
    exc: Exception, name: str, timeout: float, start_time: float
) -> "ToolResult":
    """Genera ToolResult estándar ante fallos o tiempos de espera agotados."""
    d = round((time.perf_counter() - start_time) * 1000, 2)
    if isinstance(exc, TimeoutError):
        return ToolResult(
            success=False,
            output="",
            error=f"TimeoutError: La herramienta '{name}' superó el tiempo límite de {timeout}s",
            duration_ms=d,
            metadata={"timeout_sec": timeout, "timed_out": True},
        )
    return ToolResult(success=False, output="", error=str(exc), duration_ms=d)


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

    @property
    def is_async(self) -> bool:
        """Indica si la función subyacente de la herramienta es asíncrona."""
        return inspect.iscoroutinefunction(self.func)

    def run(self, *args: Any, **kwargs: Any) -> ToolResult:
        """Ejecuta la herramienta de forma síncrona controlando el timeout asignado."""
        if self.is_async:

            def _runner() -> ToolResult:
                return asyncio.run(self.run_async(*args, **kwargs))

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                return executor.submit(_runner).result()

        start_time = time.perf_counter()
        timeout = self.timeout_sec or 30.0
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.func, *args, **kwargs)
                res = future.result(timeout=timeout)
            return _normalize_tool_result(res, (time.perf_counter() - start_time) * 1000)
        except Exception as exc:
            return _handle_tool_error(exc, self.name, timeout, start_time)

    async def run_async(self, *args: Any, **kwargs: Any) -> ToolResult:
        """Ejecuta la herramienta de forma asíncrona controlando el timeout asignado."""
        start_time = time.perf_counter()
        timeout = self.timeout_sec or 30.0
        try:
            if self.is_async:
                res = await asyncio.wait_for(self.func(*args, **kwargs), timeout=timeout)
            else:
                res = await asyncio.wait_for(
                    asyncio.to_thread(self.func, *args, **kwargs),
                    timeout=timeout,
                )
            return _normalize_tool_result(res, (time.perf_counter() - start_time) * 1000)
        except Exception as exc:
            return _handle_tool_error(exc, self.name, timeout, start_time)

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

__all__ = [
    "AgentTool",
    "ToolResult",
]
