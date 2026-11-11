# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Subcomando 'clean' para detener contenedores, desvincular symlinks y purgar cachés."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from jg_sdk.cli.common import (
    _detect_plugin_info,
    _find_matching_containers,
)
from jg_sdk.cli.link_cmd import resolve_target_plugins_dir


def _resolve_plugin_to_clean(raw_name: str | None) -> tuple[bool, Path | None, str, str]:
    """Resuelve la información del plugin que se desea limpiar."""
    if not raw_name:
        return _detect_plugin_info(Path.cwd())

    candidate_path = Path(raw_name).resolve()
    if candidate_path.is_dir():
        is_p, root_p, name_p, slug_p = _detect_plugin_info(candidate_path)
        if is_p:
            return is_p, root_p, name_p, slug_p

    for p in [Path.cwd(), *Path.cwd().parents]:
        for candidate in [p / raw_name, p / f"jg_plugin_{raw_name}"]:
            if candidate.is_dir():
                is_p, root_p, name_p, slug_p = _detect_plugin_info(candidate)
                if is_p:
                    return is_p, root_p, name_p, slug_p

    raw_slug = raw_name[len("jg_plugin_") :] if raw_name.startswith("jg_plugin_") else raw_name
    plugin_name = raw_name if raw_name.startswith("jg_plugin_") else f"jg_plugin_{raw_name}"
    return True, None, plugin_name, raw_slug


def _stop_compose_stack(plugin_root: Path | None, all_flag: bool) -> None:
    """Detiene el docker-compose local si existe."""
    if not plugin_root or not plugin_root.is_dir():
        return
    compose_file = None
    for cand in ["docker-compose.yml", "docker-compose.yaml", "compose.yml"]:
        if (plugin_root / cand).is_file():
            compose_file = plugin_root / cand
            break
    if compose_file:
        print(f"🛑 Deteniendo stack Docker Compose autónomo ({compose_file.name})...")
        cmd_down = ["docker", "compose", "-f", str(compose_file), "down"]
        if all_flag:
            cmd_down.append("--volumes")
        res_down = subprocess.run(cmd_down, cwd=plugin_root, capture_output=True, text=True)
        if res_down.returncode == 0:
            print("   ✅ Stack Docker Compose autónomo detenido y eliminado.")


def _remove_matching_containers(raw_slug: str, plugin_name: str) -> None:
    """Elimina contenedores de Docker coincidentes."""
    matched = _find_matching_containers(raw_slug, plugin_name)
    if matched:
        print(f"🐳 Contenedores Docker asociados detectados ({len(matched)}):")
        for c in matched:
            print(f"   • Deteniendo y eliminando '{c}'...")
            subprocess.run(["docker", "rm", "-f", c], capture_output=True)
            print(f"     ✓ Contenedor '{c}' eliminado.")
    else:
        print("🐳 Contenedores Docker: Ninguno asociado en ejecución.")


def _clean_symlinks(plugin_name: str, raw_slug: str, target_dir: Path | str | None) -> None:
    """Desvincula enlaces simbólicos en el directorio plugins/ del agente."""
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
    if not unlinked_any:
        print(f"🔗 Enlaces en jg_agente: Ninguno activo en {target_plugins.name}/.")


def _purge_local_caches(plugin_root: Path | None, all_flag: bool) -> None:
    """Purga cachés locales y venv si corresponde."""
    if not plugin_root or not plugin_root.is_dir():
        return
    for root_walk, dirs, _ in os.walk(plugin_root):
        for d in list(dirs):
            if d in ("__pycache__", ".pytest_cache", ".ruff_cache") or d.endswith(".egg-info"):
                shutil.rmtree(Path(root_walk) / d, ignore_errors=True)
    if all_flag:
        venv_path = plugin_root / ".venv"
        if venv_path.is_dir():
            shutil.rmtree(venv_path, ignore_errors=True)
            print("   🧹 Entorno virtual .venv eliminado.")
    print("   🧹 Cachés temporales purgadas (__pycache__, pytest, ruff).")


def handle_clean(args: argparse.Namespace) -> int:
    """Detiene y elimina contenedores autónomos, desvincula symlinks y purga cachés."""
    raw_name = getattr(args, "name", None)
    all_flag = getattr(args, "all", False)
    target_dir = getattr(args, "target", None)

    is_plugin, plugin_root, plugin_name, raw_slug = _resolve_plugin_to_clean(raw_name)

    if not is_plugin or not plugin_name:
        print(
            "❌ No se detectó ningún plugin en el directorio actual.\n"
            "   Especifica el nombre del plugin (ej. 'jg clean devops') o ejecuta desde su directorio.",
            file=sys.stderr,
        )
        return 1

    print("=" * 65)
    print(f"🧹 Limpieza de Recursos y Enlaces: {plugin_name} ({raw_slug})")
    print("=" * 65)

    _stop_compose_stack(plugin_root, all_flag)
    _remove_matching_containers(raw_slug, plugin_name)
    _clean_symlinks(plugin_name, raw_slug, target_dir)
    _purge_local_caches(plugin_root, all_flag)

    print("\n" + "=" * 65)
    print(f"✨ Plugin '{plugin_name}' limpiado con éxito.")
    print("=" * 65)
    return 0
