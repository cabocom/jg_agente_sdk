# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Subcomandos 'link' y 'unlink' para vincular plugins con jg_agente."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from jg_sdk.cli.common import _detect_capabilities, _detect_package_dir_and_name


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

    package_dir, package_name = _detect_package_dir_and_name(source)
    if package_dir is None:
        return {"error": f"No se encontró un paquete Python válido con 'plugin.py' en: {source}"}

    engines, is_privileged, has_external_network = _detect_capabilities(package_dir)
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


def _check_conflicts(
    meta: dict[str, Any], existing_plugins: list[dict[str, Any]], force: bool
) -> tuple[int, str] | None:
    """Verifica colisiones de engines y compatibilidad de seguridad entre plugins."""
    pkg_name = meta["package_name"]
    for existing in existing_plugins:
        shared = set(meta["engines"]).intersection(set(existing["engines"]))
        if shared and not force:
            conflicts = ", ".join(sorted(shared))
            return (
                2,
                f"❌ Conflicto de Motores Cognitivos Detectado:\n"
                f"   El plugin '{pkg_name}' define motor(es) [{conflicts}], pero el agente ya\n"
                f"   tiene activo el plugin '{existing['package_name']}' con el mismo tipo de motor.\n"
                f"   Dos plugins no pueden registrar la misma capacidad de ciclo (BootConflictError).\n"
                f"   Usa --force para ignorar esta validación si es para un entorno de pruebas.",
            )

    for existing in existing_plugins:
        conflict = (meta["is_privileged"] and existing["has_external_network"]) or (
            meta["has_external_network"] and existing["is_privileged"]
        )
        if conflict and not force:
            priv_name = pkg_name if meta["is_privileged"] else existing["package_name"]
            net_name = pkg_name if meta["has_external_network"] else existing["package_name"]
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
    return None


def _create_or_replace_symlink(
    symlink_path: Path, pkg_dir: Path, target_plugins: Path, force: bool, pkg_name: str
) -> tuple[int, str]:
    """Crea o reemplaza el enlace simbólico de forma segura."""
    if symlink_path.is_symlink():
        symlink_path.unlink()
    elif symlink_path.exists():
        if not force:
            return (
                1,
                f"❌ El destino '{symlink_path}' ya existe y no es un enlace simbólico.\n"
                f"   Usa --force para reemplazarlo.",
            )
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

    existing = [p for p in inspect_plugins_in_dir(target_plugins) if p["package_name"] != pkg_name]
    conflict_res = _check_conflicts(meta, existing, force)
    if conflict_res is not None:
        return conflict_res

    return _create_or_replace_symlink(
        target_plugins / pkg_name, pkg_dir, target_plugins, force, pkg_name
    )


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
