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


DEFAULT_AGENT_PORTS: dict[str, int] = {
    "conversacional": 8001,
    "devops": 8002,
    "sales": 8873,
    "datosgob": 8881,
    "filmmaker": 8881,
}

KNOWN_AGENTS: list[tuple[str, str, int, str]] = [
    ("conversacional", "jg_agente_conversacional", 8001, "Agente Conversacional"),
    ("devops", "jg_agente_devops", 8002, "Agente DevOps"),
    ("sales", "jg_agente_sales", 8873, "Agente Sales"),
    ("datosgob", "jg_agente_datosgob", 8881, "Agente Datos Gob"),
]


def _inspect_pyproject_plugin(pyproject_path: Path) -> tuple[bool, str]:
    """Inspecciona pyproject.toml para detectar entrypoint o nombre de plugin."""
    if not pyproject_path.is_file():
        return False, ""
    try:
        content = pyproject_path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, UnicodeDecodeError):
        return False, ""

    is_plugin = any(
        ep in content
        for ep in (
            '[project.entry-points."jg_agente.plugins"]',
            "[project.entry-points.'jg_agente.plugins']",
        )
    )
    pkg_name = ""
    match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
    if match:
        val = match.group(1).replace("-", "_")
        if val.startswith("jg_plugin_") or val.startswith("jg-plugin-"):
            is_plugin = True
            pkg_name = val
    return is_plugin, pkg_name


def _find_child_with_plugin(dir_path: Path) -> Path | None:
    """Busca un subdirectorio que contenga plugin.py."""
    if not dir_path.is_dir():
        return None
    try:
        for child in dir_path.iterdir():
            if child.is_dir() and (child / "plugin.py").is_file():
                return child
    except OSError:
        pass
    return None


def _detect_plugin_info(start_path: Path | None = None) -> tuple[bool, Path | None, str, str]:
    """Detecta si una ruta corresponde a un plugin del ecosistema jg_agente.

    Retorna:
        tuple[is_plugin, plugin_root, plugin_name, raw_slug]
    """
    curr = (start_path or Path.cwd()).resolve()
    excluded = {"jg_agente_sdk", "jg_agente", "jg_hub", "jg_dashboard", "jg_filmmaker"}

    for candidate in [curr, *curr.parents]:
        if candidate.name in excluded:
            continue

        is_plugin = candidate.name.startswith("jg_plugin_")
        pkg_name = candidate.name if is_plugin else ""

        p_plugin, p_name = _inspect_pyproject_plugin(candidate / "pyproject.toml")
        is_plugin = is_plugin or p_plugin
        pkg_name = pkg_name or p_name

        if not is_plugin:
            child = _find_child_with_plugin(candidate)
            if child is not None:
                is_plugin = True
                pkg_name = pkg_name or child.name

        if is_plugin:
            pkg_name = _sanitize_name(pkg_name or candidate.name)
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
    except (subprocess.SubprocessError, OSError):
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
    if (source / "plugin.py").is_file():
        return source, source.name

    child = _find_child_with_plugin(source)
    package_dir = child
    package_name = child.name if child is not None else ""

    _, p_name = _inspect_pyproject_plugin(source / "pyproject.toml")
    if p_name and not package_name:
        package_name = p_name
        if (source / p_name).is_dir():
            package_dir = source / p_name

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
