# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Configuración de argumentos y parsers para la CLI."""

from __future__ import annotations

import argparse
from pathlib import Path


def configure_init_args(target_parser: argparse.ArgumentParser) -> None:
    """Configura los argumentos del comando 'init'."""
    target_parser.add_argument(
        "name",
        type=str,
        help="Nombre base del plugin (ej. 'network', 'database', 'jg_plugin_monitoring').",
    )
    target_parser.add_argument(
        "-p",
        "--path",
        type=Path,
        default=None,
        help="Directorio destino (por defecto ./jg_plugin_<nombre>).",
    )
    target_parser.add_argument(
        "-t",
        "--template",
        choices=["minimal", "standard", "full"],
        default="standard",
        help="Plantilla arquitectónica (minimal: 1 tool; standard: tools + observer + rollback; full: observer + planner + verifier).",
    )
    target_parser.add_argument(
        "-a",
        "--author",
        type=str,
        default="Equipo de Desarrollo",
        help="Nombre del autor o empresa para metadatos.",
    )
    target_parser.add_argument(
        "-d",
        "--desc",
        "--description",
        dest="description",
        type=str,
        default="",
        help="Descripción breve del propósito del plugin.",
    )
    target_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Sobrescribe archivos si el directorio destino ya existe.",
    )


def configure_link_args(target_parser: argparse.ArgumentParser) -> None:
    """Configura los argumentos del comando 'link'."""
    target_parser.add_argument(
        "path",
        nargs="?",
        default=Path("."),
        type=Path,
        help="Ruta al plugin o paquete a vincular (por defecto: el directorio actual '.').",
    )
    target_parser.add_argument(
        "-t",
        "--target",
        "--target-dir",
        dest="target",
        type=Path,
        default=None,
        help="Directorio plugins/ de destino del agente (autodetectado si se omite).",
    )
    target_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Fuerza la creación del enlace omitiendo advertencias de seguridad o conflictos.",
    )


def configure_unlink_args(target_parser: argparse.ArgumentParser) -> None:
    """Configura los argumentos del comando 'unlink'."""
    target_parser.add_argument(
        "name",
        type=str,
        help="Nombre del plugin a desvincular (ej. 'jg_plugin_conversational' o 'conversational').",
    )
    target_parser.add_argument(
        "-t",
        "--target",
        "--target-dir",
        dest="target",
        type=Path,
        default=None,
        help="Directorio plugins/ de destino del agente (autodetectado si se omite).",
    )


def configure_clean_args(target_parser: argparse.ArgumentParser) -> None:
    """Configura los argumentos del comando 'clean'."""
    target_parser.add_argument(
        "name",
        nargs="?",
        type=str,
        default=None,
        help="Nombre o ruta del plugin a limpiar. Autodetectado si se omite.",
    )
    target_parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Elimina también el entorno virtual (.venv) además de cachés y contenedores.",
    )
    target_parser.add_argument(
        "-t",
        "--target",
        "--target-dir",
        dest="target",
        type=Path,
        default=None,
        help="Directorio plugins/ del agente donde desvincular enlaces simbólicos.",
    )
    target_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Fuerza la detención y borrado sin confirmación.",
    )


def configure_build_args(target_parser: argparse.ArgumentParser) -> None:
    """Configura los argumentos del comando 'build'."""
    target_parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=None,
        help="Ruta opcional al directorio raíz del plugin (por defecto: directorio actual).",
    )
    target_parser.add_argument(
        "--tag",
        type=str,
        default=None,
        help="Tag completo de la imagen Docker resultante.",
    )
    target_parser.add_argument(
        "--base-image",
        type=str,
        default="registry.gitlab.com/javiergalvez-ia/jg_agente:latest",
        help="Imagen base de jg_agente sobre la cual inyectar el plugin.",
    )
    target_parser.add_argument(
        "--push",
        action="store_true",
        help="Publica la imagen construida inmediatamente en el Container Registry.",
    )


