# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Subcomandos 'install', 'dev', 'run' y 'test' para el entorno de desarrollo local."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from jg_sdk.cli.common import _find_plugin_root


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


def _ensure_venv(plugin_root: Path) -> Path:
    """Verifica o crea el entorno virtual .venv del plugin."""
    venv_dir = plugin_root / ".venv"
    venv_python = venv_dir / "bin" / "python"
    if not venv_python.exists():
        print(f"📦 Entorno virtual no encontrado en: {venv_dir}")
        install_script = plugin_root / "install.sh"
        if install_script.exists():
            print(f"🚀 Ejecutando script de instalación {install_script.name}...")
            res = subprocess.run(["bash", str(install_script)], cwd=plugin_root)
            if res.returncode != 0:
                print(
                    f"❌ Error al ejecutar {install_script.name} (código {res.returncode})",
                    file=sys.stderr,
                )
        else:
            print("⚙️ Creando entorno virtual .venv...")
            res_venv = subprocess.run(
                [sys.executable, "-m", "venv", str(venv_dir)], cwd=plugin_root
            )
            if res_venv.returncode != 0:
                print(f"❌ Error al crear .venv (código {res_venv.returncode})", file=sys.stderr)
                return venv_dir
            pip_bin = venv_dir / "bin" / "pip"
            res_pip = subprocess.run([str(pip_bin), "install", "-e", "."], cwd=plugin_root)
            if res_pip.returncode != 0:
                print(
                    f"❌ Error al instalar dependencias (código {res_pip.returncode})",
                    file=sys.stderr,
                )
    return venv_dir


def handle_dev(command: list[str] | None = None) -> int:
    """Habilita el entorno virtual (.venv) o ejecuta un comando dentro de él."""
    plugin_root = _find_plugin_root()
    venv_dir = _ensure_venv(plugin_root)
    venv_python = venv_dir / "bin" / "python"

    new_env = os.environ.copy()
    new_env["VIRTUAL_ENV"] = str(venv_dir)
    new_env["PATH"] = f"{venv_dir / 'bin'}:{new_env.get('PATH', '')}"
    new_env.pop("PYTHONHOME", None)

    if command:
        cmd = list(command)
        bin_candidate = venv_dir / "bin" / cmd[0]
        if bin_candidate.exists():
            cmd[0] = str(bin_candidate)
        res = subprocess.run(cmd, env=new_env, cwd=plugin_root)
        return res.returncode

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
    except (OSError, RuntimeError) as exc:
        print(f"❌ Error al iniciar subshell: {exc}", file=sys.stderr)
        return 1


def handle_test(args: argparse.Namespace) -> int:
    """Ejecuta la suite de pruebas del plugin usando pytest."""
    pytest_args = getattr(args, "pytest_args", [])
    if pytest_args and pytest_args[0] == "--":
        pytest_args = pytest_args[1:]
    cmd = ["pytest"] + pytest_args
    return handle_dev(cmd)


def _print_run_summary(effective_dashboard_port: str, effective_agent_port: str) -> None:
    """Imprime el banner informativo de acceso al stack autónomo."""
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


def _find_compose_file(plugin_root: Path) -> Path | None:
    """Busca el archivo de configuración Docker Compose en la raíz del plugin."""
    for candidate in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]:
        p = plugin_root / candidate
        if p.exists():
            return p
    return None


def _build_compose_env(args: argparse.Namespace) -> tuple[dict[str, str], str, str]:
    """Construye las variables de entorno para Docker Compose."""
    env = os.environ.copy()
    agent_port = getattr(args, "agent_port", None) or getattr(args, "port", None)
    if agent_port is not None:
        env["AGENT_PORT"] = str(agent_port)
    dashboard_port = getattr(args, "dashboard_port", None)
    if dashboard_port is not None:
        env["DASHBOARD_PORT"] = str(dashboard_port)
    if getattr(args, "host", None):
        env["HOST"] = str(args.host)
    return env, env.get("DASHBOARD_PORT", "8880"), env.get("AGENT_PORT", "8881")


def handle_run(args: argparse.Namespace) -> int:
    """Lanza o gestiona el entorno Docker Compose autónomo del plugin."""
    plugin_root = _find_plugin_root()
    compose_file = _find_compose_file(plugin_root)
    if not compose_file:
        print(f"❌ No se encontró 'docker-compose.yml' en {plugin_root}.", file=sys.stderr)
        return 1

    sub_actions = {
        "down": (
            ["docker", "compose", "-f", str(compose_file), "down"],
            "🛑 Deteniendo entorno Docker Compose...",
        ),
        "logs": (["docker", "compose", "-f", str(compose_file), "logs", "-f"], None),
        "status": (["docker", "compose", "-f", str(compose_file), "ps"], None),
    }
    for flag, (action_cmd, msg) in sub_actions.items():
        if getattr(args, flag, False):
            if msg:
                print(msg)
            return subprocess.run(action_cmd, cwd=plugin_root).returncode

    cmd = ["docker", "compose", "-f", str(compose_file), "up", "-d"]
    if getattr(args, "build", False):
        cmd.append("--build")

    env, eff_dash_port, eff_agent_port = _build_compose_env(args)
    print(f"🐳 Iniciando stack Docker Compose autónomo ({compose_file.name})...")
    res = subprocess.run(cmd, cwd=plugin_root, env=env)
    if res.returncode == 0:
        _print_run_summary(eff_dash_port, eff_agent_port)
    return res.returncode
