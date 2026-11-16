# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Pruebas unitarias para soporte nativo de herramientas asíncronas en AgentTool y MockPluginRunner."""

import asyncio

import pytest
from pydantic import BaseModel, Field

from jg_sdk.contracts import (
    AgentTool,
    BaseEngine,
    BasePlugin,
    PluginMetadata,
    ToolResult,
    ToolType,
)
from jg_sdk.testing import MockPluginRunner


class SampleInput(BaseModel):
    name: str = Field(..., description="Nombre del objetivo")
    multiplier: int = Field(default=2, ge=1)


async def sample_async_func(name: str, multiplier: int = 2) -> str:
    """Función asíncrona de prueba."""
    await asyncio.sleep(0.01)
    return f"Hola {name} * {multiplier}"


async def sample_slow_async_func(name: str) -> str:
    """Función asíncrona lenta para probar timeouts."""
    await asyncio.sleep(0.5)
    return f"Completado tarde: {name}"


def sample_sync_func(name: str, multiplier: int = 2) -> str:
    """Función síncrona de prueba."""
    return f"Sync {name} * {multiplier}"


class DummyAsyncPlugin(BasePlugin):
    """Plugin de prueba con herramientas síncronas y asíncronas."""

    def get_plugin_metadata(self) -> PluginMetadata:
        return PluginMetadata(name="dummy_async", version="1.0.0")

    def register_tools(self) -> list[AgentTool]:
        return [
            AgentTool(
                name="async_tool",
                description="Herramienta asíncrona de prueba",
                func=sample_async_func,
                args_schema=SampleInput,
                tool_type=ToolType.OBSERVER,
                timeout_sec=5.0,
            ),
            AgentTool(
                name="slow_async_tool",
                description="Herramienta lenta para timeouts",
                func=sample_slow_async_func,
                timeout_sec=0.05,
            ),
            AgentTool(
                name="sync_tool",
                description="Herramienta síncrona de prueba",
                func=sample_sync_func,
                args_schema=SampleInput,
                timeout_sec=5.0,
            ),
        ]

    def register_engines(self) -> dict[str, BaseEngine]:
        return {}


@pytest.mark.asyncio
async def test_agent_tool_is_async_property() -> None:
    """Verifica que is_async detecta correctamente corutinas vs funciones síncronas."""
    async_tool = AgentTool(
        name="test_async",
        description="test",
        func=sample_async_func,
    )
    sync_tool = AgentTool(
        name="test_sync",
        description="test",
        func=sample_sync_func,
    )
    assert async_tool.is_async is True
    assert sync_tool.is_async is False


@pytest.mark.asyncio
async def test_agent_tool_run_async_success() -> None:
    """Verifica que run_async resuelve corutinas y devuelve ToolResult con output."""
    tool = AgentTool(
        name="test_async",
        description="test",
        func=sample_async_func,
    )
    res = await tool.run_async(name="Mundo", multiplier=3)
    assert isinstance(res, ToolResult)
    assert res.success is True
    assert res.output == "Hola Mundo * 3"
    assert res.duration_ms > 0


@pytest.mark.asyncio
async def test_agent_tool_run_async_timeout() -> None:
    """Verifica que run_async aplica timeout_sec y devuelve error estructurado."""
    tool = AgentTool(
        name="test_slow",
        description="test",
        func=sample_slow_async_func,
        timeout_sec=0.05,
    )
    res = await tool.run_async(name="TimeoutTest")
    assert isinstance(res, ToolResult)
    assert res.success is False
    assert "TimeoutError" in str(res.error)
    assert res.metadata.get("timed_out") is True


def test_agent_tool_sync_run_handles_async_func() -> None:
    """Verifica que run() síncrono puede resolver una función asíncrona sin devolver coroutine."""
    tool = AgentTool(
        name="test_async",
        description="test",
        func=sample_async_func,
    )
    res = tool.run(name="SyncCaller", multiplier=4)
    assert isinstance(res, ToolResult)
    assert res.success is True
    assert res.output == "Hola SyncCaller * 4"


@pytest.mark.asyncio
async def test_mock_plugin_runner_async_tool() -> None:
    """Verifica que MockPluginRunner.run_tool_async ejecuta y valida argumentos Pydantic."""
    plugin = DummyAsyncPlugin()
    runner = MockPluginRunner(plugin)
    await runner.startup()

    # Ejecución asíncrona pasando dict
    res_dict = await runner.run_tool_async("async_tool", {"name": "Javier", "multiplier": 5})
    assert res_dict.success is True
    assert res_dict.output == "Hola Javier * 5"

    # Ejecución asíncrona pasando BaseModel
    model_input = SampleInput(name="Galvez", multiplier=2)
    res_model = await runner.run_tool_async("async_tool", model_input)
    assert res_model.success is True
    assert res_model.output == "Hola Galvez * 2"

    # Herramienta síncrona vía runner asíncrono
    res_sync = await runner.run_tool_async("sync_tool", {"name": "Prueba"})
    assert res_sync.success is True
    assert res_sync.output == "Sync Prueba * 2"

    await runner.shutdown()
