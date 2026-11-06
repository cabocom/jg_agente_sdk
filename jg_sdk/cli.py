# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""CLI de scaffolding y utilidades para el SDK de jg_agente.

Proporciona comandos de consola para inicializar nuevos plugins compatibles con
el ecosistema jg_agente de forma estandarizada y determinista.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx


def _to_pascal_case(snake_str: str) -> str:
    """Convierte una cadena en snake_case a PascalCase."""
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", snake_str)
    parts = [p.capitalize() for p in clean.split("_") if p]
    return "".join(parts) or "Plugin"


def _sanitize_name(name: str) -> str:
    """Sanitiza el nombre base del plugin a snake_case válido."""
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", name.strip().lower())
    clean = re.sub(r"_+", "_", clean).strip("_")
    if not clean:
        clean = "custom_plugin"
    return clean


def generate_plugin_scaffold(
    name: str,
    target_dir: Path | None = None,
    template: str = "standard",
    author: str = "Equipo de Desarrollo",
    description: str = "",
    force: bool = False,
) -> Path:
    """Genera la estructura de archivos para un nuevo plugin de jg_agente.

    Args:
        name: Nombre base del plugin (ej. 'network' o 'jg_plugin_network').
        target_dir: Ruta donde se creará el proyecto. Si es None, se usará el nombre del paquete.
        template: Tipo de plantilla ('minimal', 'standard', 'full').
        author: Nombre del autor o entidad desarrolladora.
        description: Descripción breve del plugin.
        force: Si es True, sobrescribe archivos si el directorio ya existe.

    Returns:
        Path al directorio del plugin creado.

    Raises:
        FileExistsError: Si el directorio destino existe y force es False.
        ValueError: Si la plantilla especificada no es válida.
    """
    valid_templates = {"minimal", "standard", "full"}
    if template not in valid_templates:
        raise ValueError(
            f"Plantilla desconocida '{template}'. Opciones válidas: {sorted(valid_templates)}"
        )

    base_name = _sanitize_name(name)
    if base_name.startswith("jg_plugin_"):
        raw_slug = base_name[len("jg_plugin_") :]
        pkg_name = base_name
    else:
        raw_slug = base_name
        pkg_name = f"jg_plugin_{base_name}"

    distribution_name = pkg_name.replace("_", "-")
    class_prefix = _to_pascal_case(raw_slug)
    plugin_class_name = f"{class_prefix}Plugin"
    if not description:
        description = f"Plugin de {raw_slug.replace('_', ' ')} para la plataforma jg_agente."

    out_dir = target_dir if target_dir is not None else Path(pkg_name)
    out_dir = out_dir.resolve()

    if out_dir.exists() and not force and any(out_dir.iterdir()):
        raise FileExistsError(
            f"El directorio de destino '{out_dir}' ya existe y no está vacío. Usa --force para sobrescribir."
        )

    # 1. Definir contenidos de archivos según template
    pyproject_content = f"""[project]
name = "{distribution_name}"
version = "0.1.0"
description = "{description}"
readme = "README.md"
requires-python = ">=3.11"
authors = [{{ name = "{author}" }}]
dependencies = [
    "jg-agente-sdk>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]

[project.entry-points."jg_agente.plugins"]
{raw_slug} = "{pkg_name}.plugin:{plugin_class_name}"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["{pkg_name}*"]
exclude = ["tests*"]

[tool.pytest.ini_options]
minversion = "8.0"
addopts = "-ra -q"
testpaths = ["tests"]
pythonpath = ["."]
asyncio_mode = "auto"
"""

    gitignore_content = """# Entornos virtuales
.venv/
env/
venv/

# Bytecode y caches
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.coverage
htmlcov/

# Distribución y empaquetado
dist/
build/
*.egg-info/
"""

    # Generación de Tools
    if template == "minimal":
        tools_content = f'''"""Definición de herramientas para {pkg_name}."""

from pydantic import BaseModel, Field
from jg_sdk import AgentTool, RiskLevel, ToolResult, ToolType


class QueryArgs(BaseModel):
    query: str = Field(..., description="Término o parámetro de consulta")


def execute_query(query: str) -> ToolResult:
    """Función de ejecución para la herramienta básica."""
    return ToolResult(
        success=True,
        output=f"Consulta procesada exitosamente para: {{query}}",
        metadata={{"query": query}},
    )


query_tool = AgentTool(
    name="{raw_slug}_query",
    description="Ejecuta una consulta básica en el plugin {raw_slug}.",
    category="{raw_slug}",
    args_schema=QueryArgs,
    func=execute_query,
    risk_level=RiskLevel.LOW,
    tool_type=ToolType.READ,
    read_only=True,
)
'''
    elif template == "standard":
        tools_content = f'''"""Definición de herramientas para {pkg_name}."""

from pydantic import BaseModel, Field
from jg_sdk import AgentTool, RiskLevel, ToolResult, ToolType


class InspectArgs(BaseModel):
    target: str = Field(..., description="Elemento o recurso a inspeccionar")


class ActionArgs(BaseModel):
    resource_id: str = Field(..., description="Identificador del recurso a modificar")
    parameters: dict = Field(default_factory=dict, description="Parámetros de la acción")


def execute_inspect(target: str) -> ToolResult:
    """Inspecciona el estado de un recurso."""
    return ToolResult(
        success=True,
        output=f"Inspección completada para {{target}} (estado: normal).",
        metadata={{"target": target, "status": "healthy"}},
    )


def execute_action(resource_id: str, parameters: dict | None = None) -> ToolResult:
    """Ejecuta una acción con soporte de reversibilidad."""
    params = parameters or {{}}
    return ToolResult(
        success=True,
        output=f"Acción aplicada sobre {{resource_id}} con parámetros {{params}}",
        metadata={{"resource_id": resource_id}},
        rollback_context={{"resource_id": resource_id, "previous_state": "active"}},
    )


def rollback_action(rollback_context: dict) -> ToolResult:
    """Función de compensación invocada automáticamente si falla el plan."""
    res_id = rollback_context.get("resource_id", "unknown")
    prev = rollback_context.get("previous_state", "unknown")
    return ToolResult(
        success=True,
        output=f"Compensación ejecutada: {{res_id}} restaurado a {{prev}}.",
    )


inspect_tool = AgentTool(
    name="{raw_slug}_inspect",
    description="Inspecciona el estado actual de un recurso.",
    category="{raw_slug}",
    args_schema=InspectArgs,
    func=execute_inspect,
    risk_level=RiskLevel.LOW,
    tool_type=ToolType.OBSERVER,
    read_only=True,
)

action_tool = AgentTool(
    name="{raw_slug}_action",
    description="Aplica una acción reversible sobre un recurso.",
    category="{raw_slug}",
    args_schema=ActionArgs,
    func=execute_action,
    risk_level=RiskLevel.MEDIUM,
    tool_type=ToolType.MUTATION,
    read_only=False,
    reversible=True,
    rollback_func=rollback_action,
)
'''
    else:  # full
        tools_content = f'''"""Definición de herramientas completas para {pkg_name}."""

from pydantic import BaseModel, Field
from jg_sdk import AgentTool, RiskLevel, ToolResult, ToolType


class TelemetryArgs(BaseModel):
    metric: str = Field(default="system_health", description="Métrica a recolectar")


class ApplyConfigArgs(BaseModel):
    service_id: str = Field(..., description="ID del servicio a configurar")
    config_key: str = Field(..., description="Clave de configuración")
    new_value: str = Field(..., description="Nuevo valor a aplicar")


def execute_telemetry(metric: str = "system_health") -> ToolResult:
    return ToolResult(
        success=True,
        output=f"Telemetría recolectada para {{metric}}.",
        metadata={{"metric": metric, "value": 100}},
    )


def execute_apply_config(service_id: str, config_key: str, new_value: str) -> ToolResult:
    return ToolResult(
        success=True,
        output=f"Configuración {{config_key}}={{new_value}} aplicada a {{service_id}}.",
        metadata={{"service_id": service_id, "key": config_key}},
        rollback_context={{"service_id": service_id, "key": config_key, "old_value": "default"}},
    )


def rollback_apply_config(rollback_context: dict) -> ToolResult:
    svc = rollback_context.get("service_id", "unknown")
    k = rollback_context.get("key", "unknown")
    old = rollback_context.get("old_value", "default")
    return ToolResult(
        success=True,
        output=f"Rollback exitoso: {{svc}} restaurado a {{k}}={{old}}.",
    )


telemetry_tool = AgentTool(
    name="{raw_slug}_telemetry",
    description="Recolecta métricas de observabilidad.",
    category="{raw_slug}",
    args_schema=TelemetryArgs,
    func=execute_telemetry,
    risk_level=RiskLevel.LOW,
    tool_type=ToolType.OBSERVER,
    read_only=True,
)

apply_config_tool = AgentTool(
    name="{raw_slug}_apply_config",
    description="Aplica una mutación de configuración crítica con compensación.",
    category="{raw_slug}",
    args_schema=ApplyConfigArgs,
    func=execute_apply_config,
    risk_level=RiskLevel.HIGH,
    tool_type=ToolType.MUTATION,
    read_only=False,
    reversible=True,
    rollback_func=rollback_apply_config,
)
'''

    # Generación de Engines
    engines_file_content = ""
    if template == "standard":
        engines_file_content = f'''"""Motores cognitivos para {pkg_name}."""

from jg_sdk import ObserverEngine


class {class_prefix}Observer(ObserverEngine):
    """Motor de observación de telemetría e incidentes."""

    @property
    def name(self) -> str:
        return "{raw_slug}_observer"

    async def observe(self, state: dict | None = None) -> dict:
        return {{
            "component": "{raw_slug}",
            "status": "operational",
            "telemetry": {{"uptime": 3600, "healthy": True}},
        }}
'''
    elif template == "full":
        engines_file_content = f'''"""Motores cognitivos avanzados para {pkg_name}."""

from jg_sdk import ObserverEngine, PlannerEngine, VerifierEngine


class {class_prefix}Observer(ObserverEngine):
    """Motor de observación para recolectar telemetría."""

    @property
    def name(self) -> str:
        return "{raw_slug}_observer"

    async def observe(self, state: dict | None = None) -> dict:
        return {{
            "component": "{raw_slug}",
            "status": "operational",
            "incidents": [],
        }}


class {class_prefix}Planner(PlannerEngine):
    """Motor de formulación de planes de ejecución."""

    @property
    def name(self) -> str:
        return "{raw_slug}_planner"

    async def plan(self, intent: str, state: dict | None = None) -> list[dict]:
        return [
            {{
                "step": 1,
                "tool": "{raw_slug}_telemetry",
                "args": {{"metric": "system_health"}},
                "description": "Inspección previa",
            }}
        ]


class {class_prefix}Verifier(VerifierEngine):
    """Motor de verificación activa de resultados."""

    @property
    def name(self) -> str:
        return "{raw_slug}_verifier"

    async def verify(self, state: dict | None = None) -> dict:
        return {{
            "resolved": True,
            "verification_status": "PASS",
            "details": "Estado verificado satisfactoriamente.",
        }}
'''

    # Generación de Plugin Class
    if template == "minimal":
        plugin_file_content = f'''"""Implementación principal del plugin {plugin_class_name}."""

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
        plugin_file_content = f'''"""Implementación principal del plugin {plugin_class_name}."""

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
        plugin_file_content = f'''"""Implementación principal del plugin {plugin_class_name}."""

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

    # Package __init__.py
    init_content = f'''"""Paquete del plugin {pkg_name}."""

