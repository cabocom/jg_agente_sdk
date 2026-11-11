# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Plantilla de generación de código para plugin.py."""

from __future__ import annotations


def get_plugin_class_template(
    template: str,
    pkg_name: str,
    plugin_class_name: str,
    class_prefix: str,
    raw_slug: str,
    description: str,
    author: str,
) -> str:
    """Genera el código de plugin.py."""
    if template == "minimal":
        return f'''"""Implementación principal del plugin {plugin_class_name}."""

from jg_sdk import BaseEngine, BasePlugin, PluginMetadata, AgentTool
from {pkg_name}.tools import query_tool


class {plugin_class_name}(BasePlugin):
    """Plugin {raw_slug} compatible con jg_agente."""

    def get_plugin_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="{raw_slug}",
            version="0.1.0",
            description="{description}",
            author="{author}",
            jg_agente_version_min="1.0.0",
            tags=["{raw_slug}"],
        )

    def register_tools(self) -> list[AgentTool]:
        return [query_tool]

    def register_engines(self) -> dict[str, BaseEngine]:
        return {{}}

    async def startup(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def health_check(self) -> dict:
        return {{"status": "ok", "plugin": self.name}}
'''
    elif template == "standard":
        return f'''"""Implementación principal del plugin {plugin_class_name}."""

from jg_sdk import BaseEngine, BasePlugin, PluginMetadata, AgentTool
from {pkg_name}.tools import inspect_tool, action_tool
from {pkg_name}.engines import {class_prefix}Observer


class {plugin_class_name}(BasePlugin):
    """Plugin {raw_slug} compatible con jg_agente."""

    def get_plugin_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="{raw_slug}",
            version="0.1.0",
            description="{description}",
            author="{author}",
            jg_agente_version_min="1.0.0",
            tags=["{raw_slug}"],
        )

    def register_tools(self) -> list[AgentTool]:
        return [inspect_tool, action_tool]

    def register_engines(self) -> dict[str, BaseEngine]:
        return {{"{raw_slug}_observer": {class_prefix}Observer()}}

    async def startup(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def health_check(self) -> dict:
        return {{"status": "ok", "plugin": self.name}}
'''
    else:  # full
        return f'''"""Implementación principal del plugin {plugin_class_name}."""

from jg_sdk import BaseEngine, BasePlugin, PluginMetadata, AgentTool
from {pkg_name}.tools import telemetry_tool, apply_config_tool
from {pkg_name}.engines import (
    {class_prefix}Observer,
    {class_prefix}Planner,
    {class_prefix}Verifier,
)


class {plugin_class_name}(BasePlugin):
    """Plugin {raw_slug} compatible con jg_agente."""

    def get_plugin_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="{raw_slug}",
            version="0.1.0",
            description="{description}",
            author="{author}",
            jg_agente_version_min="1.0.0",
            tags=["{raw_slug}"],
        )

    def register_tools(self) -> list[AgentTool]:
        return [telemetry_tool, apply_config_tool]

    def register_engines(self) -> dict[str, BaseEngine]:
        return {{
            "{raw_slug}_observer": {class_prefix}Observer(),
            "{raw_slug}_planner": {class_prefix}Planner(),
            "{raw_slug}_verifier": {class_prefix}Verifier(),
        }}

    async def startup(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def health_check(self) -> dict:
        return {{"status": "ok", "plugin": self.name}}
'''
