# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Tests de validación de contratos, esquemas y ciclo de vida de jg_sdk."""

import time
import unittest
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from jg_sdk.contracts import (
    AgentTool,
    BaseEngine,
    BasePlugin,
    ExecutionStatus,
    PluginMetadata,
    RiskLevel,
    StepStatus,
    ToolResult,
    ToolType,
)


class TestEnums(unittest.TestCase):
    """Valida los valores y tipo de enums canónicos."""

    def test_risk_level_values(self) -> None:
        self.assertEqual(RiskLevel.LOW, "low")
        self.assertEqual(RiskLevel.MEDIUM, "medium")
        self.assertEqual(RiskLevel.HIGH, "high")
        self.assertEqual(RiskLevel.CRITICAL, "critical")

    def test_tool_type_values(self) -> None:
        self.assertEqual(ToolType.OBSERVER, "observer")
        self.assertEqual(ToolType.ACTUATOR, "actuator")
        self.assertEqual(ToolType.VERIFIER, "verifier")
        self.assertEqual(ToolType.READ, "read")
        self.assertEqual(ToolType.MUTATION, "mutation")

    def test_execution_status_values(self) -> None:
        self.assertEqual(ExecutionStatus.COMPLETED, "completed")
        self.assertEqual(ExecutionStatus.WAITING_APPROVAL, "waiting_approval")
        self.assertEqual(ExecutionStatus.FAILED, "failed")
        self.assertEqual(ExecutionStatus.CANCELLED, "cancelled")
        self.assertEqual(ExecutionStatus.IN_PROGRESS, "in_progress")
        self.assertEqual(ExecutionStatus.TIMEOUT, "timeout")

    def test_step_status_values(self) -> None:
        self.assertEqual(StepStatus.PENDING, "pending")
        self.assertEqual(StepStatus.RUNNING, "running")
        self.assertEqual(StepStatus.COMPLETED, "completed")
        self.assertEqual(StepStatus.FAILED, "failed")
        self.assertEqual(StepStatus.SKIPPED, "skipped")
        self.assertEqual(StepStatus.TIMED_OUT, "timed_out")


class TestPluginMetadata(unittest.TestCase):
    """Valida los metadatos de plugins y las reglas de validación de slugs."""

    def test_valid_metadata(self) -> None:
        meta = PluginMetadata(
            name="valid_plugin-01",
            version="1.2.3",
            description="Plugin descriptivo",
            author="Test Author",
            tags=["tag1", "tag2"],
        )
        self.assertEqual(meta.name, "valid_plugin-01")
        self.assertEqual(meta.version, "1.2.3")
        self.assertTrue(meta.enabled)
        self.assertEqual(meta.jg_agente_version_min, "1.0.0")

    def test_invalid_name_spaces(self) -> None:
        with self.assertRaises(ValidationError):
            PluginMetadata(name="invalid name", version="1.0.0")

    def test_invalid_name_special_chars(self) -> None:
        with self.assertRaises(ValidationError):
            PluginMetadata(name="plugin@bad!", version="1.0.0")

    def test_invalid_empty_name(self) -> None:
        with self.assertRaises(ValidationError):
            PluginMetadata(name="", version="1.0.0")