from {pkg_name}.plugin import {plugin_class_name}

__all__ = ["{plugin_class_name}"]
'''

    # Tests unitarios con MockPluginRunner
    if template == "minimal":
        test_content = f'''"""Pruebas unitarias para {plugin_class_name}."""

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
        test_content = f'''"""Pruebas unitarias para {plugin_class_name}."""

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
        test_content = f'''"""Pruebas unitarias para {plugin_class_name}."""

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

    # 2. Calcular ruta relativa hacia el SDK local
    sdk_root = Path(__file__).resolve().parent.parent
    try:
        rel_sdk_path = os.path.relpath(sdk_root, out_dir)
    except ValueError:
        rel_sdk_path = str(sdk_root)

    install_script_content = f"""#!/usr/bin/env bash
set -e

PLUGIN_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
cd "$PLUGIN_DIR"

echo "=========================================================="
echo "🚀 Configurando entorno de desarrollo para {distribution_name}"
echo "=========================================================="

# 1. Crear entorno virtual si no existe
if [ ! -d ".venv" ]; then
    echo "📦 Creando entorno virtual en .venv..."
    python3 -m venv .venv
else
    echo "ℹ️  Entorno virtual .venv ya existente."
fi

VENV_PIP="$PLUGIN_DIR/.venv/bin/pip"

# 2. Instalar o enlazar jg-agente-sdk
SDK_LOCAL_PATH="{rel_sdk_path}"
if [ -d "$SDK_LOCAL_PATH" ] && [ -f "$SDK_LOCAL_PATH/pyproject.toml" ]; then
    echo "🔗 Vinculando jg-agente-sdk desde repositorio local ($SDK_LOCAL_PATH)..."
    "$VENV_PIP" install -e "$SDK_LOCAL_PATH"
else
    echo "🌐 Instalando jg-agente-sdk desde índice de paquetes..."
    "$VENV_PIP" install "jg-agente-sdk>=1.0.0"
fi

# 3. Instalar dependencias de desarrollo y el plugin en modo editable
echo "📥 Instalando {distribution_name} en modo editable..."
"$VENV_PIP" install -e ".[dev]"

echo ""
echo "=========================================================="
echo "✅ Instalación completada con éxito."
echo ""
echo "Para comenzar a trabajar, activa el entorno virtual:"
echo "   source .venv/bin/activate"
echo ""
echo "Para ejecutar la suite de pruebas:"
echo "   pytest tests/"
echo "=========================================================="
"""

    readme_content = f"""# {pkg_name}

{description}

Plugin desarrollado para el runtime de agentes autónomos **`jg_agente`** utilizando **`jg-agente-sdk`**.

---

## 1. Instalación Rápida con `install.sh`

El plugin incluye un script automatizado que crea el entorno virtual `.venv`, vincula la copia local del SDK (`jg-agente-sdk`) e instala las dependencias:

```bash
./install.sh
source .venv/bin/activate
```

## 2. Instalación Manual

Si prefieres realizar los pasos manualmente:

```bash
python3 -m venv .venv
source .venv/bin/activate

# 1. Instalar jg-agente-sdk (repositorio local o PyPI)
pip install -e {rel_sdk_path}

# 2. Instalar el plugin en modo editable
pip install -e ".[dev]"
```

## 3. Ejecución de Pruebas

El proyecto cuenta con tests automatizados utilizando el arnés `MockPluginRunner`:

```bash
pytest tests/
```

## 4. Integración en `jg_agente`

Una vez instalado en el mismo entorno de Python que `jg_agente`, el runtime detectará automáticamente el entry-point `{raw_slug}` declarado en `pyproject.toml`.

Para activarlo en el contenedor o proceso del agente, añade el nombre del plugin a la variable de entorno:

```bash
ENABLED_PLUGINS={pkg_name}
```

## 5. Entorno Autónomo Docker Compose y Migraciones
El plugin incluye una suite Docker Compose completa (`docker-compose.yml`) para pruebas locales:
- **Control Plane:** Panel Web HITL en `http://localhost:8880/admin` (`admin@local.test` / `admin123456`).
- **Execution Plane:** Runtime `jg_agente` con tu plugin en `http://localhost:8881`.
- **Script de Arranque (`docker/entrypoint.sh`):** Al levantar el stack, el agente ejecuta automáticamente `alembic upgrade head` para garantizar la creación y consistencia de las tablas troncales (`core_executions`, `core_audit_records`) en PostgreSQL antes de inicializar el servidor FastAPI.
- **Configuración de LLM:** Configura tu `GROQ_API_KEY` en el archivo `.env` para habilitar el razonamiento cognitivo.
- **Ciclo de Vida de `jg run`:** Al iniciar el stack, `jg run` realiza una limpieza preventiva en la base de datos del Dashboard de agentes demo huérfanos con ID fijo (`a0000000-0000-0000-0000-000000000002`), asegurando que no existan duplicidades con el nuevo agente del plugin.

Para iniciar el entorno:
```bash
jg run
```
"""

    # 4. Configuración segura de modelo LLM y aviso preventivo de credenciales (SDK-SEC-01 / SDK-SEC-04)
    has_groq_key_in_env = bool(
        os.environ.get("GLOBAL_GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
    )
    detected_llm_model = os.environ.get("LLM_MODEL") or "openai/gpt-oss-120b"

    if has_groq_key_in_env:
        print(
            "⚠️  [Seguridad] Se detectó GROQ_API_KEY en el entorno, pero por seguridad "
            "NO se incluirá en el archivo .env generado para evitar fugas accidentales en Git.",
            flush=True,
        )

    # 5. Generar docker-compose.yml autónomo con Dashboard, Agente y PostgreSQL
    docker_compose_content = f"""# ==============================================================================
# Entorno autónomo y determinista para {pkg_name}
# Incluye Control Plane (Dashboard Laravel), Execution Plane (jg_agente) y PostgreSQL
# ==============================================================================
services:
  # ============================================================================
  # 1. Base de datos PostgreSQL para el Control Plane (Dashboard)
  # ============================================================================
  jg_dashboard_postgres:
    image: postgres:16-alpine
    container_name: jg_dashboard_postgres_{raw_slug}
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${{DB_DATABASE:-jg_dashboard}}
      POSTGRES_USER: ${{DB_USERNAME:-postgres}}
      POSTGRES_PASSWORD: ${{DB_PASSWORD:-postgres}}
    volumes:
      - jg_dashboard_postgres_data:/var/lib/postgresql/data
    # Oculto por defecto en el host para aislamiento de seguridad.
    # Descomente las siguientes líneas si desea conectarse desde un cliente SQL en el host:
    # ports:
    #   - "${{JG_DASHBOARD_DB_PORT:-8882}}:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${{DB_USERNAME:-postgres}} -d ${{DB_DATABASE:-jg_dashboard}}"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - jg_network

  # ============================================================================
  # 2. Panel Web de Control y Gobernanza HITL (Dashboard Laravel)
  # ============================================================================
  jg_dashboard:
    image: registry.gitlab.com/javiergalvez-ia/jg_dashboard:latest
    container_name: jg_dashboard_{raw_slug}
    restart: unless-stopped
    depends_on:
      jg_dashboard_postgres:
        condition: service_healthy
    environment:
      # ADVERTENCIA DE SEGURIDAD (SDK-SEC-02):
      # Los valores por defecto a continuación son ÚNICAMENTE para desarrollo local aislado.
      # Para entornos de producción o staging, configure contraseñas seguras en su archivo .env.
      APP_NAME: "jG Dashboard - {class_prefix}"
      APP_ENV: ${{APP_ENV:-local}}
      APP_KEY: "${{APP_KEY:-base64:u/pQ9k8q3N0vQzW3mY8l4xJ1t5R6w7y8z9a0b1c2d3E=}}"
      APP_DEBUG: ${{APP_DEBUG:-true}}
      APP_URL: ${{APP_URL:-http://localhost:8880}}
      DB_CONNECTION: pgsql
      DB_HOST: jg_dashboard_postgres
      DB_PORT: 5432
      DB_DATABASE: ${{DB_DATABASE:-jg_dashboard}}
      DB_USERNAME: ${{DB_USERNAME:-postgres}}
      DB_PASSWORD: ${{DB_PASSWORD:-postgres}}
      JG_AGENTE_API_URL: http://jg_agente_{raw_slug}:8000
      JG_AGENTE_SECRET: "${{JG_AGENTE_SECRET:-secret_dev_token_12345}}"
      # Variables de compatibilidad interna para versiones anteriores de imagen dashboard
      JG_CONVERSATIONAL_SECRET: "${{JG_AGENTE_SECRET:-secret_dev_token_12345}}"
      JG_DEVOPS_SECRET: "${{JG_AGENTE_SECRET:-secret_dev_token_12345}}"
      ADMIN_EMAIL: ${{ADMIN_EMAIL:-admin@local.test}}
      ADMIN_DEFAULT_PASSWORD: "${{ADMIN_DEFAULT_PASSWORD:-admin123456}}"
      RUN_MIGRATIONS: ${{RUN_MIGRATIONS:-true}}
    ports:
      - "${{DASHBOARD_PORT:-8880}}:8080"
    networks:
      - jg_network

  # ============================================================================
  # 3. Base de datos PostgreSQL para el Agente Cognitivo (Checkpointer / State)
  # ============================================================================
  jg_agente_postgres:
    image: postgres:16-alpine
    container_name: jg_agente_postgres_{raw_slug}
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${{JG_AGENTE_POSTGRES_DB:-jg_agente}}
      POSTGRES_USER: ${{JG_AGENTE_POSTGRES_USER:-postgres}}
      POSTGRES_PASSWORD: ${{JG_AGENTE_POSTGRES_PASSWORD:-postgres}}
    volumes:
      - jg_agente_postgres_data:/var/lib/postgresql/data
    # Oculto por defecto en el host para aislamiento de seguridad.
    # Descomente las siguientes líneas si desea conectarse desde un cliente SQL en el host:
    # ports:
    #   - "${{JG_AGENTE_POSTGRES_PORT:-8883}}:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${{JG_AGENTE_POSTGRES_USER:-postgres}} -d ${{JG_AGENTE_POSTGRES_DB:-jg_agente}}"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - jg_network

  # ============================================================================
  # 4. Agente Cognitivo con plugin {pkg_name} montado
  # ============================================================================
  jg_agente_{raw_slug}:
    image: registry.gitlab.com/javiergalvez-ia/jg_agente:latest
    container_name: jg_agente_{raw_slug}
    restart: unless-stopped
    depends_on:
      jg_agente_postgres:
        condition: service_healthy
    entrypoint: ["/app/docker-entrypoint.sh"]
    environment:
      ENV: ${{ENV:-development}}
      AGENT_ID: ${{AGENT_ID:-a0000000-0000-0000-0000-000000000001}}
      AGENT_NAME: "{class_prefix} Agent"
      PERMANENT_AGENT_SECRET: "${{JG_AGENTE_SECRET:-secret_dev_token_12345}}"
      AGENT_PORT: 8000
      AGENT_API_URL: http://jg_agente_{raw_slug}:8000
      POSTGRES_HOST: jg_agente_postgres
      POSTGRES_PORT: 5432
      POSTGRES_USER: ${{JG_AGENTE_POSTGRES_USER:-postgres}}
      POSTGRES_PASSWORD: ${{JG_AGENTE_POSTGRES_PASSWORD:-postgres}}
      POSTGRES_DB: ${{JG_AGENTE_POSTGRES_DB:-jg_agente}}
      DATABASE_URL: postgresql+asyncpg://${{JG_AGENTE_POSTGRES_USER:-postgres}}:${{JG_AGENTE_POSTGRES_PASSWORD:-postgres}}@jg_agente_postgres:5432/${{JG_AGENTE_POSTGRES_DB:-jg_agente}}
      DASHBOARD_URL: ${{DASHBOARD_URL:-http://jg_dashboard:8080}}
      VERIFY_CREDENTIALS_ON_BOOT: "false"
      ENABLE_HEARTBEAT: "true"
      LLM_PROVIDER: ${{LLM_PROVIDER:-groq}}
      LLM_MODEL: ${{LLM_MODEL:-{detected_llm_model}}}
      LLM_API_KEY: ${{GLOBAL_GROQ_API_KEY:-${{GROQ_API_KEY:-}}}}
      GROQ_API_KEY: ${{GLOBAL_GROQ_API_KEY:-${{GROQ_API_KEY:-}}}}
      PLUGINS_DIR: plugins
      ENABLED_PLUGINS: {raw_slug},{pkg_name}
    volumes:
      - ./{pkg_name}:/app/plugins/{pkg_name}:ro
      - ./docker/entrypoint.sh:/app/docker-entrypoint.sh:ro
    ports:
      - "127.0.0.1:${{AGENT_PORT:-8881}}:8000"
    networks:
      - jg_network

networks:
  jg_network:
    driver: bridge

volumes:
  jg_dashboard_postgres_data:
  jg_agente_postgres_data:
"""

    # 6. Generar script de arranque limpio para el contenedor del agente (docker/entrypoint.sh)
    # Reemplaza el comando inline 'sh -c alembic upgrade head && ...' por un entrypoint profesional
    docker_entrypoint_content = f"""#!/bin/sh
set -e

# ==============================================================================
# Entrypoint de arranque determinista para jg_agente ({pkg_name})
# ==============================================================================
# ¿Qué hace este script?
# 1. Ejecución de Migraciones Troncales (Alembic):
#    Aplica 'alembic upgrade head' contra la base de datos PostgreSQL del agente.
#    Esto crea y sincroniza las tablas troncales requeridas por el Core:
#      - core_executions: Persistencia de estado del grafo y ejecuciones HITL.
#      - core_audit_records: Registro inmutable de auditoría y decisiones humanas.
#    Evita errores 'relation core_executions does not exist' al recibir peticiones.
#
# 2. Inicialización del Servidor Web (Uvicorn):
#    Lanza FastAPI con el número de workers configurados escuchando en AGENT_PORT.
# ==============================================================================

echo "🔄 [jg_agente] Aplicando migraciones de base de datos troncales (alembic upgrade head)..."
alembic upgrade head

echo "🚀 [jg_agente] Migraciones aplicadas con éxito. Iniciando Execution Plane en puerto ${{AGENT_PORT:-8000}}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${{AGENT_PORT:-8000}}" --workers "${{UVICORN_WORKERS:-2}}"
"""

    env_example_content = f"""# Configuración del entorno de desarrollo para el plugin
ENV=development
GROQ_API_KEY=
LLM_PROVIDER=groq
LLM_MODEL={detected_llm_model}
JG_AGENTE_SECRET=secret_dev_token_12345
ADMIN_EMAIL=admin@local.test
ADMIN_DEFAULT_PASSWORD=admin123456
"""

    env_content = f"""# Variables de entorno locales generadas para {pkg_name}
# NOTA DE SEGURIDAD: Configura tu clave de API antes de iniciar el agente. Nunca la expongas en Git.
ENV=development
GROQ_API_KEY=
GLOBAL_GROQ_API_KEY=
LLM_PROVIDER=groq
LLM_MODEL={detected_llm_model}
JG_AGENTE_SECRET=secret_dev_token_12345
ADMIN_EMAIL=admin@local.test
ADMIN_DEFAULT_PASSWORD=admin123456
"""

    # 3. Creación de directorios y escritura de archivos
    pkg_dir = out_dir / pkg_name
    tests_dir = out_dir / "tests"
    docker_dir = out_dir / "docker"

    pkg_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)
    docker_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")
    (out_dir / ".gitignore").write_text(gitignore_content, encoding="utf-8")
    (out_dir / "README.md").write_text(readme_content, encoding="utf-8")
    (out_dir / "docker-compose.yml").write_text(docker_compose_content, encoding="utf-8")
    (out_dir / ".env.example").write_text(env_example_content, encoding="utf-8")
    (out_dir / ".env").write_text(env_content, encoding="utf-8")

    # Script docker/entrypoint.sh ejecutable
    agent_entrypoint_file = docker_dir / "entrypoint.sh"
    agent_entrypoint_file.write_text(docker_entrypoint_content, encoding="utf-8")
    agent_entrypoint_file.chmod(agent_entrypoint_file.stat().st_mode | 0o755)

    install_file = out_dir / "install.sh"
    install_file.write_text(install_script_content, encoding="utf-8")
    install_file.chmod(install_file.stat().st_mode | 0o755)

    # Añadir exportación PLUGIN_CLASS para autodescubrimiento local en jg_agente
    plugin_file_content_with_class = (
        plugin_file_content.rstrip()
        + f"\n\n\n# Exportación canónica para autodescubrimiento en PLUGINS_DIR\nPLUGIN_CLASS = {plugin_class_name}\n"
    )

    (pkg_dir / "__init__.py").write_text(init_content, encoding="utf-8")
    (pkg_dir / "plugin.py").write_text(plugin_file_content_with_class, encoding="utf-8")
    (pkg_dir / "tools.py").write_text(tools_content, encoding="utf-8")

    if engines_file_content:
        (pkg_dir / "engines.py").write_text(engines_file_content, encoding="utf-8")

    (tests_dir / "__init__.py").write_text("", encoding="utf-8")
    (tests_dir / "test_plugin.py").write_text(test_content, encoding="utf-8")

    return out_dir


