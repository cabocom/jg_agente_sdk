# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Cliente nativo HTTP para consumo de servidores MCP con Schema Pinning."""

import logging
import uuid
from typing import Any

import httpx

from jg_sdk.contracts_enums import RiskLevel
from jg_sdk.contracts_tools import AgentTool, ToolResult
from jg_sdk.mcp.normalizer import (
    compute_canonical_schema_hash,
    normalize_to_json_primitives,
    truncate_text,
)
from jg_sdk.mcp.schemas import (
    JsonRpcRequest,
    JsonRpcResponse,
    McpClientError,
    SchemaDriftError,
)
from jg_sdk.security.ssrf import SSRFValidationError, SSRFValidator
from jg_sdk.version import __version__

logger = logging.getLogger("jg_sdk.mcp.client")


class McpHttpClient:
    """Cliente HTTP nativo para integración con servidores MCP vía Streamable HTTP."""

    def __init__(
        self,
        base_url: str,
        timeout_sec: float = 30.0,
        max_output_bytes: int = 65536,
        transport: httpx.AsyncBaseTransport | None = None,
        ssrf_validator: SSRFValidator | None = None,
        headers: dict[str, str] | None = None,
        follow_redirects: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec
        self.max_output_bytes = max_output_bytes
        self._transport = transport
        self._ssrf_validator = ssrf_validator or SSRFValidator()
        self._headers = headers or {}
        self._follow_redirects = follow_redirects
        self._client: httpx.AsyncClient | None = None
        self._pinned_hashes: dict[str, str] = {}
        self._discovered_tools: dict[str, dict[str, Any]] = {}
        self._initialized = False

    async def _on_response(self, response: httpx.Response) -> None:
        if response.is_redirect:
            location = response.headers.get("Location")
            if location:
                redirect_url = str(response.url.join(location))
                is_safe, reason = await self._ssrf_validator.validate_url_async(redirect_url)
                if not is_safe:
                    raise SSRFValidationError(
                        f"Redirección prohibida por política SSRF hacia '{redirect_url}': {reason}",
                        target=redirect_url,
                    )

    async def _get_client(self) -> httpx.AsyncClient:
        """Inicializa y devuelve el cliente HTTP tras validar la URL contra SSRF."""
        if self._client is None or self._client.is_closed:
            is_safe, reason = await self._ssrf_validator.validate_url_async(self.base_url)
            if not is_safe:
                raise SSRFValidationError(
                    reason or f"Destino no permitido por SSRF: {self.base_url}",
                    target=self.base_url,
                )
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_sec,
                follow_redirects=self._follow_redirects,
                transport=self._transport,
                headers={"Content-Type": "application/json", **self._headers},
                event_hooks={"response": [self._on_response]},
            )
        return self._client

    async def _check_response_status(self, response: httpx.Response) -> None:
        if response.is_redirect or (300 <= response.status_code < 400):
            location = response.headers.get("Location", "")
            if location:
                redirect_url = str(response.url.join(location))
                is_safe, reason = await self._ssrf_validator.validate_url_async(redirect_url)
                if not is_safe:
                    raise SSRFValidationError(
                        f"Redirección HTTP {response.status_code} prohibida por política SSRF hacia '{redirect_url}': {reason}",
                        target=redirect_url,
                    )
            raise McpClientError(
                f"Redirección HTTP {response.status_code} no permitida en transporte MCP hacia '{location}'",
                code=response.status_code,
            )
        if response.status_code >= 400:
            raise McpClientError(
                f"Error HTTP {response.status_code} del servidor MCP",
                code=response.status_code,
            )

    async def _send_rpc(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """Envía una llamada JSON-RPC 2.0 y retorna el resultado procesado."""
        client = await self._get_client()
        req = JsonRpcRequest(id=str(uuid.uuid4()), method=method, params=params)
        response = await client.post("", json=req.model_dump(exclude_none=True))
        await self._check_response_status(response)
        rpc_resp = JsonRpcResponse.model_validate(response.json())
        if rpc_resp.error:
            raise McpClientError(
                f"Error RPC: {rpc_resp.error.message}",
                code=rpc_resp.error.code,
                data=rpc_resp.error.data,
            )
        return rpc_resp.result

    async def initialize(self, protocol_version: str = "2024-11-05") -> dict[str, Any]:
        """Ejecuta el handshake MCP declarando capabilities estrictamente vacías."""
        payload = {
            "protocolVersion": protocol_version,
            "capabilities": {},
            "clientInfo": {"name": "jg_agente_sdk", "version": __version__},
        }
        result = await self._send_rpc("initialize", payload)
        self._initialized = True
        return normalize_to_json_primitives(result)

    def compute_schema_hash(self, tool_def: dict[str, Any]) -> str:
        """Calcula el hash canónico determinista de una definición de herramienta."""
        return compute_canonical_schema_hash(tool_def)

    def verify_schema(self, name: str, current_def: dict[str, Any]) -> None:
        """Verifica que el esquema actual coincida con el pinned hash."""
        expected_hash = self._pinned_hashes.get(name)
        if expected_hash is None:
            raise McpClientError(f"Herramienta '{name}' no registrada previamente.")
        actual_hash = self.compute_schema_hash(current_def)
        if actual_hash != expected_hash:
            raise SchemaDriftError(
                f"Schema drift detectado en '{name}': hash esperado {expected_hash}, actual {actual_hash}"
            )

    def _create_tool_caller(self, tool_name: str) -> Any:
        """Crea una función asíncrona de invocación vinculada al nombre de la herramienta."""

        async def _caller(**kwargs: Any) -> ToolResult:
            return await self.call_tool(tool_name, kwargs)

        return _caller

    async def list_tools_with_pinning(self) -> list[AgentTool]:
        """Descubre las herramientas del servidor MCP y fija sus hashes de esquema."""
        result = await self._send_rpc("tools/list")
        tools_list: list[dict[str, Any]] = (
            result.get("tools", []) if isinstance(result, dict) else []
        )
        agent_tools: list[AgentTool] = []

        for raw_tool in tools_list:
            name = str(raw_tool.get("name", "")).strip()
            if not name:
                continue
            schema_hash = self.compute_schema_hash(raw_tool)
            self._pinned_hashes[name] = schema_hash
            self._discovered_tools[name] = raw_tool

            agent_tools.append(
                AgentTool(
                    name=name,
                    description=str(raw_tool.get("description", "")),
                    func=self._create_tool_caller(name),
                    risk_level=RiskLevel.LOW,
                )
            )
        return agent_tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """Invoca la herramienta remota con normalización estricta y truncado a 64 KB."""
        if name not in self._pinned_hashes:
            raise McpClientError(f"Herramienta '{name}' no descubierta o sin pinning.")

        result = await self._send_rpc("tools/call", {"name": name, "arguments": arguments})
        is_error = bool(result.get("isError", False)) if isinstance(result, dict) else False
        content_items = result.get("content", []) if isinstance(result, dict) else []

        text_parts = [
            str(item.get("text", ""))
            for item in content_items
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        raw_output = "\n".join(text_parts) if text_parts else str(result)
        truncated_output = truncate_text(raw_output, max_bytes=self.max_output_bytes)
        normalized_data = normalize_to_json_primitives(result)

        return ToolResult(
            success=not is_error,
            output=truncated_output,
            error=raw_output if is_error else None,
            metadata={"mcp_data": normalized_data},
        )

    async def aclose(self) -> None:
        """Cierra la sesión y conexiones activas del cliente HTTP."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> "McpHttpClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.aclose()
