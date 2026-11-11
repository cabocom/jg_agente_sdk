# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Punto de entrada principal para la CLI jg / jg-sdk."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from jg_sdk.cli.build_cmd import handle_build
from jg_sdk.cli.clean_cmd import handle_clean
from jg_sdk.cli.common import (
    _detect_plugin_info,
    _find_matching_containers,
    _find_plugin_root,
    _sanitize_name,
    _to_pascal_case,
)
from jg_sdk.cli.dev_cmd import handle_dev, handle_install, handle_test
from jg_sdk.cli.init_cmd import generate_plugin_scaffold
from jg_sdk.cli.link_cmd import (
    handle_link,
    handle_unlink,
    inspect_plugin_metadata,
    inspect_plugins_in_dir,
    link_plugin,
    resolve_target_plugins_dir,
    unlink_plugin,
)
from jg_sdk.cli.parser import create_cli_parser
from jg_sdk.cli.reload_cmd import handle_reload
from jg_sdk.cli.status_cmd import handle_status

__all__ = [
    "_detect_plugin_info",
    "_find_matching_containers",
    "_find_plugin_root",
    "_sanitize_name",
    "_to_pascal_case",
    "generate_plugin_scaffold",
    "handle_build",
    "handle_clean",
    "handle_dev",
    "handle_install",
    "handle_link",
    "handle_reload",
    "handle_status",
    "handle_test",
    "handle_unlink",
    "inspect_plugin_metadata",
    "inspect_plugins_in_dir",
    "link_plugin",
    "main",
    "resolve_target_plugins_dir",
    "unlink_plugin",
]


def _dispatch_init(args: argparse.Namespace) -> int:
    """Ejecuta la inicialización interactiva o directa de un nuevo plugin."""
    try:
        created_dir = generate_plugin_scaffold(
            name=args.name,
            target_dir=args.path,
            template=args.template,
            author=args.author,
            description=args.description,
            force=args.force,
        )
        print(f"✨ Plugin inicializado con éxito en: {created_dir}")
        print("\nEstructura generada:")
        print(f"  📁 {created_dir.name}/")
        print(
            "  ├── install.sh                  <-- Script de aprovisionamiento (.venv + SDK local)"
        )
        print("  ├── pyproject.toml")
        print(
            "  ├── docker-compose.yml          <-- Stack autónomo (Dashboard :8880, Agente :8881)"
        )
        print("  ├── README.md")
        print("  ├── .gitignore")
        print("  ├── tests/test_plugin.py")
        print(f"  └── {created_dir.name}/ (plugin.py, tools.py, etc.)")
        print("\nPróximos pasos:")
        target_display = created_dir.name if args.path is None else created_dir
        print(f"  1. cd {target_display}")
        print("  2. jg dev                       <-- Activa entorno virtual y dependencias (.venv)")
        print(
            "  3. jg run                       <-- Levanta stack autónomo en Docker (:8880 / :8881)"
        )
        print("\n🔐 Credenciales de acceso al Dashboard (http://localhost:8880/admin):")
        print("  • Usuario:    admin@local.test")
        print("  • Contraseña: admin123456")
        return 0
    except FileExistsError as exc:
        print(f"❌ Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"❌ Error al generar el plugin: {exc}", file=sys.stderr)
        return 2


def _dispatch_command(args: argparse.Namespace) -> int:
    """Enruta el comando seleccionado a su función correspondiente."""
    sub = args.subcommand
    plugin_sub = getattr(args, "plugin_subcommand", None)

    if sub == "install":
        return handle_install()
    if sub == "dev":
        raw_cmd = args.command
        if raw_cmd and raw_cmd[0] == "--":
            raw_cmd = raw_cmd[1:]
        return handle_dev(raw_cmd)
    if sub == "build" or (sub == "plugin" and plugin_sub == "build"):
        return handle_build(args)
    if sub == "run":
        from jg_sdk.cli.dev_cmd import handle_run

        return handle_run(args)
    if sub == "reload" or (sub == "plugin" and plugin_sub == "reload"):
        return handle_reload(args)
    if sub == "status" or (sub == "plugin" and plugin_sub == "status"):
        return handle_status(args)
    if sub == "clean" or (sub == "plugin" and plugin_sub == "clean"):
        return handle_clean(args)
    if sub == "test":
        return handle_test(args)
    if sub == "link" or (sub == "plugin" and plugin_sub == "link"):
        return handle_link(args)
    if sub == "unlink" or (sub == "plugin" and plugin_sub == "unlink"):
        return handle_unlink(args)
    if (sub == "plugin" and plugin_sub == "init") or sub == "init":
        return _dispatch_init(args)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada principal para la CLI jg / jg-sdk."""
    prog_name = Path(sys.argv[0]).name if sys.argv and sys.argv[0] else "jg"
    if not prog_name.startswith("jg"):
        prog_name = "jg"

    parser = create_cli_parser(prog_name)
    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help()
        return 0

    if args.subcommand == "plugin" and not getattr(args, "plugin_subcommand", None):
        parser.print_help()
        return 0

    return _dispatch_command(args)


if __name__ == "__main__":
    sys.exit(main())