def _detect_plugin_info(start_path: Path | None = None) -> tuple[bool, Path | None, str, str]:
    """Detecta si una ruta corresponde a un plugin del ecosistema jg_agente.

    Retorna:
        tuple[is_plugin, plugin_root, plugin_name, raw_slug]
    """
    curr = (start_path or Path.cwd()).resolve()
    candidates = [curr, *curr.parents]

    for candidate in candidates:
        if candidate.name in (
            "jg_agente_sdk",
            "jg_agente",
            "jg_hub",
            "jg_dashboard",
            "jg_filmmaker",
        ):
            continue

        is_plugin = False
        pkg_name = ""

        # 1. Por convención de nombre de directorio
        if candidate.name.startswith("jg_plugin_"):
            is_plugin = True
            pkg_name = candidate.name

        # 2. Por pyproject.toml con entrypoint de plugins o nombre del paquete
        pyproject = candidate / "pyproject.toml"
        if pyproject.is_file():
            try:
                content = pyproject.read_text(encoding="utf-8", errors="ignore")
                for line in content.splitlines():
                    cleaned_line = line.strip()
                    if cleaned_line.startswith(
                        '[project.entry-points."jg_agente.plugins"]'
                    ) or cleaned_line.startswith("[project.entry-points.'jg_agente.plugins']"):
                        is_plugin = True
                    if (
                        cleaned_line.startswith("name =") or cleaned_line.startswith("name=")
                    ) and not pkg_name:
                        val = cleaned_line.split("=")[1].strip().strip('"').strip("'")
                        if val.startswith("jg-plugin-") or val.startswith("jg_plugin_"):
                            is_plugin = True
                            pkg_name = val.replace("-", "_")
            except Exception:
                pass

        # 3. Por presencia de plugin.py en subcarpeta
        if not is_plugin and candidate.is_dir():
            try:
                for child in candidate.iterdir():
                    if child.is_dir() and (child / "plugin.py").is_file():
                        is_plugin = True
                        if not pkg_name:
                            pkg_name = child.name
                        break
            except Exception:
                pass

        if is_plugin:
            if not pkg_name:
                pkg_name = candidate.name
            pkg_name = _sanitize_name(pkg_name)
            if (
                not pkg_name.startswith("jg_plugin_")
                and (candidate / f"jg_plugin_{pkg_name}").exists()
            ):
                pkg_name = f"jg_plugin_{pkg_name}"
            raw_slug = (
                pkg_name[len("jg_plugin_") :] if pkg_name.startswith("jg_plugin_") else pkg_name
            )
            return True, candidate, pkg_name, raw_slug

    return False, None, "", ""


def _find_matching_containers(raw_slug: str, plugin_name: str) -> list[str]:
    """Busca contenedores Docker asociados determinísticamente a un plugin o agente."""
    try:
        res = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            return []
        matched: list[str] = []
        for line in res.stdout.strip().splitlines():
            name = line.strip()
            if not name:
                continue
            if (
                name == f"jg_agente_{raw_slug}"
                or name == f"jg_dashboard_{raw_slug}"
                or name == f"jg_agente_postgres_{raw_slug}"
                or name == f"jg_dashboard_postgres_{raw_slug}"
                or name.endswith(f"_{raw_slug}")
                or name == plugin_name
                or name == f"jg_{raw_slug}"
            ) and name not in matched:
                matched.append(name)
        return matched
    except Exception:
        return []


def _find_plugin_root() -> Path:
    """Busca la raíz del plugin buscando pyproject.toml o install.sh desde el directorio actual hacia arriba."""
    is_p, root_p, _, _ = _detect_plugin_info(Path.cwd())
    if is_p and root_p is not None:
        return root_p
    curr = Path.cwd().resolve()
    for parent in [curr, *curr.parents]:
        if (parent / "pyproject.toml").is_file() or (parent / "install.sh").is_file():
            return parent
    return curr