def _configure_subcommand_parsers(subparsers: argparse._SubParsersAction) -> None:
    """Registra subcomandos y sus banderas."""
    plugin_parser = subparsers.add_parser(
        "plugin", help="Comandos de gestión del ciclo de vida de plugins."
    )
    plugin_subparsers = plugin_parser.add_subparsers(
        dest="plugin_subcommand", help="Operación sobre el plugin"
    )

    p_init = plugin_subparsers.add_parser("init", help="Crea el andamiaje inicial.")
    configure_init_args(p_init)
    p_link = plugin_subparsers.add_parser("link", help="Enlaza el plugin en jg_agente.")
    configure_link_args(p_link)
    p_unlink = plugin_subparsers.add_parser("unlink", help="Desvincula el plugin de jg_agente.")
    configure_unlink_args(p_unlink)
    p_clean = plugin_subparsers.add_parser("clean", help="Limpia contenedores y enlaces.")
    configure_clean_args(p_clean)

    p_status = plugin_subparsers.add_parser("status", help="Inspecciona el estado del plugin.")
    p_status.add_argument(
        "-g", "--global", dest="is_global", action="store_true", help="Inspección global."
    )
    p_status.add_argument(
        "-t", "--target", dest="target", type=Path, default=None, help="Directorio plugins/."
    )

    p_build = plugin_subparsers.add_parser("build", help="Construye la imagen Docker del plugin.")
    configure_build_args(p_build)

    # Alias directos
    configure_init_args(subparsers.add_parser("init", help="Alias directo de 'jg plugin init'."))
    configure_link_args(subparsers.add_parser("link", help="Alias directo de 'jg plugin link'."))
    configure_unlink_args(
        subparsers.add_parser("unlink", help="Alias directo de 'jg plugin unlink'.")
    )
    configure_clean_args(subparsers.add_parser("clean", help="Alias directo de 'jg plugin clean'."))
    configure_build_args(subparsers.add_parser("build", help="Alias directo de 'jg plugin build'."))

    subparsers.add_parser(
        "install", help="Instala las dependencias del plugin y prepara el entorno .venv."
    )

    dev_p = subparsers.add_parser(
        "dev",
        help="Habilita el entorno virtual (.venv) o ejecuta comandos dentro de él.",
        description=(
            "Ejecuta un comando arbitrario en el entorno virtual del plugin (.venv).\n"
            "Si no se especifica ningún comando, inicia una subshell interactiva dentro del entorno.\n\n"
            "Ejemplos:\n"
            "  jg dev pytest\n"
            "  jg dev ruff check .\n"
            "  jg dev python -m mi_modulo"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    dev_p.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Comando opcional a ejecutar dentro de .venv (ej. 'pytest', 'ruff check .').",
    )

    run_p = subparsers.add_parser("run", help="Lanza el stack Docker Compose autónomo.")
    run_p.add_argument("-d", "--down", action="store_true", help="Detiene contenedores.")
    run_p.add_argument("-l", "--logs", action="store_true", help="Muestra logs.")
    run_p.add_argument("-b", "--build", action="store_true", help="Reconstruye imágenes.")
    run_p.add_argument("-s", "--status", action="store_true", help="Muestra estado.")
    run_p.add_argument("--host", type=str, default=None, help="Dirección IP de enlace.")
    run_p.add_argument("--port", type=int, default=None, help="Puerto del agente.")
    run_p.add_argument("--agent-port", type=int, default=None, help="Puerto del agente.")
    run_p.add_argument("--dashboard-port", type=int, default=None, help="Puerto del dashboard.")

    reload_p = subparsers.add_parser(
        "reload", help="Recarga en caliente los plugins de los agentes."
    )
    reload_p.add_argument(
        "target", nargs="?", default="all", choices=["all", "conversacional", "devops", "datosgob"]
    )

    status_p = subparsers.add_parser("status", help="Inspecciona el estado de salud y capacidades.")
    status_p.add_argument(
        "-g", "--global", dest="is_global", action="store_true", help="Inspección global."
    )
    status_p.add_argument(
        "-t", "--target", dest="target", type=Path, default=None, help="Directorio plugins/."
    )

    test_p = subparsers.add_parser(
        "test", help="Ejecuta la suite de pruebas del plugin usando pytest."
    )
    test_p.add_argument("pytest_args", nargs=argparse.REMAINDER, help="Argumentos para pytest.")


def create_cli_parser(prog_name: str = "jg") -> argparse.ArgumentParser:
    """Crea y devuelve el parser principal de la CLI jg / jg-sdk."""
    parser = argparse.ArgumentParser(
        prog=prog_name,
        description="CLI para desarrollo y scaffolding de plugins en la plataforma jg_agente.",
    )
    parser.add_argument("--version", action="version", version=f"{prog_name} 1.2.0")
    subparsers = parser.add_subparsers(dest="subcommand", help="Comandos disponibles")
    _configure_subcommand_parsers(subparsers)
    return parser
