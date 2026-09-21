"""Pruebas unitarias para la CLI de scaffolding (jg_sdk.cli)."""

from pathlib import Path
import pytest
from jg_sdk.cli import _sanitize_name, _to_pascal_case, generate_plugin_scaffold, main


def test_naming_helpers():
    """Valida los formateadores de nombres a snake_case y PascalCase."""
    assert _to_pascal_case("network_diagnostics") == "NetworkDiagnostics"
    assert _to_pascal_case("devops-tools") == "DevopsTools"
    assert _to_pascal_case("monitoring") == "Monitoring"

    assert _sanitize_name("Network-Diagnostics") == "network_diagnostics"
    assert _sanitize_name("  monitoring_agent  ") == "monitoring_agent"
    assert _sanitize_name("special!!-characters--name") == "special_characters_name"


def test_generate_standard_scaffold(tmp_path: Path):
    """Verifica la generación de la plantilla estándar y su estructura de archivos."""
    target_dir = tmp_path / "jg_plugin_observability"
    created = generate_plugin_scaffold(
        name="observability",
        target_dir=target_dir,
        template="standard",
        author="SRE Team",
        description="Observabilidad avanzada.",
    )

    assert created == target_dir
    assert (target_dir / "pyproject.toml").is_file()
    assert (target_dir / "README.md").is_file()
    assert (target_dir / ".gitignore").is_file()
    assert (target_dir / "install.sh").is_file()
    # Comprobar permisos de ejecución en install.sh
    import os
    assert os.access(target_dir / "install.sh", os.X_OK)

    pkg_dir = target_dir / "jg_plugin_observability"
    assert (pkg_dir / "__init__.py").is_file()
    assert (pkg_dir / "plugin.py").is_file()
    assert (pkg_dir / "tools.py").is_file()
    assert (pkg_dir / "engines.py").is_file()

    test_file = target_dir / "tests" / "test_plugin.py"
    assert test_file.is_file()

    # Validar contenidos clave
    pyproject_text = (target_dir / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "jg-plugin-observability"' in pyproject_text
    assert '[project.entry-points."jg_agente.plugins"]' in pyproject_text
    assert 'observability = "jg_plugin_observability.plugin:ObservabilityPlugin"' in pyproject_text

    plugin_text = (pkg_dir / "plugin.py").read_text(encoding="utf-8")
    assert "class ObservabilityPlugin(BasePlugin):" in plugin_text
    assert 'tags=["observability"]' in plugin_text

    tools_text = (pkg_dir / "tools.py").read_text(encoding="utf-8")
    assert "name=\"observability_inspect\"" in tools_text
    assert "name=\"observability_action\"" in tools_text
    assert "rollback_action" in tools_text


def test_generate_minimal_scaffold(tmp_path: Path):
    """Verifica la plantilla minimal sin motores cognitivos."""
    target_dir = tmp_path / "jg_plugin_minimal"
    generate_plugin_scaffold(
        name="minimal",
        target_dir=target_dir,
        template="minimal",
    )

    pkg_dir = target_dir / "jg_plugin_minimal"
    assert (pkg_dir / "plugin.py").is_file()
    assert (pkg_dir / "tools.py").is_file()
    # En minimal no se debe generar engines.py
    assert not (pkg_dir / "engines.py").exists()

    plugin_text = (pkg_dir / "plugin.py").read_text(encoding="utf-8")
    assert "return {}" in plugin_text


def test_generate_full_scaffold(tmp_path: Path):
    """Verifica la plantilla full con Observer, Planner y Verifier."""
    target_dir = tmp_path / "jg_plugin_full"
    generate_plugin_scaffold(
        name="full",
        target_dir=target_dir,
        template="full",
    )

    pkg_dir = target_dir / "jg_plugin_full"
    assert (pkg_dir / "engines.py").is_file()

    engines_text = (pkg_dir / "engines.py").read_text(encoding="utf-8")
    assert "ObserverEngine" in engines_text
    assert "PlannerEngine" in engines_text
    assert "VerifierEngine" in engines_text


def test_generate_rejects_existing_directory_without_force(tmp_path: Path):
    """Verifica que se lance FileExistsError si el directorio ya existe y no está vacío."""
    target_dir = tmp_path / "my_plugin"
    target_dir.mkdir()
    (target_dir / "existing_file.txt").write_text("dummy", encoding="utf-8")

    with pytest.raises(FileExistsError, match="ya existe y no está vacío"):
        generate_plugin_scaffold(name="my_plugin", target_dir=target_dir, force=False)

    # Con force=True debe sobrescribir sin error
    created = generate_plugin_scaffold(name="my_plugin", target_dir=target_dir, force=True)
    assert created == target_dir
    assert (target_dir / "pyproject.toml").is_file()


def test_generate_rejects_invalid_template(tmp_path: Path):
    """Verifica que plantillas inexistentes arrojen ValueError."""
    with pytest.raises(ValueError, match="Plantilla desconocida 'invalid'"):
        generate_plugin_scaffold(name="my_plugin", target_dir=tmp_path / "p", template="invalid")


def test_main_cli_execution(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """Prueba la ejecución de la función main() con init directo y con plugin init."""
    dest1 = tmp_path / "cli_generated_plugin_1"
    ret1 = main(["init", "network_monitor", "--path", str(dest1), "--template", "standard"])
    assert ret1 == 0
    assert (dest1 / "pyproject.toml").is_file()

    dest2 = tmp_path / "cli_generated_plugin_2"
    ret2 = main([
        "plugin",
        "init",
        "datosgob",
        "--author",
        "Javier Gálvez",
        "--desc",
        "Buscador de datos abiertos",
        "-p",
        str(dest2),
    ])
    assert ret2 == 0
    assert (dest2 / "pyproject.toml").is_file()
    assert (dest2 / "install.sh").is_file()
    pyproj = (dest2 / "pyproject.toml").read_text(encoding="utf-8")
    assert "Javier Gálvez" in pyproj
    assert "Buscador de datos abiertos" in pyproj

    captured = capsys.readouterr()
    assert "Plugin inicializado con éxito" in captured.out


def test_main_cli_help_and_version(capsys: pytest.CaptureFixture[str]):
    """Prueba que --help e invocación sin comandos muestren ayuda."""
    ret = main([])
    assert ret == 0
    captured = capsys.readouterr()
    assert "usage: jg-sdk" in captured.out

    ret_plugin = main(["plugin"])
    assert ret_plugin == 0
    captured_plugin = capsys.readouterr()
    assert "usage: jg-sdk plugin" in captured_plugin.out

