# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Plantilla de generación de código para tests/test_plugin.py."""

from __future__ import annotations


def get_test_template(template: str, pkg_name: str, plugin_class_name: str, raw_slug: str) -> str:
    """Genera el código de tests/test_plugin.py."""
    if template == "minimal":
        return f'''"""Pruebas unitarias para {plugin_class_name}."""

import pytest
from jg_sdk.testing import MockPluginRunner
from {pkg_name}.plugin import {plugin_class_name}


@pytest.mark.asyncio
async def test_plugin_metadata_and_health():
    plugin = {plugin_class_name}()
    async with MockPluginRunner(plugin) as runner:
        meta = runner.metadata
        assert meta.name == "{raw_slug}"
        assert meta.version == "0.1.0"

        health = await runner.health_check()
        assert health["status"] == "ok"


@pytest.mark.asyncio
async def test_tool_execution():
    plugin = {plugin_class_name}()
    async with MockPluginRunner(plugin) as runner:
        res = runner.run_tool("{raw_slug}_query", {{"query": "diagnostico_inicial"}})
        assert res.success is True
        assert "diagnostico_inicial" in str(res.output)
'''
    elif template == "standard":
        return f'''"""Pruebas unitarias para {plugin_class_name}."""

import pytest
from jg_sdk.testing import MockPluginRunner
from {pkg_name}.plugin import {plugin_class_name}


@pytest.mark.asyncio
async def test_plugin_lifecycle_and_observer():
    plugin = {plugin_class_name}()
    async with MockPluginRunner(plugin) as runner:
        assert runner.metadata.name == "{raw_slug}"
        health = await runner.health_check()
        assert health["status"] == "ok"

        engines = plugin.register_engines()
        assert "{raw_slug}_observer" in engines
        obs_res = await engines["{raw_slug}_observer"].observe()
        assert obs_res["status"] == "operational"


@pytest.mark.asyncio
async def test_inspect_tool():
    plugin = {plugin_class_name}()
    async with MockPluginRunner(plugin) as runner:
        res = runner.run_tool("{raw_slug}_inspect", {{"target": "servicio_principal"}})
        assert res.success is True
        assert res.metadata["status"] == "healthy"


@pytest.mark.asyncio
async def test_action_tool_and_rollback():
    plugin = {plugin_class_name}()
    async with MockPluginRunner(plugin) as runner:
        tool = runner.get_tool("{raw_slug}_action")
        assert tool.reversible is True

        res = runner.run_tool(
            "{raw_slug}_action",
            {{"resource_id": "res_001", "parameters": {{"retry": 3}}}},
        )
        assert res.success is True
        assert res.rollback_context is not None

        # Probar compensación de rollback
        assert tool.rollback_func is not None
        rb_res = tool.rollback_func(res.rollback_context)
        assert rb_res.success is True
'''
    else:  # full
        return f'''"""Pruebas unitarias para {plugin_class_name}."""

import pytest
from jg_sdk.testing import MockPluginRunner
from {pkg_name}.plugin import {plugin_class_name}


@pytest.mark.asyncio
async def test_full_engines():
    plugin = {plugin_class_name}()
    async with MockPluginRunner(plugin) as runner:
        health = await runner.health_check()
        assert health["status"] == "ok"

        engines = plugin.register_engines()
        assert "{raw_slug}_observer" in engines
        assert "{raw_slug}_planner" in engines
        assert "{raw_slug}_verifier" in engines

        plan = await engines["{raw_slug}_planner"].plan("test_intent")
        assert len(plan) >= 1

        v_res = await engines["{raw_slug}_verifier"].verify()
        assert v_res["resolved"] is True


@pytest.mark.asyncio
async def test_tools():
    plugin = {plugin_class_name}()
    async with MockPluginRunner(plugin) as runner:
        res_tel = runner.run_tool("{raw_slug}_telemetry", {{"metric": "cpu_load"}})
        assert res_tel.success is True

        res_apply = runner.run_tool(
            "{raw_slug}_apply_config",
            {{"service_id": "s1", "config_key": "timeout", "new_value": "60"}},
        )
        assert res_apply.success is True
        assert res_apply.rollback_context is not None
'''
