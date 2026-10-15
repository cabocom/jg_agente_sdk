# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez <contacto@javiergalvez.com>
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Test end-to-end de un plugin de prueba desarrollado exclusivamente con jg_sdk."""

import unittest
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from jg_sdk import (
    AgentTool,
    BaseEngine,
    BasePlugin,
    MockPluginRunner,
    ObserverEngine,
    PluginMetadata,
    RiskLevel,
    ToolResult,
    ToolType,
)

# =====================================================================
# 1. Definición del Plugin de Ejemplo (desarrollado con jg_sdk)
# =====================================================================


class PingArgs(BaseModel):
    """Esquema tipado para la herramienta ping."""

    host: str = Field(..., min_length=1, description="Host o IP a diagnosticar")
    count: int = Field(default=3, ge=1, le=5, description="Número de paquetes")


class BlockIpArgs(BaseModel):
    """Esquema para bloqueo reversible de tráfico sospechoso."""

    ip: str = Field(..., min_length=7, description="Dirección IP a bloquear")
    reason: str = Field(default="Tráfico anómalo", description="Motivo del bloqueo")


class NetworkObserver(ObserverEngine):
    """Motor de observación de red provisto por el plugin."""

    @property
    def name(self) -> str:
        return "network_observer"


class NetworkDiagnosticsPlugin(BasePlugin):
    """Plugin de ejemplo para telemetría y aislamiento de red."""

    def __init__(self) -> None:
        self.blocked_ips: set[str] = set()
        self.is_active = False

    def get_plugin_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="network-diagnostics",
            version="1.0.0",
            description="Herramientas de diagnóstico de red y mitigación perimetral.",
            author="Platform Core Team",
            tags=["network", "security"],
        )

    def register_tools(self) -> list[AgentTool]:
        def ping_func(host: str, count: int = 3) -> ToolResult:
            return ToolResult(
                success=True,
                output=f"Ping exitoso a {host}: {count} paquetes transmitidos, 0% packet loss.",
                metadata={"host": host, "count": count},
            )

        def block_ip_func(ip: str, reason: str = "Tráfico anómalo") -> ToolResult:
            self.blocked_ips.add(ip)
            return ToolResult(
                success=True,
                output=f"IP {ip} bloqueada en firewall perimetral por: {reason}",
                rollback_context={"blocked_ip": ip},
            )

        def rollback_block_ip(rollback_context: dict[str, Any]) -> ToolResult:
            ip = rollback_context["blocked_ip"]
            if ip in self.blocked_ips:
                self.blocked_ips.remove(ip)
            return ToolResult(
                success=True,
                output=f"IP {ip} desbloqueada exitosamente del firewall.",
            )

        return [
            AgentTool(
                name="ping_host",
                description="Diagnostica latencia y alcanzabilidad de un host remoto.",
                category="network",
                args_schema=PingArgs,
                func=ping_func,
                risk_level=RiskLevel.LOW,
                tool_type=ToolType.OBSERVER,
                read_only=True,
                timeout_sec=5.0,
            ),
            AgentTool(
                name="block_ip",
                description="Bloquea temporalmente una IP en el cortafuegos.",
                category="firewall",
                args_schema=BlockIpArgs,
                func=block_ip_func,
                risk_level=RiskLevel.HIGH,
                tool_type=ToolType.MUTATION,
                read_only=False,
                reversible=True,
                rollback_func=rollback_block_ip,
            ),
        ]

    def register_engines(self) -> dict[str, BaseEngine]:
        return {"network_observer": NetworkObserver()}

    async def startup(self) -> None:
        self.is_active = True

    async def shutdown(self) -> None:
        self.is_active = False

    async def health_check(self) -> dict[str, Any]:
        return {"status": "ok", "plugin": self.name, "active": self.is_active}


# =====================================================================
# 2. Test Suite usando MockPluginRunner
# =====================================================================


class TestNetworkPluginWithMockRunner(unittest.IsolatedAsyncioTestCase):
    """Valida el plugin utilizando el arnés de desarrollo MockPluginRunner."""

    async def test_plugin_full_flow(self) -> None:
        plugin = NetworkDiagnosticsPlugin()

        async with MockPluginRunner(plugin) as runner:
            # 1. Comprobación de metadatos y salud
            self.assertEqual(runner.metadata.name, "network-diagnostics")
            self.assertEqual(runner.metadata.version, "1.0.0")

            health = await runner.health_check()
            self.assertEqual(health["status"], "ok")
            self.assertTrue(health["active"])

            # 2. Comprobación de herramientas y motores registrados
            tools = runner.list_tools()
            self.assertEqual(len(tools), 2)
            engines = runner.list_engines()
            self.assertIn("network_observer", engines)

            # 3. Invocación de herramienta pasando un modelo Pydantic directamente
            ping_args = PingArgs(host="192.168.1.1", count=4)
            result_ping = runner.run_tool("ping_host", ping_args)
            self.assertTrue(result_ping.success)
            self.assertIn("192.168.1.1", str(result_ping.output))
            self.assertEqual(result_ping.metadata.get("count"), 4)

            # 4. Invocación pasando un diccionario (se valida contra args_schema)
            result_dict = runner.run_tool("ping_host", {"host": "10.0.0.1", "count": 2})
            self.assertTrue(result_dict.success)
            self.assertIn("10.0.0.1", str(result_dict.output))

            # 5. Invocación con argumentos inválidos (debe disparar ValidationError de Pydantic)
            with self.assertRaises(ValidationError):
                # count > 5 viola le=5
                runner.run_tool("ping_host", {"host": "10.0.0.1", "count": 10})

            # 6. Invocación de herramienta reversible (bloqueo)
            block_res = runner.run_tool(
                "block_ip",
                BlockIpArgs(ip="203.0.113.55", reason="Ataque DDoS detectado"),
            )
            self.assertTrue(block_res.success)
            self.assertIn("203.0.113.55", str(block_res.output))
            self.assertIn("203.0.113.55", plugin.blocked_ips)
            self.assertIsNotNone(block_res.rollback_context)

            # 7. Ejecución de compensación (rollback) usando el contexto devuelto
            rollback_res = runner.rollback_tool("block_ip", block_res.rollback_context or {})
            self.assertTrue(rollback_res.success)
            self.assertIn("desbloqueada exitosamente", str(rollback_res.output))
            self.assertNotIn("203.0.113.55", plugin.blocked_ips)

        # 8. Comprobación tras shutdown del contexto
        self.assertFalse(plugin.is_active)


if __name__ == "__main__":
    unittest.main()
