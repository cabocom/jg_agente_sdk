# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Paquete de plantillas de generación de código y scaffolding para plugins."""

from __future__ import annotations

from jg_sdk.cli.templates.config import (
    get_env_templates,
    get_gitignore_template,
    get_install_script_template,
    get_pyproject_template,
)
from jg_sdk.cli.templates.docker import (
    get_docker_compose_template,
    get_docker_entrypoint_template,
)
from jg_sdk.cli.templates.docs import (
    get_readme_template,
)
from jg_sdk.cli.templates.engines import (
    get_engines_template,
)
from jg_sdk.cli.templates.plugin import (
    get_plugin_class_template,
)
from jg_sdk.cli.templates.tests import (
    get_test_template,
)
from jg_sdk.cli.templates.tools import (
    get_tools_template,
)

__all__ = [
    "get_docker_compose_template",
    "get_docker_entrypoint_template",
    "get_engines_template",
    "get_env_templates",
    "get_gitignore_template",
    "get_install_script_template",
    "get_plugin_class_template",
    "get_pyproject_template",
    "get_readme_template",
    "get_test_template",
    "get_tools_template",
]