def handle_install() -> int:
    """Instala las dependencias del plugin y aprovisiona el entorno virtual (.venv)."""
    plugin_root = _find_plugin_root()
    install_script = plugin_root / "install.sh"
    if install_script.exists():
        print(f"🚀 Ejecutando aprovisionamiento con {install_script.name}...")
        res = subprocess.run(["bash", str(install_script)], cwd=plugin_root)
        if res.returncode == 0:
            print("\n✨ Dependencias del plugin instaladas con éxito.")
        return res.returncode

    venv_dir = plugin_root / ".venv"
    print(f"⚙️ Creando entorno virtual .venv en {venv_dir}...")
    res_venv = subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], cwd=plugin_root)
    if res_venv.returncode != 0:
        print("❌ Falló la creación de .venv", file=sys.stderr)
        return res_venv.returncode
    pip_bin = venv_dir / "bin" / "pip"
    res_pip = subprocess.run([str(pip_bin), "install", "-e", "."], cwd=plugin_root)
    if res_pip.returncode == 0:
        print("\n✨ Dependencias del plugin instaladas con éxito.")
    return res_pip.returncode


def handle_dev(command: list[str] | None = None) -> int:
    """Habilita el entorno virtual (.venv) o ejecuta un comando arbitrario dentro de él.

    Nota de diseño (SDK-CLI-01): Si se proporciona `command`, se ejecuta directamente
    dentro del entorno del plugin (ej. `pytest`, `ruff check .`) sin filtrado adicional.
    """
    plugin_root = _find_plugin_root()
    venv_dir = plugin_root / ".venv"
    venv_python = venv_dir / "bin" / "python"

    if not venv_python.exists():
        print(f"📦 Entorno virtual no encontrado en: {venv_dir}")
        install_script = plugin_root / "install.sh"
        if install_script.exists():
            print(f"🚀 Ejecutando script de instalación {install_script.name}...")
            res = subprocess.run(["bash", str(install_script)], cwd=plugin_root)
            if res.returncode != 0:
                print("❌ Falló la preparación del entorno con install.sh", file=sys.stderr)
                return res.returncode
        else:
            print("⚙️ Creando entorno virtual .venv...")
            res_venv = subprocess.run(
                [sys.executable, "-m", "venv", str(venv_dir)], cwd=plugin_root
            )
            if res_venv.returncode != 0:
                print("❌ Falló la creación de .venv", file=sys.stderr)
                return res_venv.returncode
            pip_bin = venv_dir / "bin" / "pip"
            subprocess.run([str(pip_bin), "install", "-e", "."], cwd=plugin_root)

    new_env = os.environ.copy()
    new_env["VIRTUAL_ENV"] = str(venv_dir)
    new_env["PATH"] = f"{venv_dir / 'bin'}:{new_env.get('PATH', '')}"
    new_env.pop("PYTHONHOME", None)

    # Si se pasaron comandos específicos a ejecutar: e.g. jg-sdk dev pytest
    if command:
        cmd = list(command)
        bin_candidate = venv_dir / "bin" / cmd[0]
        if bin_candidate.exists():
            cmd[0] = str(bin_candidate)
        res = subprocess.run(cmd, env=new_env, cwd=plugin_root)
        return res.returncode

    # Modo interactivo: spawn de subshell enriquecido
    shell = os.environ.get("SHELL", "/bin/bash")
    print("=" * 65)
    print("🚀 Entorno de desarrollo interactivo activado (.venv)")
    print(f"📁 Directorio raíz:  {plugin_root}")
    print(f"🐍 Python binario:   {venv_python}")
    print("🛠️  Herramientas:     pytest, ruff, jg-sdk")
    print("💡 Escribe 'exit' para salir del entorno virtual.")
    print("=" * 65)

    try:
        res = subprocess.run([shell], env=new_env, cwd=plugin_root)
        print("\n👋 Saliste del entorno de desarrollo.")
        return res.returncode
    except Exception as exc:
        print(f"❌ Error al iniciar subshell: {exc}", file=sys.stderr)
        return 1


def handle_run(args: argparse.Namespace) -> int:
    """Lanza o gestiona el entorno Docker Compose autónomo del plugin."""
    plugin_root = _find_plugin_root()
    compose_file: Path | None = None
    for candidate in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]:
        p = plugin_root / candidate
        if p.exists():
            compose_file = p
            break

    if not compose_file:
        print(
            f"❌ No se encontró 'docker-compose.yml' en {plugin_root}.\n"
            "Asegúrate de ejecutar 'jg run' dentro del directorio de tu plugin.",
            file=sys.stderr,
        )
        return 1

    if getattr(args, "down", False):
        print("🛑 Deteniendo entorno Docker Compose...")
        return subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "down"], cwd=plugin_root
        ).returncode

    if getattr(args, "logs", False):
        return subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "logs", "-f"], cwd=plugin_root
        ).returncode

    if getattr(args, "status", False):
        return subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "ps"], cwd=plugin_root
        ).returncode

    cmd = ["docker", "compose", "-f", str(compose_file), "up", "-d"]
    if getattr(args, "build", False):
        cmd.append("--build")

    env = os.environ.copy()
    agent_port = getattr(args, "agent_port", None) or getattr(args, "port", None)
    if agent_port is not None:
        env["AGENT_PORT"] = str(agent_port)
    dashboard_port = getattr(args, "dashboard_port", None)
    if dashboard_port is not None:
        env["DASHBOARD_PORT"] = str(dashboard_port)
    host = getattr(args, "host", None)
    if host is not None:
        env["HOST"] = str(host)

    effective_agent_port = env.get("AGENT_PORT", "8881")
    effective_dashboard_port = env.get("DASHBOARD_PORT", "8880")

    print(f"🐳 Iniciando stack Docker Compose autónomo ({compose_file.name})...")
    print(
        "⚠️  Stack iniciado con credenciales de DESARROLLO. "
        "Configura el .env antes de desplegar en producción."
    )
    res = subprocess.run(cmd, cwd=plugin_root, env=env)
    if res.returncode != 0:
        return res.returncode

    # Limpieza de agentes demo huérfanos en el Dashboard (SDK-SEC-03):
    # Al iniciar el stack, se ejecuta una operación determinista y estática (sin input de usuario)
    # mediante 'artisan tinker' para eliminar el agente demo legacy con ID fijo
    # ('a0000000-0000-0000-0000-000000000002') proveniente de versiones iniciales de la imagen
    # base del Dashboard. Esto previene entradas duplicadas o conflictos con el agente actual.
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(compose_file),
            "exec",
            "-T",
            "jg_dashboard",
            "php",
            "artisan",
            "tinker",
            "--execute=\\App\\Models\\Agent::where('agent_id', 'a0000000-0000-0000-0000-000000000002')->delete();",
        ],
        cwd=plugin_root,
        capture_output=True,
    )

    # Mostrar puertos y servicios configurados
    print("\n" + "=" * 65)
    print("✨ Stack autónomo de jg_agente iniciado correctamente")
    print("=" * 65)
    print("⚠️  AVISO DE SEGURIDAD (SDK-SEC-02):")
    print("   Stack iniciado con credenciales de DESARROLLO por defecto.")
    print("   Configura el .env antes de desplegar en producción.")
    print("=" * 65)
    print("📍 Puntos de acceso disponibles:")
    print(f"   🌐 Dashboard Web HITL:      http://localhost:{effective_dashboard_port}/admin")
    print(f"   🤖 Agente API REST:         http://localhost:{effective_agent_port}")
    print(f"   🔍 Capacidades Plugins:     http://localhost:{effective_agent_port}/capabilities")
    print(f"   🩺 Comprobación de Salud:   http://localhost:{effective_agent_port}/health")
    print("   🗄️ PostgreSQL Dashboard:   Interno (red privada Docker, host 8882 desactivado)")
    print("   🗄️ PostgreSQL Agente:      Interno (red privada Docker, host 8883 desactivado)")
    print("\n🔐 Credenciales de acceso al Dashboard (SOLO DESARROLLO LOCAL):")
    print("   • URL:                      http://localhost:8880/admin")
    print("   • Usuario:                  admin@local.test")
    print("   • Contraseña:               admin123456 (insegura por defecto)")
    print("\n💡 Comandos de gestión rápida:")
    print("   • Ver logs en tiempo real:  jg run -l")
    print("   • Ver estado de servicios:  jg run -s")
    print("   • Detener el entorno:       jg run --down")
    print("=" * 65)
    return 0


