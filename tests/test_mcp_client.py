# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Tests unitarios para el cliente MCP nativo McpHttpClient."""

import json
from typing import Any

import httpx
import pytest

from jg_sdk.mcp import (
    McpHttpClient,
    SchemaDriftError,
    compute_canonical_schema_hash,
)
from jg_sdk.security.ssrf import SSRFValidationError, SSRFValidator


@pytest.fixture
def ssrf_permissive_validator() -> SSRFValidator:
    """Validador SSRF que permite hostnames simulados para testing con mock."""
    return SSRFValidator(allowed_hosts=["api.mockmcp.com"])


@pytest.mark.asyncio
async def test_mcp_lifecycle_and_empty_capabilities(
    ssrf_permissive_validator: SSRFValidator,
) -> None:
    """Verifica el ciclo completo initialize -> tools/list -> tools/call."""
    sent_requests: list[dict[str, Any]] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        sent_requests.append(body)
        method = body.get("method")
        rpc_id = body.get("id")

        if method == "initialize":
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "mock-mcp-server", "version": "1.0.0"},
                    },
                },
            )
        if method == "tools/list":
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "result": {
                        "tools": [
                            {
                                "name": "echo_tool",
                                "description": "Devuelve el input",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {"message": {"type": "string"}},
                                    "required": ["message"],
                                },
                            }
                        ]
                    },
                },
            )
        if method == "tools/call":
            args = body.get("params", {}).get("arguments", {})
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Echo: {args.get('message')}"}],
                        "isError": False,
                    },
                },
            )
        return httpx.Response(
            404,
            json={
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {"code": -32601, "message": "Method not found"},
            },
        )

    transport = httpx.MockTransport(handle_request)
    client = McpHttpClient(
        base_url="https://api.mockmcp.com/mcp",
        transport=transport,
        ssrf_validator=ssrf_permissive_validator,
    )

    async with client:
        # 1. Initialize
        init_result = await client.initialize()
        assert init_result["serverInfo"]["name"] == "mock-mcp-server"

        # Comprobar que envió capabilities: {} estrictamente
        init_req = sent_requests[0]
        assert init_req["method"] == "initialize"
        assert init_req["params"]["capabilities"] == {}

        # 2. Tools list
        tools = await client.list_tools_with_pinning()
        assert len(tools) == 1
        assert tools[0].name == "echo_tool"

        # 3. Call tool
        tool_res = await client.call_tool("echo_tool", {"message": "hola mundo"})
        assert tool_res.success is True
        assert tool_res.output == "Echo: hola mundo"

        # 4. Invocación directa a través de AgentTool.run_async
        direct_res = await tools[0].run_async(message="test directo")
        assert direct_res.success is True
        assert direct_res.output == "Echo: test directo"


def test_schema_drift_detection(ssrf_permissive_validator: SSRFValidator) -> None:
    """Verifica detección de manipulación de esquema (Rug Pull / Schema Drift)."""
    client = McpHttpClient(
        base_url="https://api.mockmcp.com/mcp",
        ssrf_validator=ssrf_permissive_validator,
    )

    original_schema = {
        "name": "critical_tool",
        "description": "Herramienta segura",
        "inputSchema": {"type": "object", "properties": {"amount": {"type": "number"}}},
    }
    client._pinned_hashes["critical_tool"] = compute_canonical_schema_hash(original_schema)

    # Esquema sin alterar: verificación pasa
    client.verify_schema("critical_tool", original_schema)

    # Esquema alterado maliciosamente (parámetros añadidos o cambiados)
    altered_schema = {
        "name": "critical_tool",
        "description": "Herramienta segura alterada",
        "inputSchema": {"type": "object", "properties": {"destination": {"type": "string"}}},
    }
    with pytest.raises(SchemaDriftError, match="Schema drift detectado"):
        client.verify_schema("critical_tool", altered_schema)


@pytest.mark.asyncio
async def test_truncation_at_64kb(ssrf_permissive_validator: SSRFValidator) -> None:
    """Verifica el truncado estricto a 64 KB (65.536 bytes) de respuestas excesivas."""
    giant_text = "A" * 100_000

    def handle_giant(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {"content": [{"type": "text", "text": giant_text}], "isError": False},
            },
        )

    transport = httpx.MockTransport(handle_giant)
    client = McpHttpClient(
        base_url="https://api.mockmcp.com/mcp",
        transport=transport,
        ssrf_validator=ssrf_permissive_validator,
    )
    client._pinned_hashes["giant_tool"] = "dummy_hash"

    result = await client.call_tool("giant_tool", {})
    assert result.success is True
    assert "[TRUNCATED_AT_64KB]" in str(result.output)
    assert len(str(result.output).encode("utf-8")) <= 65536


@pytest.mark.asyncio
async def test_ssrf_blocking_private_base_url() -> None:
    """Verifica que destinos privados o loopback son rechazados antes del socket."""
    client = McpHttpClient(base_url="http://127.0.0.1:8000/mcp")
    with pytest.raises(SSRFValidationError, match="bloqueada por pertenecer a rango restringido"):
        await client.initialize()


@pytest.mark.asyncio
async def test_mcp_client_rejects_ssrf_redirect_metadata() -> None:
    """Verifica que redirecciones HTTP 302 a IP de metadatos cloud son bloqueadas."""

    def handle_redirect(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"Location": "http://169.254.169.254/latest/meta-data/"},
            request=request,
        )

    transport = httpx.MockTransport(handle_redirect)
    validator = SSRFValidator(allowed_hosts=["api.mockmcp.com"])
    client = McpHttpClient(
        base_url="https://api.mockmcp.com",
        transport=transport,
        ssrf_validator=validator,
        follow_redirects=False,
    )
    with pytest.raises(SSRFValidationError, match="Redirección.*prohibida"):
        await client.initialize()


@pytest.mark.asyncio
async def test_mcp_client_rejects_ssrf_redirect_localhost() -> None:
    """Verifica que redirecciones HTTP 302 a loopback son bloqueadas con follow_redirects=True."""

    def handle_redirect(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"Location": "http://127.0.0.1:8080/internal"},
            request=request,
        )

    transport = httpx.MockTransport(handle_redirect)
    validator = SSRFValidator(allowed_hosts=["api.mockmcp.com"])
    client = McpHttpClient(
        base_url="https://api.mockmcp.com",
        transport=transport,
        ssrf_validator=validator,
        follow_redirects=True,
    )
    with pytest.raises(SSRFValidationError, match="Redirección.*prohibida"):
        await client.initialize()


def test_serialization_primitives_safety() -> None:
    """Verifica que la salida normalizada sea serializable a JSON estándar sin errores."""
    from jg_sdk.mcp.normalizer import normalize_to_json_primitives

    complex_input = {
        "bytes_field": b"raw bytes",
        "nested_set": {"item1", "item2"},
        "none_val": None,
        "integer": 42,
    }
    normalized = normalize_to_json_primitives(complex_input)
    serialized = json.dumps(normalized)
    assert "raw bytes" in serialized
    assert isinstance(normalized["nested_set"], list)
