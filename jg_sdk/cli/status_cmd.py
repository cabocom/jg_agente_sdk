# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Subcomando 'status' para inspeccionar salud y estado del plugin o del ecosistema."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import httpx

from jg_sdk.cli.common import (
    _detect_plugin_info,
    _find_matching_containers,
)
from jg_sdk.cli.link_cmd import resolve_target_plugins_dir


def _inspect_plugin_containers(containers: list[str]) -> list[str]:
    """Muestra el estado de los contenedores Docker asociados al plugin."""
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
    return running_containers


def _check_runtime_health(running_containers: list[str], raw_slug: str) -> None:
    """Verifica el endpoint /health y /capabilities del agente."""
    known_ports = {"devops": 8922, "conversacional": 8921, "sales": 8873, "datosgob": 8881}
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
                    print(
                        f"     └─► Capacidades: {cd.get('plugins_count', 0)} plugins | {cd.get('tools_count', 0)} tools"
                    )
            except Exception:
                pass
        else:
            print(f"  ⚠️  Runtime API:            HTTP {r.status_code}")
    except Exception:
        print(f"  ⚪ Runtime API:            OFFLINE (puerto {candidate_port})")


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

    has_compose = any(
        (plugin_root / f).is_file()
        for f in ["docker-compose.yml", "docker-compose.yaml", "compose.yml"]
    )
    mode_str = (
        "Autónomo (docker-compose.yml propio)"
        if has_compose
        else "Compartido / Integrado (montaje en runtime jg_agente)"
    )
    print(f"  🏗️  Modo Arquitectónico:   {mode_str}")

    target_plugins = resolve_target_plugins_dir(getattr(args, "target", None))
    symlink_found = None
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

    containers = _find_matching_containers(raw_slug, plugin_name)
    running_containers = _inspect_plugin_containers(containers)
    _check_runtime_health(running_containers, raw_slug)

    venv_ok = (plugin_root / ".venv").is_dir()
    tests_ok = (plugin_root / "tests").is_dir()
    print(f"  📦 Entorno Virtual (.venv): {'Presente' if venv_ok else 'Ausente'}")
    print(f"  🧪 Suite de Tests:         {'Presente (tests/)' if tests_ok else 'No encontrada'}")
    print("-" * 65)
    if not running_containers and not symlink_found:
        print("  🟢 ESTADO LIMPIO: El plugin no tiene contenedores activos ni enlaces.")
    else:
        print("  🟠 RECURSOS EN USO: Hay contenedores o enlaces activos (usa 'jg clean').")
    print("=" * 65)
    return 0


def _handle_global_status() -> int:
    """Muestra el estado global de todos los servicios del ecosistema."""
    services = [
        ("Portal & Docs (jg_hub)", "http://localhost:8930/up"),
        ("Dashboard (Control Plane)", "http://localhost:8003/up"),
        ("Agente Conversacional", "http://localhost:8921/health"),
        ("Agente DevOps", "http://localhost:8922/health"),
        ("Agente Sales", "http://localhost:8873/health"),
        ("Filmmaker Web", "http://localhost:8010/up"),
        ("Dashboard Autónomo (Plugins)", "http://localhost:8880/up"),
        ("Agente Autónomo (Plugins)", "http://localhost:8881/health"),
    ]

    print("=" * 65)
    print("🩺 Estado de Servicios y Runtimes (javiergalvez-ia)")
    print("=" * 65)

    for name, url in services:
        try:
            r = httpx.get(url, timeout=2.0)
            if r.status_code == 200:
                print(f"  ✅ {name:<30} ONLINE  ({url})")
            else:
                print(f"  ⚠️  {name:<30} HTTP {r.status_code} ({url})")
        except Exception:
            print(f"  ⚪ {name:<30} OFFLINE ({url})")

    print("=" * 65)
    return 0


def handle_status(args: argparse.Namespace) -> int:
    """Inspecciona la salud y capacidades de un plugin específico o del ecosistema completo."""
    if not getattr(args, "is_global", False):
        is_plugin, plugin_root, plugin_name, raw_slug = _detect_plugin_info(Path.cwd())
        if is_plugin and plugin_root is not None:
            return _handle_plugin_status(plugin_root, plugin_name, raw_slug, args)
    return _handle_global_status()