def handle_build(args: argparse.Namespace) -> int:
    """Construye y empaqueta la imagen Docker del plugin basada en jg_agente."""
    raw_path = getattr(args, "path", None)
    plugin_root = Path(raw_path).resolve() if raw_path else Path.cwd()

    # 1. Determinar el nombre del plugin
    plugin_name = None
    pyproject_file = plugin_root / "pyproject.toml"
    if pyproject_file.exists():
        with contextlib.suppress(Exception):
            content = pyproject_file.read_text(encoding="utf-8")
            for line in content.splitlines():
                if line.strip().startswith("name =") or line.strip().startswith("name="):
                    plugin_name = line.split("=")[1].strip().strip('"').strip("'")
                    break

    if not plugin_name:
        for p in plugin_root.glob("*/plugin.py"):
            plugin_name = p.parent.name
            break
        if not plugin_name:
            plugin_name = plugin_root.name

    if plugin_name:
        plugin_name = _sanitize_name(plugin_name)

    if (
        not plugin_name.startswith("jg_plugin_")
        and (plugin_root / f"jg_plugin_{plugin_name}").exists()
    ):
        plugin_name = f"jg_plugin_{plugin_name}"

    base_image = getattr(args, "base_image", "registry.gitlab.com/javiergalvez-ia/jg_agente:latest")
    raw_tag = getattr(args, "tag", None)

    if not raw_tag:
        ci_registry_image = os.environ.get("CI_REGISTRY_IMAGE")
        ci_commit_slug = os.environ.get("CI_COMMIT_REF_SLUG", "latest")
        if ci_registry_image:
            raw_tag = f"{ci_registry_image}:{ci_commit_slug}"
        else:
            raw_tag = f"registry.gitlab.com/javiergalvez-ia/{plugin_name}:{ci_commit_slug}"

    print("=" * 65)
    print(f"📦 Construyendo imagen Docker para plugin '{plugin_name}'...")
    print(f"   • Imagen Base:   {base_image}")
    print(f"   • Tag Destino:   {raw_tag}")
    print(f"   • Directorio:    {plugin_root}")
    print("=" * 65)

    dockerfile_path = plugin_root / "Dockerfile"
    temp_dockerfile = False

    if not dockerfile_path.exists():
        pkg_dir = plugin_name
        if not (plugin_root / pkg_dir).exists():
            for sub in plugin_root.iterdir():
                if sub.is_dir() and (sub / "plugin.py").exists():
                    pkg_dir = sub.name
                    break

        dockerfile_content = f"""FROM {base_image}

USER root

# Inyectar el plugin dentro del directorio /app/plugins del agente
COPY {pkg_dir} /app/plugins/{plugin_name}
COPY pyproject.toml* /app/plugins/{plugin_name}/
RUN if [ -f /app/plugins/{plugin_name}/pyproject.toml ]; then pip install --no-cache-dir /app/plugins/{plugin_name}; fi
RUN chown -R appuser:appgroup /app/plugins/{plugin_name}

USER appuser
"""
        dockerfile_path = plugin_root / ".Dockerfile.tmp"
        dockerfile_path.write_text(dockerfile_content, encoding="utf-8")
        temp_dockerfile = True

    try:
        cmd_build = ["docker", "build", "-t", raw_tag, "-f", str(dockerfile_path), str(plugin_root)]
        print(f"▶ Ejecutando: {' '.join(cmd_build)}")
        res = subprocess.run(cmd_build, cwd=plugin_root)
        if res.returncode != 0:
            print(
                f"❌ Error al construir la imagen Docker (código {res.returncode}).",
                file=sys.stderr,
            )
            return res.returncode

        print(f"✓ Imagen construida con éxito: {raw_tag}")

        should_push = getattr(args, "push", False)
        if should_push:
            print(f"🚀 Publicando imagen en registro remoto: {raw_tag}...")
            res_push = subprocess.run(["docker", "push", raw_tag], cwd=plugin_root)
            if res_push.returncode != 0:
                print(
                    f"❌ Error al publicar la imagen en el registro (código {res_push.returncode}).",
                    file=sys.stderr,
                )
                return res_push.returncode

            ci_branch = os.environ.get("CI_COMMIT_BRANCH")
            ci_default = os.environ.get("CI_DEFAULT_BRANCH", "main")
            if (
                ci_branch
                and (ci_branch == ci_default or ci_branch == "main")
                and not raw_tag.endswith(":latest")
            ):
                base_name = raw_tag.split(":")[0]
                latest_tag = f"{base_name}:latest"
                print(f"🏷️ Etiquetando y publicando también como {latest_tag}...")
                subprocess.run(["docker", "tag", raw_tag, latest_tag], cwd=plugin_root, check=True)
                subprocess.run(["docker", "push", latest_tag], cwd=plugin_root)

    finally:
        if temp_dockerfile and dockerfile_path.exists():
            dockerfile_path.unlink()

    print("=" * 65)
    print(f"🎉 ¡Empaquetado Docker de '{plugin_name}' completado con éxito!")
    print("=" * 65)
    return 0


def handle_test(args: argparse.Namespace) -> int:
    """Ejecuta la suite de pruebas del plugin usando pytest dentro del entorno virtual."""
    pytest_args = getattr(args, "pytest_args", [])
    if pytest_args and pytest_args[0] == "--":
        pytest_args = pytest_args[1:]
    cmd = ["pytest"] + pytest_args
    return handle_dev(cmd)


def handle_reload(args: argparse.Namespace) -> int:
    """Recarga de forma inmediata los plugins de los agentes en ejecución."""
    target = getattr(args, "target", "all") or "all"
    target = target.lower()

    agents_map = [
        ("conversacional", "jg_agente_conversacional", 8001, "Agente Conversacional"),
        ("devops", "jg_agente_devops", 8002, "Agente DevOps"),
        ("datosgob", "jg_agente_datosgob", 8881, "Agente Datos Gob"),
    ]

    print("=" * 65)
    print("🔌 Recargando plugins de agentes cognitivos...")
    print("=" * 65)

    reloaded_any = False
    for a_key, a_container, a_port, a_name in agents_map:
        if target not in ("all", a_key):
            continue

        reloaded_any = True
        print(f"\n▶ [{a_name}] ({a_container})")

        # Verificar si el contenedor está corriendo
        res = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
        )
        if a_container not in res.stdout.splitlines():
            print(f"   ⚠️  Contenedor '{a_container}' no está en ejecución. Omitiendo.")
            continue

        print("   🔄 Reiniciando runtime...")
        restart_res = subprocess.run(["docker", "restart", a_container], capture_output=True)
        if restart_res.returncode != 0:
            print(f"   ❌ Error al reiniciar contenedor '{a_container}'.")
            continue

        print(f"   ⏳ Verificando salud en http://localhost:{a_port}/health...")
        healthy = False
        start_t = time.time()
        for _ in range(25):
            try:
                r = httpx.get(f"http://localhost:{a_port}/health", timeout=2.0)
                if r.status_code == 200:
                    healthy = True
                    break
            except Exception:
                pass
            time.sleep(1)

        elapsed = round(time.time() - start_t, 1)
        if not healthy:
            print("   ❌ El agente no respondió saludable tras 25s.")
            continue

        print(f"   ✓ Agente saludable y operativo ({elapsed}s)")

        try:
            r = httpx.get(f"http://localhost:{a_port}/capabilities", timeout=3.0)
            if r.status_code == 200:
                data = r.json()
                plugins = [
                    p.get("name", "") + " (v" + p.get("version", "?") + ")"
                    for p in data.get("plugins", [])
                ]
                tools = [
                    t.get("name", "") + " [" + t.get("risk_level", "low") + "]"
                    for t in data.get("tools", [])
                ]
                engines = [e.get("name", "") for e in data.get("engines", [])]

                print(
                    f"   📦 Plugins activos  ({data.get('plugins_count', 0)}): {', '.join(plugins) if plugins else 'Ninguno'}"
                )
                print(
                    f"   🛠️  Herramientas    ({data.get('tools_count', 0)}): {', '.join(tools) if tools else 'Ninguna'}"
                )
                if engines:
                    print(
                        f"   🧠 Motores Cognit. ({data.get('engines_count', 0)}): {', '.join(engines)}"
                    )
        except Exception:
            pass

        print("   ✨ Plugins sincronizados con éxito.")

    if not reloaded_any:
        print(
            f"❌ Objetivo desconocido: '{target}'. Opciones válidas: all, conversacional, devops, datosgob"
        )
        return 1

    print("\n" + "=" * 65)
    print("🎉 Recarga de plugins completada satisfactoriamente")
    print("=" * 65)
    return 0


def _handle_plugin_status(
    plugin_root: Path,
    plugin_name: str,
    raw_slug: str,
    args: argparse.Namespace,
) -> int:
    """Muestra el estado detallado de un plugin específico."""
    print("=" * 65)
    print(f"🔌 Estado del Plugin: {plugin_name} ({raw_slug})")
    print(f"📁 Directorio: {plugin_root}")
    print("=" * 65)

    # 1. Modo arquitectónico
    has_compose = any(
        (plugin_root / f).is_file()
        for f in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]
    )
    if has_compose:
        print("  🏗️  Modo Arquitectónico:   Autónomo (docker-compose.yml propio)")
    else:
        print("  🏗️  Modo Arquitectónico:   Compartido / Integrado (montaje en runtime jg_agente)")

    # 2. Enlace simbólico en jg_agente
    target_plugins = resolve_target_plugins_dir(getattr(args, "target", None))
    symlink_found: tuple[Path, str] | None = None
    for cand in [plugin_name, raw_slug, f"jg_plugin_{raw_slug}"]:
        p = target_plugins / cand
        if p.is_symlink():
            try:
                symlink_found = (p, str(p.readlink()))
            except Exception:
                symlink_found = (p, str(p.resolve()))
            break

    if symlink_found:
        print(f"  🔗 Enlace en jg_agente:    ACTIVO -> {symlink_found[0]} ({symlink_found[1]})")
    else:
        print(f"  ⚪ Enlace en jg_agente:    No vinculado en {target_plugins.name}/")

    # 3. Contenedores Docker asociados
    containers = _find_matching_containers(raw_slug, plugin_name)
    running_containers: list[str] = []
    if containers:
        print(f"  🐳 Contenedores Docker asociados ({len(containers)}):")
        res_ps = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"],
            capture_output=True,
            text=True,
        )
        c_map: dict[str, tuple[str, str]] = {}
        for line in res_ps.stdout.strip().splitlines():
            parts = line.split("\t")
            if parts:
                c_map[parts[0]] = (
                    parts[1] if len(parts) > 1 else "",
                    parts[2] if len(parts) > 2 else "",
                )

        for c in containers:
            status, ports = c_map.get(c, ("Desconocido", ""))
            ports_display = f" | {ports}" if ports else ""
            if "Up" in status:
                running_containers.append(c)
                print(f"     ✅ {c:<30} {status}{ports_display}")
            else:
                print(f"     ⚪ {c:<30} {status}{ports_display}")
    else:
        print("  ⚪ Contenedores Docker:    Ninguno activo (stack apagado)")

    # 4. Salud HTTP y capacidades del agente
    known_ports = {
        "devops": 8922,
        "conversacional": 8921,
        "sales": 8873,
        "datosgob": 8881,
    }
    candidate_port = known_ports.get(raw_slug, 8881)

    for c in running_containers:
        try:
            res_port = subprocess.run(["docker", "port", c, "8000"], capture_output=True, text=True)
            if res_port.returncode == 0 and res_port.stdout.strip():
                candidate_port = int(res_port.stdout.strip().split(":")[-1])
                break
        except Exception:
            pass

    try:
        r = httpx.get(f"http://localhost:{candidate_port}/health", timeout=1.5)
        if r.status_code == 200:
            print(
                f"  ✅ Runtime API:            ONLINE  (http://localhost:{candidate_port}/health)"
            )
            try:
                cr = httpx.get(f"http://localhost:{candidate_port}/capabilities", timeout=1.5)
                if cr.status_code == 200:
                    cd = cr.json()
                    p_cnt = cd.get("plugins_count", 0)
                    t_cnt = cd.get("tools_count", 0)
                    e_cnt = cd.get("engines_count", 0)
                    print(
                        f"     └─► Capacidades: {p_cnt} plugins | {t_cnt} tools | {e_cnt} engines"
                    )
            except Exception:
                pass
        else:
            print(
                f"  ⚠️  Runtime API:            HTTP {r.status_code} (http://localhost:{candidate_port}/health)"
            )
    except Exception:
        print(f"  ⚪ Runtime API:            OFFLINE (puerto {candidate_port})")

    # 5. Entorno local
    venv_ok = (plugin_root / ".venv").is_dir()
    tests_ok = (plugin_root / "tests").is_dir()
    print(f"  📦 Entorno Virtual (.venv): {'Presente' if venv_ok else 'Ausente'}")
    print(f"  🧪 Suite de Tests:         {'Presente (tests/)' if tests_ok else 'No encontrada'}")

    # 6. Diagnóstico para el desarrollador
    print("-" * 65)
    if not running_containers and not symlink_found:
        print("  🟢 ESTADO LIMPIO: El plugin no tiene contenedores activos ni enlaces.")
        print("     Esta carpeta se puede archivar en Git o borrar con seguridad:")
        print(f"     rm -rf {plugin_root}")
    else:
        print("  🟠 RECURSOS EN USO: Hay contenedores o enlaces activos.")
        print("     Para desmantelarlos antes de borrar la carpeta, ejecuta:")
        print("     jg clean")
    print("=" * 65)
    return 0


