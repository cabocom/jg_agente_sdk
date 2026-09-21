"""CLI de scaffolding y utilidades para el SDK de jg_agente.

Proporciona comandos de consola para inicializar nuevos plugins compatibles con
el ecosistema jg_agente de forma estandarizada y determinista.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


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
        raise ValueError(f"Plantilla desconocida '{template}'. Opciones válidas: {sorted(valid_templates)}")

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

    if out_dir.exists() and not force:
        # Si el directorio existe y tiene contenido, rechazar
        if any(out_dir.iterdir()):
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
        import os
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
"""

    # 3. Creación de directorios y escritura de archivos
    pkg_dir = out_dir / pkg_name
    tests_dir = out_dir / "tests"

    pkg_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")
    (out_dir / ".gitignore").write_text(gitignore_content, encoding="utf-8")
    (out_dir / "README.md").write_text(readme_content, encoding="utf-8")

    install_file = out_dir / "install.sh"
    install_file.write_text(install_script_content, encoding="utf-8")
    install_file.chmod(install_file.stat().st_mode | 0o755)

    (pkg_dir / "__init__.py").write_text(init_content, encoding="utf-8")
    (pkg_dir / "plugin.py").write_text(plugin_file_content, encoding="utf-8")
    (pkg_dir / "tools.py").write_text(tools_content, encoding="utf-8")

    if engines_file_content:
        (pkg_dir / "engines.py").write_text(engines_file_content, encoding="utf-8")

    (tests_dir / "__init__.py").write_text("", encoding="utf-8")
    (tests_dir / "test_plugin.py").write_text(test_content, encoding="utf-8")

    return out_dir


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada principal para la CLI jg-sdk."""
    parser = argparse.ArgumentParser(
        prog="jg-sdk",
        description="CLI para desarrollo y scaffolding de plugins en la plataforma jg_agente.",
    )
    parser.add_argument("--version", action="version", version="jg-sdk 1.0.0")

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

    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help()
        return 0

    is_plugin_init = args.subcommand == "plugin" and getattr(args, "plugin_subcommand", None) == "init"
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
            print("  ├── install.sh                  <-- Script de aprovisionamiento (.venv + SDK local)")
            print("  ├── pyproject.toml")
            print("  ├── README.md")
            print("  ├── .gitignore")
            print("  ├── tests/test_plugin.py")
            print(f"  └── {created_dir.name}/ (plugin.py, tools.py, etc.)")
            print("\nPróximos pasos:")
            target_display = created_dir.name if args.path is None else created_dir
            print(f"  1. cd {target_display}")
            print("  2. ./install.sh")
            print("  3. source .venv/bin/activate")
            print("  4. pytest tests/")
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
