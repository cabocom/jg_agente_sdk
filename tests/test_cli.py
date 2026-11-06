# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

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
    real_secret_key = "mock_super_secret_production_key_123456789"
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


def test_scaffold_env_does_not_inject_real_api_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifica SDK-TEST-01: El scaffold no inyecta claves API reales en .env bajo ninguna circunstancia."""
    real_api_key = "mock-test-real-key-12345"
    monkeypatch.setenv("GROQ_API_KEY", real_api_key)
    monkeypatch.setenv("GLOBAL_GROQ_API_KEY", real_api_key)

    target_dir = tmp_path / "my_plugin"
    generate_plugin_scaffold(name="my_plugin", target_dir=target_dir)

    env_content = (target_dir / ".env").read_text(encoding="utf-8")
    assert real_api_key not in env_content
    assert "GROQ_API_KEY=" in env_content


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
        "GROQ_API_KEY=mock_parent_monorepo_secret_999\nLLM_MODEL=parent/custom-model\n",
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
    assert "mock_parent_monorepo_secret_999" not in generated_env
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


def test_link_plugin_creates_relative_symlink(tmp_path: Path):
    """Verifica que link_plugin cree un enlace simbólico relativo portable."""
    from jg_sdk.cli import link_plugin, unlink_plugin

    plugins_src = tmp_path / "plugins_src" / "jg_plugin_demo"
    pkg_dir = plugins_src / "jg_plugin_demo"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    (pkg_dir / "plugin.py").write_text(
        "class DemoPlugin:\n    pass\nPLUGIN_CLASS = DemoPlugin\n", encoding="utf-8"
    )

    agent_plugins = tmp_path / "agent" / "plugins"
    agent_plugins.mkdir(parents=True)

    code, msg = link_plugin(plugins_src, target_dir=agent_plugins)
    assert code == 0
    assert "enlazado con éxito" in msg

    link_target = agent_plugins / "jg_plugin_demo"
    assert link_target.is_symlink()
    assert link_target.resolve() == pkg_dir.resolve()

    # Desvincular
    code_u, msg_u = unlink_plugin("jg_plugin_demo", target_dir=agent_plugins)
    assert code_u == 0
    assert "desvinculado con éxito" in msg_u
    assert not link_target.exists()
    assert pkg_dir.exists()


def test_link_plugin_detects_engine_conflict(tmp_path: Path):
    """Verifica que link_plugin detecte colisión de motores cognitivos exclusivos."""
    from jg_sdk.cli import link_plugin

    agent_plugins = tmp_path / "agent" / "plugins"
    agent_plugins.mkdir(parents=True)

    # 1. Plugin existente con PlannerEngine
    p1 = agent_plugins / "jg_plugin_p1"
    p1.mkdir()
    (p1 / "plugin.py").write_text("class PlannerEngine:\n    pass\n", encoding="utf-8")

    # 2. Plugin nuevo que también define PlannerEngine
    p2 = tmp_path / "src" / "jg_plugin_p2"
    p2_pkg = p2 / "jg_plugin_p2"
    p2_pkg.mkdir(parents=True)
    (p2_pkg / "plugin.py").write_text("class PlannerEngine:\n    pass\n", encoding="utf-8")

    # Sin force: debe abortar con código 2
    code, msg = link_plugin(p2, target_dir=agent_plugins, force=False)
    assert code == 2
    assert "Conflicto de Motores Cognitivos Detectado" in msg

    # Con force: debe permitirlo
    code_f, msg_f = link_plugin(p2, target_dir=agent_plugins, force=True)
    assert code_f == 0
    assert "enlazado con éxito" in msg_f


def test_link_plugin_detects_security_trust_gap(tmp_path: Path):
    """Verifica que link_plugin alerte sobre mezcla de privilegios Docker y red externa."""
    from jg_sdk.cli import link_plugin

    agent_plugins = tmp_path / "agent" / "plugins"
    agent_plugins.mkdir(parents=True)

    # 1. Plugin DevOps privilegiado (socket docker)
    p_devops = agent_plugins / "jg_plugin_devops"
    p_devops.mkdir()
    (p_devops / "plugin.py").write_text(
        "DOCKER_HOST = 'tcp://...'\ndef docker_restart(): pass\n", encoding="utf-8"
    )

    # 2. Plugin conversacional con red abierta (httpx, weather)
    p_conv = tmp_path / "src" / "jg_plugin_conversational"
    p_conv_pkg = p_conv / "jg_plugin_conversational"
    p_conv_pkg.mkdir(parents=True)
    (p_conv_pkg / "plugin.py").write_text(
        "import httpx\ndef get_weather(): pass\n", encoding="utf-8"
    )

    # Sin force: debe abortar con alerta de seguridad (código 3)
    code, msg = link_plugin(p_conv, target_dir=agent_plugins, force=False)
    assert code == 3
    assert "ALERTA DE SEGURIDAD" in msg
    assert "Principio de Mínimo Privilegio" in msg

    # Con force: debe proceder
    code_f, msg_f = link_plugin(p_conv, target_dir=agent_plugins, force=True)
    assert code_f == 0
    assert "enlazado con éxito" in msg_f


def test_unlink_plugin_protects_real_directories(tmp_path: Path):
    """Verifica que unlink_plugin no elimine carpetas reales para no destruir código."""
    from jg_sdk.cli import unlink_plugin

    agent_plugins = tmp_path / "agent" / "plugins"
    agent_plugins.mkdir(parents=True)

    real_folder = agent_plugins / "jg_plugin_real"
    real_folder.mkdir()
    (real_folder / "plugin.py").write_text("print('hello')", encoding="utf-8")

    code, msg = unlink_plugin("jg_plugin_real", target_dir=agent_plugins)
    assert code == 1
    assert "es un directorio real y no un enlace simbólico" in msg
    assert real_folder.exists()


def test_cli_main_link_and_unlink(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """Verifica la invocación mediante main(['link', ...]) y main(['unlink', ...])."""
    plugins_src = tmp_path / "my_plugin"
    pkg = plugins_src / "my_plugin"
    pkg.mkdir(parents=True)
    (pkg / "plugin.py").write_text("class MyPlugin: pass", encoding="utf-8")

    agent_plugins = tmp_path / "agent" / "plugins"
    agent_plugins.mkdir(parents=True)

    # jg link
    ret_link = main(["link", str(plugins_src), "-t", str(agent_plugins)])
    assert ret_link == 0
    captured_link = capsys.readouterr()
    assert "enlazado con éxito" in captured_link.out

    # jg unlink
    ret_unlink = main(["unlink", "my_plugin", "-t", str(agent_plugins)])
    assert ret_unlink == 0
    captured_unlink = capsys.readouterr()
    assert "desvinculado con éxito" in captured_unlink.out


def test_cli_main_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    """Verifica que 'jg build' y 'jg plugin build' ejecuten docker build correctamente."""
    import subprocess
    from unittest.mock import MagicMock

    plugin_dir = tmp_path / "jg_plugin_test"
    plugin_dir.mkdir()
    (plugin_dir / "pyproject.toml").write_text('name = "jg_plugin_test"\n', encoding="utf-8")
    pkg = plugin_dir / "jg_plugin_test"
    pkg.mkdir()
    (pkg / "plugin.py").write_text("class TestPlugin: pass\n", encoding="utf-8")

    mock_run = MagicMock()
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
    monkeypatch.setattr(subprocess, "run", mock_run)

    # 1. Probar 'jg plugin build'
    ret_plugin_build = main(
        [
            "plugin",
            "build",
            str(plugin_dir),
            "--tag",
            "registry.gitlab.com/javiergalvez-ia/jg_plugin_test:v1.0.0",
            "--push",
        ]
    )
    assert ret_plugin_build == 0
    assert mock_run.call_count >= 2  # docker build + docker push

    # Validar argumentos del comando build
    build_call = mock_run.call_args_list[0]
    assert "docker" in build_call[0][0]
    assert "build" in build_call[0][0]
    assert "registry.gitlab.com/javiergalvez-ia/jg_plugin_test:v1.0.0" in build_call[0][0]

    # 2. Probar alias 'jg build'
    mock_run.reset_mock()
    ret_build = main(
        [
            "build",
            str(plugin_dir),
            "--tag",
            "registry.gitlab.com/javiergalvez-ia/jg_plugin_test:latest",
        ]
    )
    assert ret_build == 0
    assert mock_run.call_count == 1
    build_args = mock_run.call_args_list[0][0][0]
    assert "build" in build_args
    assert "registry.gitlab.com/javiergalvez-ia/jg_plugin_test:latest" in build_args


def test_cli_clean_and_contextual_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    """Verifica el ciclo de vida de 'jg status' contextual y 'jg clean'."""
    import subprocess
    from unittest.mock import MagicMock

    # Crear plugin de prueba
    plugin_dir = tmp_path / "jg_plugin_mockclean"
    plugin_dir.mkdir()
    (plugin_dir / "pyproject.toml").write_text(
        '[project]\nname = "jg-plugin-mockclean"\n[project.entry-points."jg_agente.plugins"]\nmockclean = "jg_plugin_mockclean.plugin:MockPlugin"\n',
        encoding="utf-8",
    )
    pkg = plugin_dir / "jg_plugin_mockclean"
    pkg.mkdir()
    (pkg / "plugin.py").write_text("class MockPlugin: pass\n", encoding="utf-8")
    (plugin_dir / "docker-compose.yml").write_text(
        "services:\n  test:\n    image: alpine\n", encoding="utf-8"
    )

    # Crear cachés temporales y venv ficticio
    cache_dir = plugin_dir / "__pycache__"
    cache_dir.mkdir()
    (cache_dir / "mock.pyc").write_text("dummy", encoding="utf-8")
    venv_dir = plugin_dir / ".venv"
    venv_dir.mkdir()
    (venv_dir / "pyvenv.cfg").write_text("home = /usr", encoding="utf-8")

    agent_plugins = tmp_path / "agent" / "plugins"
    agent_plugins.mkdir(parents=True)
    symlink_dest = agent_plugins / "jg_plugin_mockclean"
    symlink_dest.symlink_to(pkg, target_is_directory=True)

    # 1. Probar status contextual dentro del plugin
    monkeypatch.chdir(plugin_dir)
    ret_status = main(["status", "-t", str(agent_plugins)])
    assert ret_status == 0
    captured_status = capsys.readouterr()
    assert "Estado del Plugin: jg_plugin_mockclean" in captured_status.out
    assert "Modo Arquitectónico:   Autónomo" in captured_status.out
    assert "Enlace en jg_agente:    ACTIVO" in captured_status.out

    # 2. Probar clean con mock de subprocess para docker compose down y docker rm
    mock_run = MagicMock()
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    monkeypatch.setattr(subprocess, "run", mock_run)

    ret_clean = main(["clean", "--all", "-t", str(agent_plugins)])
    assert ret_clean == 0
    captured_clean = capsys.readouterr()
    assert "Limpieza de Recursos y Enlaces: jg_plugin_mockclean" in captured_clean.out
    assert "desvinculado con éxito" in captured_clean.out
    assert "Cachés temporales purgadas" in captured_clean.out
    assert "Entorno virtual .venv eliminado" in captured_clean.out
    assert not symlink_dest.exists()
    assert not venv_dir.exists()
    assert not cache_dir.exists()

    # 3. Tras clean, status debe indicar ESTADO LIMPIO
    ret_status_after = main(["status", "-t", str(agent_plugins)])
    assert ret_status_after == 0
    captured_status_after = capsys.readouterr()
    assert "ESTADO LIMPIO" in captured_status_after.out
