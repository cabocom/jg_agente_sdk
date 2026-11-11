# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Subcomando 'build' para empaquetado de plugins en imágenes Docker."""

from __future__ import annotations

import argparse
import contextlib
import os
import subprocess
import sys
from pathlib import Path

from jg_sdk.cli.common import _sanitize_name


def _resolve_plugin_name(plugin_root: Path) -> str:
    """Resuelve el nombre canónico del paquete del plugin."""
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

    plugin_name = _sanitize_name(plugin_name)
    if (
        not plugin_name.startswith("jg_plugin_")
        and (plugin_root / f"jg_plugin_{plugin_name}").exists()
    ):
        plugin_name = f"jg_plugin_{plugin_name}"
    return plugin_name


def _build_temporary_dockerfile(plugin_root: Path, plugin_name: str, base_image: str) -> Path:
    """Crea un Dockerfile temporal si no existe uno en la raíz."""
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
    return dockerfile_path


def _push_docker_image(raw_tag: str, plugin_root: Path) -> int:
    """Publica la imagen construida y etiqueta :latest si corresponde."""
    print(f"🚀 Publicando imagen en registro remoto: {raw_tag}...")
    res_push = subprocess.run(["docker", "push", raw_tag], cwd=plugin_root)
    if res_push.returncode != 0:
        print(f"❌ Error al publicar la imagen (código {res_push.returncode}).", file=sys.stderr)
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
    return 0


def handle_build(args: argparse.Namespace) -> int:
    """Construye y empaqueta la imagen Docker del plugin basada en jg_agente."""
    raw_path = getattr(args, "path", None)
    plugin_root = Path(raw_path).resolve() if raw_path else Path.cwd()
    plugin_name = _resolve_plugin_name(plugin_root)

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
        dockerfile_path = _build_temporary_dockerfile(plugin_root, plugin_name, base_image)
        temp_dockerfile = True

    try:
        cmd_build = ["docker", "build", "-t", raw_tag, "-f", str(dockerfile_path), str(plugin_root)]
        print(f"▶ Ejecutando: {' '.join(cmd_build)}")
        res = subprocess.run(cmd_build, cwd=plugin_root)
        if res.returncode != 0:
            print(f"❌ Error al construir imagen Docker ({res.returncode}).", file=sys.stderr)
            return res.returncode

        print(f"✓ Imagen construida con éxito: {raw_tag}")

        if getattr(args, "push", False):
            push_res = _push_docker_image(raw_tag, plugin_root)
            if push_res != 0:
                return push_res
    finally:
        if temp_dockerfile and dockerfile_path.exists():
            dockerfile_path.unlink()

    print("=" * 65)
    print(f"🎉 ¡Empaquetado Docker de '{plugin_name}' completado con éxito!")
    print("=" * 65)
    return 0