def _handle_global_status(args: argparse.Namespace) -> int:
    """Muestra el estado global de todos los servicios del ecosistema."""
    services = [
        ("Portal & Docs (jg_hub)", "http://localhost:8930/up", "web", 8930),
        ("Dashboard (Control Plane)", "http://localhost:8003/up", "web", 8003),
        ("Agente Conversacional", "http://localhost:8921/health", "agent", 8921),
        ("Agente DevOps", "http://localhost:8922/health", "agent", 8922),
        ("Agente Sales", "http://localhost:8873/health", "agent", 8873),
        ("Filmmaker Web", "http://localhost:8010/up", "web", 8010),
        ("Dashboard Autónomo (Plugins)", "http://localhost:8880/up", "web", 8880),
        ("Agente Autónomo (Plugins)", "http://localhost:8881/health", "agent", 8881),
    ]

    print("=" * 65)
    print("🩺 Estado de Servicios y Runtimes (javiergalvez-ia)")
    print("=" * 65)

    for item in services:
        name = item[0]
        url = item[1]
        stype = item[2]
        port = item[3]

        try:
            r = httpx.get(url, timeout=2.0)
            if r.status_code == 200:
                print(f"  ✅ {name:<30} ONLINE  ({url})")
                if stype == "agent":
                    try:
                        cr = httpx.get(f"http://localhost:{port}/capabilities", timeout=2.0)
                        if cr.status_code == 200:
                            cd = cr.json()
                            p_cnt = cd.get("plugins_count", 0)
                            t_cnt = cd.get("tools_count", 0)
                            e_cnt = cd.get("engines_count", 0)
                            print(
                                f"     └─► Plugins: {p_cnt} | Herramientas: {t_cnt} | Motores: {e_cnt}"
                            )
                    except Exception:
                        pass
            else:
                print(f"  ⚠️  {name:<30} HTTP {r.status_code} ({url})")
        except Exception:
            print(f"  ⚪ {name:<30} OFFLINE ({url})")

    print("=" * 65)
    return 0


def handle_status(args: argparse.Namespace) -> int:
    """Inspecciona la salud y capacidades de un plugin específico o del ecosistema completo."""
    is_global = getattr(args, "is_global", False)

    if not is_global:
        is_plugin, plugin_root, plugin_name, raw_slug = _detect_plugin_info(Path.cwd())
        if is_plugin and plugin_root is not None:
            return _handle_plugin_status(plugin_root, plugin_name, raw_slug, args)

    return _handle_global_status(args)


def handle_clean(args: argparse.Namespace) -> int:
    """Detiene y elimina contenedores autónomos o dedicados, desvincula symlinks en agentes y purga cachés."""
    raw_name = getattr(args, "name", None)
    all_flag = getattr(args, "all", False)
    target_dir = getattr(args, "target", None)

    is_plugin, plugin_root, plugin_name, raw_slug = False, None, "", ""

    if raw_name:
        candidate_path = Path(raw_name).resolve()
        if candidate_path.is_dir():
            is_plugin, plugin_root, plugin_name, raw_slug = _detect_plugin_info(candidate_path)
        if not is_plugin:
            for p in [Path.cwd(), *Path.cwd().parents]:
                for candidate in [p / raw_name, p / f"jg_plugin_{raw_name}"]:
                    if candidate.is_dir():
                        is_plugin, plugin_root, plugin_name, raw_slug = _detect_plugin_info(
                            candidate
                        )
                        if is_plugin:
                            break
                if is_plugin:
                    break

        if not is_plugin:
            raw_slug = (
                raw_name[len("jg_plugin_") :] if raw_name.startswith("jg_plugin_") else raw_name
            )
            plugin_name = raw_name if raw_name.startswith("jg_plugin_") else f"jg_plugin_{raw_name}"
            plugin_root = None
            is_plugin = True
    else:
        is_plugin, plugin_root, plugin_name, raw_slug = _detect_plugin_info(Path.cwd())

    if not is_plugin or not plugin_name:
        print(
            "❌ No se detectó ningún plugin en el directorio actual.\n"
            "   Especifica el nombre del plugin (ej. 'jg clean devops') o ejecuta el comando desde su directorio.",
            file=sys.stderr,
        )
        return 1

    print("=" * 65)
    print(f"🧹 Limpieza de Recursos y Enlaces: {plugin_name} ({raw_slug})")
    print("=" * 65)

    # 1. Detener Docker Compose autónomo (si existe compose local)
    if plugin_root and plugin_root.is_dir():
        compose_file = None
        for candidate in [
            "docker-compose.yml",
            "docker-compose.yaml",
            "compose.yml",
            "compose.yaml",
        ]:
            p = plugin_root / candidate
            if p.is_file():
                compose_file = p
                break
        if compose_file:
            print(f"🛑 Deteniendo stack Docker Compose autónomo ({compose_file.name})...")
            cmd_down = ["docker", "compose", "-f", str(compose_file), "down"]
            if all_flag:
                cmd_down.append("--volumes")
            res_down = subprocess.run(cmd_down, cwd=plugin_root, capture_output=True, text=True)
            if res_down.returncode == 0:
                print("   ✅ Stack Docker Compose autónomo detenido y eliminado.")
            else:
                msg = res_down.stderr.strip() or res_down.stdout.strip()
                if msg:
                    print(f"   ℹ️  Docker Compose: {msg}")

    # 2. Detectar y eliminar contenedores Docker asociados en el sistema
    matched_containers = _find_matching_containers(raw_slug, plugin_name)
    if matched_containers:
        print(f"🐳 Contenedores Docker asociados detectados ({len(matched_containers)}):")
        for c in matched_containers:
            print(f"   • Deteniendo y eliminando '{c}'...")
            subprocess.run(["docker", "rm", "-f", c], capture_output=True)
            print(f"     ✓ Contenedor '{c}' eliminado.")
    else:
        print("🐳 Contenedores Docker: Ninguno asociado en ejecución.")

    # 3. Desvincular enlace simbólico en agente (Modo Compartido)
    target_plugins = resolve_target_plugins_dir(target_dir)
    unlinked_any = False
    for candidate_name in [plugin_name, raw_slug, f"jg_plugin_{raw_slug}"]:
        cand_path = target_plugins / candidate_name
        if cand_path.is_symlink():
            try:
                cand_path.unlink()
                print(
                    f"🔗 Enlace simbólico '{candidate_name}' desvinculado con éxito de: {target_plugins}"
                )
                unlinked_any = True
            except Exception as exc:
                print(f"   ⚠️  Fallo al desvincular '{candidate_name}': {exc}")
        elif cand_path.exists() and cand_path.is_dir():
            print(
                f"   ⚠️  '{cand_path}' es un directorio real y no un symlink. No se elimina por seguridad."
            )

    if not unlinked_any:
        print(f"🔗 Enlaces en jg_agente: Ninguno activo en {target_plugins.name}/.")

    # 4. Limpieza de cachés y artefactos locales
    if plugin_root and plugin_root.is_dir():
        for root_walk, dirs, _ in os.walk(plugin_root):
            for d in list(dirs):
                if d in ("__pycache__", ".pytest_cache", ".ruff_cache") or d.endswith(".egg-info"):
                    target_d = Path(root_walk) / d
                    shutil.rmtree(target_d, ignore_errors=True)
        if all_flag:
            venv_path = plugin_root / ".venv"
            if venv_path.is_dir():
                shutil.rmtree(venv_path, ignore_errors=True)
                print("   🧹 Entorno virtual .venv eliminado.")

        print("   🧹 Cachés temporales purgadas (__pycache__, pytest, ruff).")

    print("\n" + "=" * 65)
    print(f"✨ Plugin '{plugin_name}' limpiado con éxito.")
    print("📁 El plugin no tiene procesos activos ni enlaces vinculados en el agente.")
    if plugin_root:
        print("ℹ️  Ahora puedes archivar en Git o eliminar esta carpeta sin riesgo:")
        print(f"   rm -rf {plugin_root}")
    print("=" * 65)
    return 0


def resolve_target_plugins_dir(explicit_target: Path | str | None = None) -> Path:
    """Resuelve la ruta al directorio plugins/ del agente."""
    if explicit_target is not None:
        return Path(explicit_target).resolve()

    cwd = Path.cwd().resolve()
    for parent in [cwd, *cwd.parents]:
        for candidate in [
            parent / "jg_agente" / "plugins",
            parent / "plugins",
        ]:
            if candidate.is_dir():
                return candidate.resolve()

    return (cwd / "plugins").resolve()


def inspect_plugin_metadata(plugin_source_dir: Path | str) -> dict[str, Any]:
    """Inspecciona estáticamente un plugin para extraer metadatos, engines y capacidades."""
    source = Path(plugin_source_dir).resolve()
    if not source.exists():
        return {"error": f"La ruta del plugin no existe: {source}"}

    package_dir: Path | None = None
    package_name: str = ""

    if (source / "plugin.py").is_file():
        package_dir = source
        package_name = source.name
    elif source.is_dir():
        for child in source.iterdir():
            if child.is_dir() and (child / "plugin.py").is_file():
                package_dir = child
                package_name = child.name
                break

    pyproject = source / "pyproject.toml"
    if pyproject.is_file():
        content = pyproject.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
        if match and not package_name:
            pkg_name_from_pyproject = match.group(1).replace("-", "_")
            package_name = pkg_name_from_pyproject
            if (source / pkg_name_from_pyproject).is_dir():
                package_dir = source / pkg_name_from_pyproject

    if package_dir is None:
        return {"error": f"No se encontró un paquete Python válido con 'plugin.py' en: {source}"}

    if not package_name:
        package_name = package_dir.name

    code_texts: list[str] = []
    for py_file in package_dir.glob("*.py"):
        with contextlib.suppress(Exception):
            code_texts.append(py_file.read_text(encoding="utf-8", errors="ignore"))

    combined_code = "\n".join(code_texts)

    engines: list[str] = []
    if "ObserverEngine" in combined_code:
        engines.append("observer_engine")
    if "PlannerEngine" in combined_code:
        engines.append("planner_engine")
    if "VerifierEngine" in combined_code:
        engines.append("verifier_engine")
    if "DiagnosticEngine" in combined_code:
        engines.append("diagnostic_engine")

    is_privileged = any(
        kw in combined_code
        for kw in [
            "docker_socket",
            "DOCKER_HOST",
            "docker_restart",
            "docker_list",
            "tecnativa",
            "docker.from_env",
            "docker_inspect",
        ]
    )

    has_external_network = any(
        kw in combined_code
        for kw in [
            "httpx",
            "requests",
            "urllib",
            "weather",
            "news",
            "rss",
            "datosgob",
            "http://",
            "https://",
        ]
    )

    return {
        "package_name": package_name,
        "package_dir": package_dir,
        "engines": engines,
        "is_privileged": is_privileged,
        "has_external_network": has_external_network,
        "error": None,
    }


