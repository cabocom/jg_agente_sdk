# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Modelos y esquemas de datos JSON-RPC 2.0 y protocolo MCP."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class McpClientError(Exception):
    """Excepción base para errores en el cliente MCP."""

    def __init__(self, message: str, code: int | None = None, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.data = data


class SchemaDriftError(McpClientError):
    """Excepción lanzada cuando el esquema remoto de una tool difiere del pinned hash."""


class JsonRpcRequest(BaseModel):
    """Estructura de petición estándar JSON-RPC 2.0."""

    model_config = ConfigDict(extra="forbid")

    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int
    method: str
    params: dict[str, Any] | None = None


class JsonRpcError(BaseModel):
    """Estructura de error estándar JSON-RPC 2.0."""

    model_config = ConfigDict(extra="allow")

    code: int
    message: str
    data: Any = None


class JsonRpcResponse(BaseModel):
    """Estructura de respuesta estándar JSON-RPC 2.0."""

    model_config = ConfigDict(extra="allow")

    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int | None = None
    result: Any = None
    error: JsonRpcError | None = None


class McpToolDefinition(BaseModel):
    """Definición de herramienta expuesta por un servidor MCP."""

    model_config = ConfigDict(extra="allow")

    name: str
    description: str = ""
    inputSchema: dict[str, Any] = Field(default_factory=dict)
