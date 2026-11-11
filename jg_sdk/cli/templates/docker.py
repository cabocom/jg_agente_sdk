# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Plantillas de Docker: docker-compose.yml y entrypoint.sh."""

from __future__ import annotations


def get_docker_compose_template(
    pkg_name: str, raw_slug: str, class_prefix: str, detected_llm_model: str
) -> str:
    """Genera el contenido de docker-compose.yml."""
    return f"""# ==============================================================================
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


def get_docker_entrypoint_template(pkg_name: str) -> str:
    """Genera el contenido de docker/entrypoint.sh."""
    return f"""#!/bin/sh
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
