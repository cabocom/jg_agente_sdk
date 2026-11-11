# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Subcomando 'init' para scaffolding de nuevos plugins."""

from __future__ import annotations

import os
from pathlib import Path

from jg_sdk.cli.common import _sanitize_name, _to_pascal_case
from jg_sdk.cli.templates import (
    get_docker_compose_template,
    get_docker_entrypoint_template,
    get_engines_template,
    get_env_templates,
    get_gitignore_template,
    get_install_script_template,
    get_plugin_class_template,
    get_pyproject_template,
    get_readme_template,
    get_test_template,
    get_tools_template,
)


def generate_plugin_scaffold(
    name: str,
    target_dir: Path | None = None,
    template: str = "standard",
    author: str = "Equipo de Desarrollo",
    description: str = "",
    force: bool = False,
) -> Path:
    """Genera la estructura de archivos para un nuevo plugin de jg_agente.

    Args:
        name: Nombre base del plugin (ej. 'network' o 'jg_plugin_network').
        target_dir: Ruta donde se creará el proyecto. Si es None, se usará el nombre del paquete.
        template: Tipo de plantilla ('minimal', 'standard', 'full').
        author: Nombre del autor o entidad desarrolladora.
        description: Descripción breve del plugin.
        force: Si es True, sobrescribe archivos si el directorio ya existe.

    Returns:
        Path al directorio del plugin creado.

    Raises:
        FileExistsError: Si el directorio destino existe y force es False.
        ValueError: Si la plantilla especificada no es válida.
    """
    valid_templates = {"minimal", "standard", "full"}
    if template not in valid_templates:
        raise ValueError(
            f"Plantilla desconocida '{template}'. Opciones válidas: {sorted(valid_templates)}"
        )

    base_name = _sanitize_name(name)
    if base_name.startswith("jg_plugin_"):
        raw_slug = base_name[len("jg_plugin_") :]
        pkg_name = base_name
    else:
        raw_slug = base_name
        pkg_name = f"jg_plugin_{base_name}"

    distribution_name = pkg_name.replace("_", "-")
    class_prefix = _to_pascal_case(raw_slug)
    plugin_class_name = f"{class_prefix}Plugin"
    if not description:
        description = f"Plugin de {raw_slug.replace('_', ' ')} para la plataforma jg_agente."

    out_dir = target_dir if target_dir is not None else Path(pkg_name)
    out_dir = out_dir.resolve()

    if out_dir.exists() and not force and any(out_dir.iterdir()):
        raise FileExistsError(
            f"El directorio de destino '{out_dir}' ya existe y no está vacío. Usa --force para sobrescribir."
        )

    # 1. Definir contenidos de archivos según template
    pyproject_content = get_pyproject_template(
        distribution_name=distribution_name,
        description=description,
        author=author,
        raw_slug=raw_slug,
        pkg_name=pkg_name,
        plugin_class_name=plugin_class_name,
    )
    gitignore_content = get_gitignore_template()
    tools_content = get_tools_template(template, pkg_name, raw_slug)
    engines_file_content = get_engines_template(template, pkg_name, class_prefix, raw_slug)
    plugin_file_content = get_plugin_class_template(
        template=template,
        pkg_name=pkg_name,
        plugin_class_name=plugin_class_name,
        class_prefix=class_prefix,
        raw_slug=raw_slug,
        description=description,
        author=author,
    )
    init_content = f'"""Paquete del plugin {pkg_name}."""\n\nfrom {pkg_name}.plugin import {plugin_class_name}\n\n__all__ = ["{plugin_class_name}"]\n'
    test_content = get_test_template(template, pkg_name, plugin_class_name, raw_slug)

    # 2. Calcular ruta relativa hacia el SDK local
    sdk_root = Path(__file__).resolve().parent.parent.parent
    try:
        rel_sdk_path = os.path.relpath(sdk_root, out_dir)
    except ValueError:
        rel_sdk_path = str(sdk_root)

    install_script_content = get_install_script_template(distribution_name, rel_sdk_path)
    readme_content = get_readme_template(pkg_name, description, rel_sdk_path, raw_slug)

    has_groq_key_in_env = bool(
        os.environ.get("GLOBAL_GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
    )
    detected_llm_model = os.environ.get("LLM_MODEL") or "openai/gpt-oss-120b"

    if has_groq_key_in_env:
        print(
            "⚠️  [Seguridad] Se detectó GROQ_API_KEY en el entorno, pero por seguridad "
            "NO se incluirá en el archivo .env generado para evitar fugas accidentales en Git.",
            flush=True,
        )

    docker_compose_content = get_docker_compose_template(
        pkg_name, raw_slug, class_prefix, detected_llm_model
    )
    docker_entrypoint_content = get_docker_entrypoint_template(pkg_name)
    env_example_content, env_content = get_env_templates(pkg_name, detected_llm_model)

    # 3. Creación de directorios y escritura de archivos
    pkg_dir = out_dir / pkg_name
    tests_dir = out_dir / "tests"
    docker_dir = out_dir / "docker"

    pkg_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)
    docker_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")
    (out_dir / ".gitignore").write_text(gitignore_content, encoding="utf-8")
    (out_dir / "README.md").write_text(readme_content, encoding="utf-8")
    (out_dir / "docker-compose.yml").write_text(docker_compose_content, encoding="utf-8")
    (out_dir / ".env.example").write_text(env_example_content, encoding="utf-8")
    (out_dir / ".env").write_text(env_content, encoding="utf-8")

    agent_entrypoint_file = docker_dir / "entrypoint.sh"
    agent_entrypoint_file.write_text(docker_entrypoint_content, encoding="utf-8")
    agent_entrypoint_file.chmod(agent_entrypoint_file.stat().st_mode | 0o755)

    install_file = out_dir / "install.sh"
    install_file.write_text(install_script_content, encoding="utf-8")
    install_file.chmod(install_file.stat().st_mode | 0o755)

    plugin_file_content_with_class = (
        plugin_file_content.rstrip()
        + f"\n\n\n# Exportación canónica para autodescubrimiento en PLUGINS_DIR\nPLUGIN_CLASS = {plugin_class_name}\n"
    )

    (pkg_dir / "__init__.py").write_text(init_content, encoding="utf-8")
    (pkg_dir / "plugin.py").write_text(plugin_file_content_with_class, encoding="utf-8")
    (pkg_dir / "tools.py").write_text(tools_content, encoding="utf-8")

    if engines_file_content:
        (pkg_dir / "engines.py").write_text(engines_file_content, encoding="utf-8")

    (tests_dir / "__init__.py").write_text("", encoding="utf-8")
    (tests_dir / "test_plugin.py").write_text(test_content, encoding="utf-8")

    return out_dir