def inspect_plugins_in_dir(target_plugins_dir: Path) -> list[dict[str, Any]]:
    """Inspecciona todos los plugins existentes en target_plugins_dir."""
    if not target_plugins_dir.is_dir():
        return []

    plugins: list[dict[str, Any]] = []
    for entry in target_plugins_dir.iterdir():
        if entry.is_dir() or entry.is_symlink():
            meta = inspect_plugin_metadata(entry)
            if not meta.get("error"):
                plugins.append(meta)
    return plugins


def link_plugin(
    plugin_path: Path | str = ".",
    target_dir: Path | str | None = None,
    force: bool = False,
) -> tuple[int, str]:
    """Crea un enlace simbólico de un plugin hacia el directorio plugins/ del agente."""
    meta = inspect_plugin_metadata(plugin_path)
    if meta.get("error"):
        return 1, f"❌ Error: {meta['error']}"

    pkg_name = meta["package_name"]
    pkg_dir: Path = meta["package_dir"]
    target_plugins = resolve_target_plugins_dir(target_dir)
    target_plugins.mkdir(parents=True, exist_ok=True)

    symlink_path = target_plugins / pkg_name

    existing_plugins = [
        p for p in inspect_plugins_in_dir(target_plugins) if p["package_name"] != pkg_name
    ]

    # 1. Comprobación de colisión de motores cognitivos exclusivos
    for existing in existing_plugins:
        shared_engines = set(meta["engines"]).intersection(set(existing["engines"]))
        if shared_engines:
            conflicts = ", ".join(sorted(shared_engines))
            if not force:
                return (
                    2,
                    f"❌ Conflicto de Motores Cognitivos Detectado:\n"
                    f"   El plugin '{pkg_name}' define motor(es) [{conflicts}], pero el agente ya\n"
                    f"   tiene activo el plugin '{existing['package_name']}' con el mismo tipo de motor.\n"
                    f"   Dos plugins no pueden registrar la misma capacidad de ciclo (BootConflictError).\n"
                    f"   Usa --force para ignorar esta validación si es para un entorno de pruebas.",
                )

    # 2. Comprobación de seguridad: Privilegios de Docker / Infraestructura vs Red Externa
    for existing in existing_plugins:
        if (meta["is_privileged"] and existing["has_external_network"]) or (
            meta["has_external_network"] and existing["is_privileged"]
        ):
            priv_name = pkg_name if meta["is_privileged"] else existing["package_name"]
            net_name = pkg_name if meta["has_external_network"] else existing["package_name"]
            if not force:
                return (
                    3,
                    f"⚠️  ALERTA DE SEGURIDAD (Principio de Mínimo Privilegio - AGENTE-SEC-01):\n"
                    f"   Conflicto de aislamiento detectado:\n"
                    f"   • Plugin con privilegios sobre Docker/sistema: '{priv_name}'\n"
                    f"   • Plugin expuesto a red externa/estímulos abiertos: '{net_name}'\n\n"
                    f"   Mezclar ambos perfiles en el mismo runtime de ejecución vulnera el aislamiento\n"
                    f"   y expone el daemon de Docker ante posibles movimientos laterales o inyecciones.\n"
                    f"   Se recomienda mantener cada perfil en un agente independiente (Estrategia Multi-Agente).\n"
                    f"   Usa --force para forzar la vinculación en entornos de desarrollo local.",
                )

    # 3. Crear o actualizar enlace simbólico
    if symlink_path.is_symlink():
        symlink_path.unlink()
    elif symlink_path.exists():
        if not force:
            return (
                1,
                f"❌ El destino '{symlink_path}' ya existe y no es un enlace simbólico.\n"
                f"   Usa --force para reemplazarlo.",
            )
        import shutil

        try:
            if symlink_path.is_dir():
                shutil.rmtree(symlink_path)
            else:
                symlink_path.unlink()
        except PermissionError:
            return (
                1,
                f"❌ Error de permisos al intentar reemplazar '{symlink_path}'.\n"
                f"   Si hay un contenedor Docker activo montando esta ruta, deténgalo primero ('docker compose stop').",
            )

    try:
        try:
            rel_target = os.path.relpath(pkg_dir, start=target_plugins)
            symlink_path.symlink_to(rel_target, target_is_directory=True)
            link_display = f"{rel_target}"
        except ValueError:
            symlink_path.symlink_to(pkg_dir, target_is_directory=True)
            link_display = f"{pkg_dir}"

        return (
            0,
            f"✨ Plugin '{pkg_name}' enlazado con éxito:\n"
            f"   🔗 {symlink_path} -> {link_display}\n"
            f"   Directorio del agente: {target_plugins}",
        )
    except Exception as exc:
        return 1, f"❌ Fallo al crear el enlace simbólico: {exc}"


def unlink_plugin(
    plugin_name: str,
    target_dir: Path | str | None = None,
) -> tuple[int, str]:
    """Elimina de forma segura el enlace simbólico de un plugin."""
    target_plugins = resolve_target_plugins_dir(target_dir)
    target = target_plugins / plugin_name

    if not target.exists() and not target.is_symlink() and not plugin_name.startswith("jg_plugin_"):
        alt = target_plugins / f"jg_plugin_{plugin_name}"
        if alt.exists() or alt.is_symlink():
            target = alt
            plugin_name = alt.name

    if not target.exists() and not target.is_symlink():
        return (
            1,
            f"❌ No se encontró ningún plugin o enlace con el nombre '{plugin_name}' en: {target_plugins}",
        )

    if not target.is_symlink():
        return (
            1,
            f"❌ '{target}' es un directorio real y no un enlace simbólico.\n"
            f"   Por seguridad, jg unlink solo elimina enlaces simbólicos para no destruir código fuente.",
        )

    try:
        target.unlink()
        return 0, f"🗑️  Enlace simbólico '{plugin_name}' desvinculado con éxito de: {target_plugins}"
    except Exception as exc:
        return 1, f"❌ Fallo al eliminar enlace simbólico: {exc}"


def handle_link(args: argparse.Namespace) -> int:
    """Manejador del comando 'jg plugin link' / 'jg link'."""
    code, msg = link_plugin(
        plugin_path=getattr(args, "path", Path(".")),
        target_dir=getattr(args, "target", None),
        force=getattr(args, "force", False),
    )
    if code == 0:
        print(msg)
    else:
        print(msg, file=sys.stderr)
    return code


