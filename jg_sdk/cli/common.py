# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Módulo de utilidades y detección de plugins para la CLI."""

from __future__ import annotations

import contextlib
import re
import subprocess
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


def _detect_plugin_info(start_path: Path | None = None) -> tuple[bool, Path | None, str, str]:
    """Detecta si una ruta corresponde a un plugin del ecosistema jg_agente.

    Retorna:
        tuple[is_plugin, plugin_root, plugin_name, raw_slug]
    """
    curr = (start_path or Path.cwd()).resolve()
    candidates = [curr, *curr.parents]

    for candidate in candidates:
        if candidate.name in (
            "jg_agente_sdk",
            "jg_agente",
            "jg_hub",
            "jg_dashboard",
            "jg_filmmaker",
        ):
            continue

        is_plugin = False
        pkg_name = ""

        # 1. Por convención de nombre de directorio
        if candidate.name.startswith("jg_plugin_"):
            is_plugin = True
            pkg_name = candidate.name

        # 2. Por pyproject.toml con entrypoint de plugins o nombre del paquete
        pyproject = candidate / "pyproject.toml"
        if pyproject.is_file():
            try:
                content = pyproject.read_text(encoding="utf-8", errors="ignore")
                for line in content.splitlines():
                    cleaned_line = line.strip()
                    if cleaned_line.startswith(
                        '[project.entry-points."jg_agente.plugins"]'
                    ) or cleaned_line.startswith("[project.entry-points.'jg_agente.plugins']"):
                        is_plugin = True
                    if (
                        cleaned_line.startswith("name =") or cleaned_line.startswith("name=")
                    ) and not pkg_name:
                        val = cleaned_line.split("=")[1].strip().strip('"').strip("'")
                        if val.startswith("jg-plugin-") or val.startswith("jg_plugin_"):
                            is_plugin = True
                            pkg_name = val.replace("-", "_")
            except Exception:
                pass

        # 3. Por presencia de plugin.py en subcarpeta
        if not is_plugin and candidate.is_dir():
            try:
                for child in candidate.iterdir():
                    if child.is_dir() and (child / "plugin.py").is_file():
                        is_plugin = True
                        if not pkg_name:
                            pkg_name = child.name
                        break
            except Exception:
                pass

        if is_plugin:
            if not pkg_name:
                pkg_name = candidate.name
            pkg_name = _sanitize_name(pkg_name)
            if (
                not pkg_name.startswith("jg_plugin_")
                and (candidate / f"jg_plugin_{pkg_name}").exists()
            ):
                pkg_name = f"jg_plugin_{pkg_name}"
            raw_slug = (
                pkg_name[len("jg_plugin_") :] if pkg_name.startswith("jg_plugin_") else pkg_name
            )
            return True, candidate, pkg_name, raw_slug

    return False, None, "", ""


def _find_matching_containers(raw_slug: str, plugin_name: str) -> list[str]:
    """Busca contenedores Docker asociados determinísticamente a un plugin o agente."""
    try:
        res = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            return []
        matched: list[str] = []
        for line in res.stdout.strip().splitlines():
            name = line.strip()
            if not name:
                continue
            if (
                name == f"jg_agente_{raw_slug}"
                or name == f"jg_dashboard_{raw_slug}"
                or name == f"jg_agente_postgres_{raw_slug}"
                or name == f"jg_dashboard_postgres_{raw_slug}"
                or name.endswith(f"_{raw_slug}")
                or name == plugin_name
                or name == f"jg_{raw_slug}"
            ) and name not in matched:
                matched.append(name)
        return matched
    except Exception:
        return []


def _find_plugin_root() -> Path:
    """Busca la raíz del plugin buscando pyproject.toml o install.sh desde el directorio actual hacia arriba."""
    is_p, root_p, _, _ = _detect_plugin_info(Path.cwd())
    if is_p and root_p is not None:
        return root_p
    curr = Path.cwd().resolve()
    for parent in [curr, *curr.parents]:
        if (parent / "pyproject.toml").is_file() or (parent / "install.sh").is_file():
            return parent
    return curr


def _detect_package_dir_and_name(source: Path) -> tuple[Path | None, str]:
    """Detecta el directorio del paquete Python y su nombre a partir de una ruta fuente."""
    package_dir: Path | None = None
    package_name: str = ""

    if (source / "plugin.py").is_file():
        package_dir = source
        package_name = source.name
    elif source.is_dir():
        for child in source.iterdir():
            if child.is_dir() and (child / "plugin.py").is_file():
                package_dir = child
                package_name = child.name
                break

    pyproject = source / "pyproject.toml"
    if pyproject.is_file():
        content = pyproject.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
        if match and not package_name:
            pkg_name_from_pyproject = match.group(1).replace("-", "_")
            package_name = pkg_name_from_pyproject
            if (source / pkg_name_from_pyproject).is_dir():
                package_dir = source / pkg_name_from_pyproject

    if package_dir and not package_name:
        package_name = package_dir.name

    return package_dir, package_name


def _detect_capabilities(package_dir: Path) -> tuple[list[str], bool, bool]:
    """Inspecciona estáticamente el código del paquete para detectar engines y privilegios."""
    code_texts: list[str] = []
    for py_file in package_dir.glob("*.py"):
        with contextlib.suppress(Exception):
            code_texts.append(py_file.read_text(encoding="utf-8", errors="ignore"))

    combined = "\n".join(code_texts)

    engines: list[str] = []
    for engine, marker in [
        ("observer_engine", "ObserverEngine"),
        ("planner_engine", "PlannerEngine"),
        ("verifier_engine", "VerifierEngine"),
        ("diagnostic_engine", "DiagnosticEngine"),
    ]:
        if marker in combined:
            engines.append(engine)

    priv_kws = [
        "docker_socket",
        "DOCKER_HOST",
        "docker_restart",
        "docker_list",
        "tecnativa",
        "docker.from_env",
        "docker_inspect",
    ]
    is_privileged = any(kw in combined for kw in priv_kws)

    net_kws = [
        "httpx",
        "requests",
        "urllib",
        "weather",
        "news",
        "rss",
        "datosgob",
        "http://",
        "https://",
    ]
    has_external_network = any(kw in combined for kw in net_kws)

    return engines, is_privileged, has_external_network
