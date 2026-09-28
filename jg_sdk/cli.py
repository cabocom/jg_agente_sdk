"""CLI de scaffolding y utilidades para el SDK de jg_agente.

Proporciona comandos de consola para inicializar nuevos plugins compatibles con
el ecosistema jg_agente de forma estandarizada y determinista.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

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
    image: registry.cabocom.net/javiergalvez-ia/jg_dashboard:latest
    container_name: jg_dashboard_{raw_slug}
    restart: unless-stopped
    depends_on:
      jg_dashboard_postgres:
        condition: service_healthy
    environment:
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
    image: registry.cabocom.net/javiergalvez-ia/jg_agente:latest
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


def _find_plugin_root() -> Path:
    """Busca la raíz del plugin buscando pyproject.toml o install.sh desde el directorio actual hacia arriba."""
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
    """Habilita y activa el entorno virtual de desarrollo (.venv) para el plugin."""
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
    res = subprocess.run(cmd, cwd=plugin_root, env=env)
    if res.returncode != 0:
        return res.returncode

    # Limpieza preventiva de agentes demo huérfanos en imágenes anteriores del dashboard
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
    print("📍 Puntos de acceso disponibles:")
    print(f"   🌐 Dashboard Web HITL:      http://localhost:{effective_dashboard_port}/admin")
    print(f"   🤖 Agente API REST:         http://localhost:{effective_agent_port}")
    print(f"   🔍 Capacidades Plugins:     http://localhost:{effective_agent_port}/capabilities")
    print(f"   🩺 Comprobación de Salud:   http://localhost:{effective_agent_port}/health")
    print("   🗄️ PostgreSQL Dashboard:   Interno (red privada Docker, host 8882 desactivado)")
    print("   🗄️ PostgreSQL Agente:      Interno (red privada Docker, host 8883 desactivado)")
    print("\n🔐 Credenciales de acceso al Dashboard:")
    print("   • URL:                      http://localhost:8880/admin")
    print("   • Usuario:                  admin@local.test")
    print("   • Contraseña:               admin123456")
    print("\n💡 Comandos de gestión rápida:")
    print("   • Ver logs en tiempo real:  jg run -l")
    print("   • Ver estado de servicios:  jg run -s")
    print("   • Detener el entorno:       jg run --down")
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


def handle_status(args: argparse.Namespace) -> int:
    """Inspecciona la salud y capacidades de los servicios del ecosistema."""
    services = [
        ("Dashboard (Control Plane)", "http://localhost:8080/up", "web", 8080),
        ("Dashboard Autónomo", "http://localhost:8880/up", "web", 8880),
        ("Agente Conversacional", "http://localhost:8001/health", "agent", 8001),
        ("Agente DevOps", "http://localhost:8002/health", "agent", 8002),
        ("Agente Datos Gob", "http://localhost:8881/health", "agent", 8881),
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


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada principal para la CLI jg / jg-sdk."""
    prog_name = Path(sys.argv[0]).name if sys.argv and sys.argv[0] else "jg"
    if not prog_name.startswith("jg"):
        prog_name = "jg"

    parser = argparse.ArgumentParser(
        prog=prog_name,
        description="CLI para desarrollo y scaffolding de plugins en la plataforma jg_agente.",
    )
    parser.add_argument("--version", action="version", version=f"{prog_name} 1.0.0")

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

    # 1. Subcomando 'plugin' con sub-subcomando 'init'
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

    # 2. Alias directo 'init' para conveniencia rápida
    init_parser = subparsers.add_parser(
        "init",
        help="Alias directo de 'jg-sdk plugin init'.",
    )
    _configure_init_args(init_parser)

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
    subparsers.add_parser(
        "status",
        help="Inspecciona el estado de salud y capacidades de los agentes y dashboard.",
    )

    # 8. Subcomando 'test'
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

    if args.subcommand == "run":
        return handle_run(args)

    if args.subcommand == "reload" or (
        args.subcommand == "plugin" and getattr(args, "plugin_subcommand", None) == "reload"
    ):
        return handle_reload(args)

    if args.subcommand == "status":
        return handle_status(args)

    if args.subcommand == "test":
        return handle_test(args)

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
