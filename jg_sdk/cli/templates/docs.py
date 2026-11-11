# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Plantilla para generación de README.md de plugins."""

from __future__ import annotations


def get_readme_template(pkg_name: str, description: str, rel_sdk_path: str, raw_slug: str) -> str:
    """Genera el contenido del README.md."""
    return f"""# {pkg_name}

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
