# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Módulo cliente MCP nativo para jg_sdk."""

from jg_sdk.mcp.client import McpHttpClient
from jg_sdk.mcp.normalizer import (
    compute_canonical_schema_hash,
    normalize_to_json_primitives,
    truncate_text,
)
from jg_sdk.mcp.schemas import (
    JsonRpcError,
    JsonRpcRequest,
    JsonRpcResponse,
    McpClientError,
    McpToolDefinition,
    SchemaDriftError,
)

__all__ = [
    "JsonRpcError",
    "JsonRpcRequest",
    "JsonRpcResponse",
    "McpClientError",
    "McpHttpClient",
    "McpToolDefinition",
    "SchemaDriftError",
    "compute_canonical_schema_hash",
    "normalize_to_json_primitives",
    "truncate_text",
]