def handle_unlink(args: argparse.Namespace) -> int:
    """Manejador del comando 'jg plugin unlink' / 'jg unlink'."""
    code, msg = unlink_plugin(
        plugin_name=args.name,
        target_dir=getattr(args, "target", None),
    )
    if code == 0:
        print(msg)
    else:
        print(msg, file=sys.stderr)
    return code


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada principal para la CLI jg / jg-sdk."""
    prog_name = Path(sys.argv[0]).name if sys.argv and sys.argv[0] else "jg"
    if not prog_name.startswith("jg"):
        prog_name = "jg"

    parser = argparse.ArgumentParser(
        prog=prog_name,
        description="CLI para desarrollo y scaffolding de plugins en la plataforma jg_agente.",
    )
    parser.add_argument("--version", action="version", version=f"{prog_name} 1.1.0")

    subparsers = parser.add_subparsers(dest="subcommand", help="Comandos disponibles")

    def _configure_init_args(target_parser: argparse.ArgumentParser) -> None:
        target_parser.add_argument(
            "name",
            type=str,
            help="Nombre base del plugin (ej. 'network', 'database', 'jg_plugin_monitoring').",
        )
        target_parser.add_argument(
            "-p",
            "--path",
            type=Path,
            default=None,
            help="Directorio destino (por defecto ./jg_plugin_<nombre>).",
        )
        target_parser.add_argument(
            "-t",
            "--template",
            choices=["minimal", "standard", "full"],
            default="standard",
            help="Plantilla arquitectónica (minimal: 1 tool; standard: tools + observer + rollback; full: observer + planner + verifier).",
        )
        target_parser.add_argument(
            "-a",
            "--author",
            type=str,
            default="Equipo de Desarrollo",
            help="Nombre del autor o empresa para metadatos.",
        )
        target_parser.add_argument(
            "-d",
            "--desc",
            "--description",
            dest="description",
            type=str,
            default="",
            help="Descripción breve del propósito del plugin.",
        )
        target_parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Sobrescribe archivos si el directorio destino ya existe.",
        )

    def _configure_link_args(target_parser: argparse.ArgumentParser) -> None:
        target_parser.add_argument(
            "path",
            nargs="?",
            default=Path("."),
            type=Path,
            help="Ruta al plugin o paquete a vincular (por defecto: el directorio actual '.').",
        )
        target_parser.add_argument(
            "-t",
            "--target",
            "--target-dir",
            dest="target",
            type=Path,
            default=None,
            help="Directorio plugins/ de destino del agente (autodetectado si se omite).",
        )
        target_parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Fuerza la creación del enlace omitiendo advertencias de seguridad o conflictos.",
        )

    def _configure_unlink_args(target_parser: argparse.ArgumentParser) -> None:
        target_parser.add_argument(
            "name",
            type=str,
            help="Nombre del plugin a desvincular (ej. 'jg_plugin_conversational' o 'conversational').",
        )
        target_parser.add_argument(
            "-t",
            "--target",
            "--target-dir",
            dest="target",
            type=Path,
            default=None,
            help="Directorio plugins/ de destino del agente (autodetectado si se omite).",
        )

    def _configure_clean_args(target_parser: argparse.ArgumentParser) -> None:
        target_parser.add_argument(
            "name",
            nargs="?",
            type=str,
            default=None,
            help="Nombre o ruta del plugin a limpiar (ej. 'devops' o 'jg_plugin_devops'). Autodetectado si se omite.",
        )
        target_parser.add_argument(
            "-a",
            "--all",
            action="store_true",
            help="Elimina también el entorno virtual (.venv) además de cachés y contenedores.",
        )
        target_parser.add_argument(
            "-t",
            "--target",
            "--target-dir",
            dest="target",
            type=Path,
            default=None,
            help="Directorio plugins/ del agente donde desvincular enlaces simbólicos.",
        )
        target_parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Fuerza la detención y borrado de contenedores y enlaces sin confirmación.",
        )

    def _configure_build_args(target_parser: argparse.ArgumentParser) -> None:
        target_parser.add_argument(
            "path",
            nargs="?",
            type=Path,
            default=None,
            help="Ruta opcional al directorio raíz del plugin (por defecto: directorio actual).",
        )
        target_parser.add_argument(
            "-t",
            "--tag",
            dest="tag",
            type=str,
            default=None,
            help="Tag o nombre de la imagen Docker a construir (por defecto: $CI_REGISTRY_IMAGE:$CI_COMMIT_REF_SLUG o autodetectado).",
        )
        target_parser.add_argument(
            "--base-image",
            dest="base_image",
            type=str,
            default="registry.gitlab.com/javiergalvez-ia/jg_agente:latest",
            help="Imagen base del agente cognitivo (por defecto: registry.gitlab.com/javiergalvez-ia/jg_agente:latest).",
        )
        target_parser.add_argument(
            "--push",
            action="store_true",
            help="Publica la imagen en el registro Docker remoto tras compilarla.",
        )

    # 1. Subcomando 'plugin' con operaciones de plugin
    plugin_parser = subparsers.add_parser(
        "plugin",
        help="Gestión y desarrollo de plugins.",
    )
    plugin_subparsers = plugin_parser.add_subparsers(
        dest="plugin_subcommand",
        help="Operaciones de plugins",
    )
    plugin_init_parser = plugin_subparsers.add_parser(
        "init",
        help="Inicializa la estructura de un nuevo plugin compatible con jg_agente.",
    )
    _configure_init_args(plugin_init_parser)

    plugin_link_parser = plugin_subparsers.add_parser(
        "link",
        help="Crea un enlace simbólico del plugin en el agente con verificación de seguridad y compatibilidad.",
    )
    _configure_link_args(plugin_link_parser)

    plugin_unlink_parser = plugin_subparsers.add_parser(
        "unlink",
        help="Elimina el enlace simbólico de un plugin del directorio de plugins del agente.",
    )
    _configure_unlink_args(plugin_unlink_parser)

    plugin_clean_parser = plugin_subparsers.add_parser(
        "clean",
        help="Detiene contenedores autónomos o dedicados, desvincula symlinks en agentes y purga cachés.",
    )
    _configure_clean_args(plugin_clean_parser)

    plugin_status_parser = plugin_subparsers.add_parser(
        "status",
        help="Inspecciona el estado de salud y capacidades de un plugin específico o del ecosistema completo.",
    )
    plugin_status_parser.add_argument(
        "-g",
        "--global",
        dest="is_global",
        action="store_true",
        help="Fuerza la inspección global del ecosistema completo.",
    )
    plugin_status_parser.add_argument(
        "-t",
        "--target",
        "--target-dir",
        dest="target",
        type=Path,
        default=None,
        help="Directorio plugins/ del agente donde comprobar enlaces simbólicos.",
    )

    plugin_build_parser = plugin_subparsers.add_parser(
        "build",
        help="Construye la imagen Docker del plugin empaquetada junto a jg_agente.",
    )
    _configure_build_args(plugin_build_parser)

    # 2. Alias directos para conveniencia rápida
    init_parser = subparsers.add_parser(
        "init",
        help="Alias directo de 'jg plugin init'.",
    )
    _configure_init_args(init_parser)

    link_parser = subparsers.add_parser(
        "link",
        help="Alias directo de 'jg plugin link'.",
    )
    _configure_link_args(link_parser)

    unlink_parser = subparsers.add_parser(
        "unlink",
        help="Alias directo de 'jg plugin unlink'.",
    )
    _configure_unlink_args(unlink_parser)

    clean_parser = subparsers.add_parser(
        "clean",
        help="Alias directo de 'jg plugin clean'.",
    )
    _configure_clean_args(clean_parser)

    build_parser = subparsers.add_parser(
        "build",
        help="Alias directo de 'jg plugin build'.",
    )
    _configure_build_args(build_parser)

    # 3. Subcomando 'install'
    subparsers.add_parser(
        "install",
        help="Instala las dependencias del plugin y prepara el entorno virtual (.venv).",
        description="Ejecuta 'install.sh' o inicializa '.venv' instalando el SDK y el plugin en modo editable.",
    )

    # 4. Subcomando 'dev'
    dev_parser = subparsers.add_parser(
        "dev",
        help="Habilita el entorno virtual (.venv) o ejecuta comandos dentro de él.",
        description=(
            "Ejecuta un comando arbitrario en el entorno virtual del plugin (.venv).\n"
            "Si no se especifica ningún comando, inicia una subshell interactiva dentro del entorno.\n\n"
            "Ejemplos:\n"
            "  jg dev pytest\n"
            "  jg dev ruff check .\n"
            "  jg dev python -m mi_modulo"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    dev_parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Comando opcional a ejecutar dentro de .venv (ej. 'pytest', 'ruff check .').",
    )

    # 5. Subcomando 'run'
    run_parser = subparsers.add_parser(
        "run",
        help="Lanza el stack Docker Compose autónomo (Dashboard :8880, Agente :8881, PostgreSQL).",
        description=(
            "Lanza el entorno Docker Compose autónomo del plugin.\n"
            "El agente arranca mediante el script limpio 'docker/entrypoint.sh', aplicando automáticamente\n"
            "las migraciones troncales de base de datos ('alembic upgrade head') para crear y sincronizar\n"
            "las tablas 'core_executions' y 'core_audit_records' antes de iniciar el servidor web Uvicorn."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    run_parser.add_argument(
        "-d",
        "--down",
        action="store_true",
        help="Detiene todos los contenedores del entorno Docker Compose.",
    )
    run_parser.add_argument(
        "-l",
        "--logs",
        action="store_true",
        help="Muestra los logs en tiempo real de los servicios.",
    )
    run_parser.add_argument(
        "-b",
        "--build",
        action="store_true",
        help="Reconstruye las imágenes antes de levantar el stack.",
    )
    run_parser.add_argument(
        "-s",
        "--status",
        action="store_true",
        help="Muestra el estado actual de los contenedores del stack.",
    )
    run_parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Dirección IP o interfaz de enlace para exponer los servicios (ej. '127.0.0.1' o '0.0.0.0').",
    )
    run_parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Puerto en el host para el runtime del agente (por defecto 8881).",
    )
    run_parser.add_argument(
        "--agent-port",
        type=int,
        default=None,
        help="Puerto en el host para el agente (alias descriptivo de --port).",
    )
    run_parser.add_argument(
        "--dashboard-port",
        type=int,
        default=None,
        help="Puerto en el host para el Dashboard Web HITL (por defecto 8880).",
    )

    # 6. Subcomando 'reload'
    reload_parser = subparsers.add_parser(
        "reload",
        help="Recarga en caliente los plugins de los agentes en ejecución sin reiniciar el stack.",
    )
    reload_parser.add_argument(
        "target",
        nargs="?",
        default="all",
        choices=["all", "conversacional", "devops", "datosgob"],
        help="Agente objetivo a recargar (por defecto: all).",
    )

    # 7. Subcomando 'status'
    status_parser = subparsers.add_parser(
        "status",
        help="Inspecciona el estado de salud y capacidades de un plugin específico o del ecosistema completo.",
    )
    status_parser.add_argument(
        "-g",
        "--global",
        dest="is_global",
        action="store_true",
        help="Fuerza la inspección global del ecosistema completo aunque se ejecute dentro de un plugin.",
    )
    status_parser.add_argument(
        "-t",
        "--target",
        "--target-dir",
        dest="target",
        type=Path,
        default=None,
        help="Directorio plugins/ del agente donde comprobar enlaces simbólicos.",
    )

    # 8. Subcomando 'clean'
    # Configurado anteriormente vía alias y plugin clean

    # 9. Subcomando 'test'
    test_parser = subparsers.add_parser(
        "test",
        help="Ejecuta la suite de pruebas unitarias del plugin usando pytest.",
    )
    test_parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Argumentos adicionales a pasar a pytest.",
    )

    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help()
        return 0

    if args.subcommand == "install":
        return handle_install()

    if args.subcommand == "dev":
        raw_cmd = args.command
        if raw_cmd and raw_cmd[0] == "--":
            raw_cmd = raw_cmd[1:]
        return handle_dev(raw_cmd)

    if args.subcommand == "build" or (
        args.subcommand == "plugin" and getattr(args, "plugin_subcommand", None) == "build"
    ):
        return handle_build(args)

    if args.subcommand == "run":
        return handle_run(args)

    if args.subcommand == "reload" or (
        args.subcommand == "plugin" and getattr(args, "plugin_subcommand", None) == "reload"
    ):
        return handle_reload(args)

    if args.subcommand == "status" or (
        args.subcommand == "plugin" and getattr(args, "plugin_subcommand", None) == "status"
    ):
        return handle_status(args)

    if args.subcommand == "clean" or (
        args.subcommand == "plugin" and getattr(args, "plugin_subcommand", None) == "clean"
    ):
        return handle_clean(args)

    if args.subcommand == "test":
        return handle_test(args)

    if args.subcommand == "link" or (
        args.subcommand == "plugin" and getattr(args, "plugin_subcommand", None) == "link"
    ):
        return handle_link(args)

    if args.subcommand == "unlink" or (
        args.subcommand == "plugin" and getattr(args, "plugin_subcommand", None) == "unlink"
    ):
        return handle_unlink(args)

    is_plugin_init = (
        args.subcommand == "plugin" and getattr(args, "plugin_subcommand", None) == "init"
    )
    is_direct_init = args.subcommand == "init"

    if args.subcommand == "plugin" and not getattr(args, "plugin_subcommand", None):
        plugin_parser.print_help()
        return 0

    if is_plugin_init or is_direct_init:
        try:
            created_dir = generate_plugin_scaffold(
                name=args.name,
                target_dir=args.path,
                template=args.template,
                author=args.author,
                description=args.description,
                force=args.force,
            )
            print(f"✨ Plugin inicializado con éxito en: {created_dir}")
            print("\nEstructura generada:")
            print(f"  📁 {created_dir.name}/")
            print(
                "  ├── install.sh                  <-- Script de aprovisionamiento (.venv + SDK local)"
            )
            print("  ├── pyproject.toml")
            print(
                "  ├── docker-compose.yml          <-- Stack autónomo (Dashboard :8880, Agente :8881)"
            )
            print("  ├── README.md")
            print("  ├── .gitignore")
            print("  ├── tests/test_plugin.py")
            print(f"  └── {created_dir.name}/ (plugin.py, tools.py, etc.)")
            print("\nPróximos pasos:")
            target_display = created_dir.name if args.path is None else created_dir
            print(f"  1. cd {target_display}")
            print(
                "  2. jg dev                       <-- Activa entorno virtual y dependencias (.venv)"
            )
            print(
                "  3. jg run                       <-- Levanta stack autónomo en Docker (:8880 / :8881)"
            )
            print("\n🔐 Credenciales de acceso al Dashboard (http://localhost:8880/admin):")
            print("  • Usuario:    admin@local.test")
            print("  • Contraseña: admin123456")
            return 0
        except FileExistsError as exc:
            print(f"❌ Error: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"❌ Error al generar el plugin: {exc}", file=sys.stderr)
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
