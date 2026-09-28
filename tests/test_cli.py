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
    assert 'name="observability_inspect"' in tools_text
    assert 'name="observability_action"' in tools_text
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
    ret2 = main(
        [
            "plugin",
            "init",
            "datosgob",
            "--author",
            "Javier Gálvez",
            "--desc",
            "Buscador de datos abiertos",
            "-p",
            str(dest2),
        ]
    )
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
    assert "usage: jg" in captured.out

    ret_plugin = main(["plugin"])
    assert ret_plugin == 0
    captured_plugin = capsys.readouterr()
    assert "usage: jg" in captured_plugin.out


def test_main_cli_dev_and_run_help(capsys: pytest.CaptureFixture[str]):
    """Prueba que los subcomandos dev y run respondan a --help."""
    with pytest.raises(SystemExit) as exc_dev:
        main(["dev", "--help"])
    assert exc_dev.value.code == 0
    captured_dev = capsys.readouterr()
    assert "dev" in captured_dev.out

    with pytest.raises(SystemExit) as exc_run:
        main(["run", "--help"])
    assert exc_run.value.code == 0
    captured_run = capsys.readouterr()
    assert "run" in captured_run.out


def test_cli_run_without_compose(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    """Verifica que run informe error si no existe docker-compose.yml."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    monkeypatch.chdir(empty_dir)

    ret = main(["run"])
    assert ret == 1
    captured = capsys.readouterr()
    assert "No se encontró 'docker-compose.yml'" in captured.err


def test_main_cli_new_commands_help(capsys: pytest.CaptureFixture[str]):
    """Prueba que los subcomandos reload, status y test respondan a --help."""
    for cmd in ["reload", "status", "test"]:
        with pytest.raises(SystemExit) as exc:
            main([cmd, "--help"])
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert cmd in captured.out


def test_cli_status_execution(capsys: pytest.CaptureFixture[str]):
    """Verifica que status se ejecute sin excepciones capturando estado de red."""
    ret = main(["status"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Estado de Servicios y Runtimes" in captured.out


def test_scaffold_does_not_leak_api_key_in_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    """Verifica SDK-SEC-01: El .env generado no debe contener claves de API reales del entorno."""
    real_secret_key = "gsk_super_secret_production_key_123456789"
    monkeypatch.setenv("GROQ_API_KEY", real_secret_key)
    monkeypatch.setenv("GLOBAL_GROQ_API_KEY", real_secret_key)

    target_dir = tmp_path / "jg_plugin_secure"
    created = generate_plugin_scaffold(
        name="secure",
        target_dir=target_dir,
    )

    assert created == target_dir
    env_path = target_dir / ".env"
    assert env_path.is_file()

    env_content = env_path.read_text(encoding="utf-8")
    assert real_secret_key not in env_content
    assert "GROQ_API_KEY=" in env_content

    for line in env_content.splitlines():
        if line.startswith("GROQ_API_KEY="):
            assert line.strip() == "GROQ_API_KEY="
        if line.startswith("GLOBAL_GROQ_API_KEY="):
            assert line.strip() == "GLOBAL_GROQ_API_KEY="

    captured = capsys.readouterr()
    assert (
        "Se detectó GROQ_API_KEY en el entorno, pero por seguridad NO se incluirá" in captured.out
    )


def test_scaffold_does_not_traverse_parent_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    """Verifica SDK-SEC-04: El scaffold no debe subir por árboles de directorios padre buscando .env."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GLOBAL_GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    # Simular estructura de monorepo con .env en la raíz
    monorepo_root = tmp_path / "monorepo"
    monorepo_root.mkdir()
    parent_env = monorepo_root / ".env"
    parent_env.write_text(
        "GROQ_API_KEY=gsk_parent_monorepo_secret_999\nLLM_MODEL=parent/custom-model\n",
        encoding="utf-8",
    )

    nested_target_dir = monorepo_root / "packages" / "plugins" / "my_plugin"
    created = generate_plugin_scaffold(
        name="my_plugin",
        target_dir=nested_target_dir,
    )

    assert created == nested_target_dir
    generated_env = (nested_target_dir / ".env").read_text(encoding="utf-8")

    # No debe haber filtrado la clave del padre
    assert "gsk_parent_monorepo_secret_999" not in generated_env
    # No debe haber adoptado el modelo del .env del padre
    assert "parent/custom-model" not in generated_env
    assert "openai/gpt-oss-120b" in generated_env


def test_scaffold_docker_compose_security_warnings(tmp_path: Path):
    """Verifica SDK-SEC-02: docker-compose.yml incluye advertencias de seguridad para credenciales por defecto."""
    target_dir = tmp_path / "jg_plugin_sec02"
    generate_plugin_scaffold(name="sec02", target_dir=target_dir)

    compose_path = target_dir / "docker-compose.yml"
    assert compose_path.is_file()
    compose_text = compose_path.read_text(encoding="utf-8")

    assert "ADVERTENCIA DE SEGURIDAD (SDK-SEC-02)" in compose_text
    assert (
        "Los valores por defecto a continuación son ÚNICAMENTE para desarrollo local"
        in compose_text
    )


def test_cli_run_prints_security_warning_banner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    """Verifica SDK-SEC-02: jg run imprime banner de advertencia sobre credenciales de desarrollo."""
    import subprocess

    dummy_compose = tmp_path / "docker-compose.yml"
    dummy_compose.write_text("services: {}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    # Simular ejecución exitosa de docker compose
    def fake_subprocess_run(cmd, *args, **kwargs):
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_subprocess_run)

    ret = main(["run"])
    assert ret == 0

    captured = capsys.readouterr()
    assert "Stack iniciado con credenciales de DESARROLLO" in captured.out
    assert "Configura el .env antes de desplegar en producción" in captured.out


def test_cli_dev_help_documents_arbitrary_commands(capsys: pytest.CaptureFixture[str]):
    """Verifica SDK-CLI-01: El subcomando dev documenta explícitamente la ejecución de comandos arbitrarios."""
    with pytest.raises(SystemExit) as exc:
        main(["dev", "--help"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "Ejecuta un comando arbitrario en el entorno virtual" in captured.out
    assert "jg dev pytest" in captured.out
    assert "jg dev ruff check ." in captured.out


def test_scaffold_readme_documents_run_lifecycle_cleanup(tmp_path: Path):
    """Verifica SDK-SEC-03: El README generado documenta el ciclo de vida de jg run y la limpieza de agentes."""
    target_dir = tmp_path / "jg_plugin_sec03"
    generate_plugin_scaffold(name="sec03", target_dir=target_dir)

    readme_path = target_dir / "README.md"
    assert readme_path.is_file()
    readme_text = readme_path.read_text(encoding="utf-8")

    assert "Ciclo de Vida de `jg run`" in readme_text
    assert "limpieza preventiva en la base de datos del Dashboard" in readme_text
    assert "a0000000-0000-0000-0000-000000000002" in readme_text
