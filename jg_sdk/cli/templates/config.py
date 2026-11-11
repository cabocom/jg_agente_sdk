# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Plantillas de configuración para plugins: pyproject.toml, .gitignore, install.sh y .env."""

from __future__ import annotations


def get_pyproject_template(
    distribution_name: str,
    description: str,
    author: str,
    raw_slug: str,
    pkg_name: str,
    plugin_class_name: str,
) -> str:
    """Genera el contenido de pyproject.toml."""
    return f"""[project]
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


def get_gitignore_template() -> str:
    """Genera el contenido de .gitignore."""
    return """# Entornos virtuales
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


def get_install_script_template(distribution_name: str, rel_sdk_path: str) -> str:
    """Genera el contenido de install.sh."""
    return f"""#!/usr/bin/env bash
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


def get_env_templates(pkg_name: str, detected_llm_model: str) -> tuple[str, str]:
    """Genera el contenido de .env.example y .env."""
    env_example = f"""# Configuración del entorno de desarrollo para el plugin
ENV=development
GROQ_API_KEY=
LLM_PROVIDER=groq
LLM_MODEL={detected_llm_model}
JG_AGENTE_SECRET=secret_dev_token_12345
ADMIN_EMAIL=admin@local.test
ADMIN_DEFAULT_PASSWORD=admin123456
"""
    env_actual = f"""# Variables de entorno locales generadas para {pkg_name}
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
    return env_example, env_actual