class TestAgentTool(unittest.TestCase):
    """Valida la especificación, ejecución, timeouts y compensaciones de AgentTool."""

    class DummyArgs(BaseModel):
        param_x: int = Field(..., gt=0)
        param_y: str = Field(default="default_val")

    def test_agent_tool_creation(self) -> None:
        def my_func(param_x: int, param_y: str = "default") -> str:
            return f"{param_x}-{param_y}"

        tool = AgentTool(
            name="test_tool",
            description="Herramienta de prueba",
            args_schema=self.DummyArgs,
            func=my_func,
            risk_level=RiskLevel.LOW,
            tool_type=ToolType.READ,
        )
        self.assertEqual(tool.name, "test_tool")
        self.assertEqual(tool.risk_level, RiskLevel.LOW)
        self.assertEqual(tool.tool_type, ToolType.READ)
        self.assertTrue(tool.read_only)
        self.assertFalse(tool.reversible)

    def test_reversible_without_rollback_raises_error(self) -> None:
        def my_func() -> str:
            return "ok"

        with self.assertRaises(ValueError) as ctx:
            AgentTool(
                name="bad_reversible",
                description="desc",
                func=my_func,
                reversible=True,
                rollback_func=None,
            )
        self.assertIn("rollback_func", str(ctx.exception))

    def test_rollback_func_sets_reversible_true(self) -> None:
        def my_func() -> str:
            return "ok"

        def my_rollback(ctx: dict[str, Any]) -> ToolResult:
            return ToolResult(success=True, output="reverted")

        tool = AgentTool(
            name="good_reversible",
            description="desc",
            func=my_func,
            reversible=False,
            rollback_func=my_rollback,
        )
        self.assertTrue(tool.reversible)

    def test_run_success_output(self) -> None:
        def adder(x: int, y: int) -> int:
            return x + y

        tool = AgentTool(
            name="adder",
            description="Suma dos números",
            func=adder,
        )
        result = tool.run(x=5, y=10)
        self.assertIsInstance(result, ToolResult)
        self.assertTrue(result.success)
        self.assertEqual(result.output, 15)
        self.assertGreaterEqual(result.duration_ms, 0.0)

    def test_run_timeout_handling(self) -> None:
        def slow_func() -> str:
            time.sleep(0.5)
            return "finished"

        tool = AgentTool(
            name="slow_tool",
            description="Herramienta lenta",
            func=slow_func,
            timeout_sec=0.1,
        )
        result = tool.run()
        self.assertFalse(result.success)
        self.assertIn("TimeoutError", result.error or "")
        self.assertTrue(result.metadata.get("timed_out"))

    def test_rollback_execution(self) -> None:
        def rollback_fn(context: dict[str, Any]) -> ToolResult:
            item_id = context.get("item_id")
            return ToolResult(success=True, output=f"Item {item_id} deleted")

        tool = AgentTool(
            name="reversible_tool",
            description="desc",
            func=lambda: "done",
            reversible=True,
            rollback_func=rollback_fn,
        )
        res = tool.rollback({"item_id": "42"})
        self.assertTrue(res.success)
        self.assertEqual(res.output, "Item 42 deleted")
        self.assertTrue(res.metadata.get("rollback_executed"))

    def test_rollback_non_reversible_tool(self) -> None:
        tool = AgentTool(
            name="read_only_tool",
            description="desc",
            func=lambda: "done",
            reversible=False,
        )
        res = tool.rollback({})
        self.assertFalse(res.success)
        self.assertEqual(res.error, "NO_ROLLBACK_AVAILABLE")


class TestBasePlugin(unittest.IsolatedAsyncioTestCase):
    """Valida los contratos de BasePlugin y su ciclo de vida asíncrono."""

    class MinimalPlugin(BasePlugin):
        def __init__(self) -> None:
            self.started = False
            self.stopped = False

        def get_plugin_metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name="minimal-test-plugin",
                version="1.0.0",
                description="Plugin para test de BasePlugin",
            )

        def register_tools(self) -> list[AgentTool]:
            return []

        def register_engines(self) -> dict[str, BaseEngine]:
            return {}

        async def startup(self) -> None:
            self.started = True

        async def shutdown(self) -> None:
            self.stopped = True

    async def test_base_plugin_lifecycle(self) -> None:
        plugin = self.MinimalPlugin()
        self.assertEqual(plugin.name, "minimal-test-plugin")
        self.assertEqual(plugin.version, "1.0.0")

        async with plugin as p:
            self.assertTrue(p.started)
            self.assertFalse(p.stopped)
            health = await p.health_check()
            self.assertEqual(health.get("status"), "ok")

        self.assertTrue(plugin.stopped)

    def test_cannot_instantiate_incomplete_subclass(self) -> None:
        class IncompletePlugin(BasePlugin):
            pass

        with self.assertRaises(TypeError):
            IncompletePlugin()  # type: ignore


if __name__ == "__main__":
    unittest.main()
