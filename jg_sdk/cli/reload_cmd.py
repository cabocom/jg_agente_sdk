# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Subcomando 'reload' para recargar plugins en caliente en los agentes."""

from __future__ import annotations

import argparse
import subprocess
import time

import httpx


def _reload_agent(a_container: str, a_port: int, a_name: str) -> None:
    """Reinicia un agente cognitivo específico y verifica su salud."""
    print(f"\n▶ [{a_name}] ({a_container})")
    res = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
    )
    if a_container not in res.stdout.splitlines():
        print(f"   ⚠️  Contenedor '{a_container}' no está en ejecución. Omitiendo.")
        return

    print("   🔄 Reiniciando runtime...")
    restart_res = subprocess.run(["docker", "restart", a_container], capture_output=True)
    if restart_res.returncode != 0:
        print(f"   ❌ Error al reiniciar contenedor '{a_container}'.")
        return

    print(f"   ⏳ Verificando salud en http://localhost:{a_port}/health...")
    healthy = False
    start_t = time.time()
    for _ in range(25):
        try:
            r = httpx.get(f"http://localhost:{a_port}/health", timeout=2.0)
            if r.status_code == 200:
                healthy = True
                break
        except Exception:
            pass
        time.sleep(1)

    elapsed = round(time.time() - start_t, 1)
    if not healthy:
        print("   ❌ El agente no respondió saludable tras 25s.")
        return

    print(f"   ✓ Agente saludable y operativo ({elapsed}s)")
    try:
        r = httpx.get(f"http://localhost:{a_port}/capabilities", timeout=3.0)
        if r.status_code == 200:
            data = r.json()
            plugins = [
                p.get("name", "") + " (v" + p.get("version", "?") + ")"
                for p in data.get("plugins", [])
            ]
            tools = [
                t.get("name", "") + " [" + t.get("risk_level", "low") + "]"
                for t in data.get("tools", [])
            ]
            print(
                f"   📦 Plugins activos  ({data.get('plugins_count', 0)}): {', '.join(plugins) if plugins else 'Ninguno'}"
            )
            print(
                f"   🛠️  Herramientas    ({data.get('tools_count', 0)}): {', '.join(tools) if tools else 'Ninguna'}"
            )
    except Exception:
        pass
    print("   ✨ Plugins sincronizados con éxito.")


def handle_reload(args: argparse.Namespace) -> int:
    """Recarga de forma inmediata los plugins de los agentes en ejecución."""
    target = getattr(args, "target", "all") or "all"
    target = target.lower()

    agents_map = [
        ("conversacional", "jg_agente_conversacional", 8001, "Agente Conversacional"),
        ("devops", "jg_agente_devops", 8002, "Agente DevOps"),
        ("datosgob", "jg_agente_datosgob", 8881, "Agente Datos Gob"),
    ]

    print("=" * 65)
    print("🔌 Recargando plugins de agentes cognitivos...")
    print("=" * 65)

    matched = False
    for a_key, a_container, a_port, a_name in agents_map:
        if target in ("all", a_key):
            matched = True
            _reload_agent(a_container, a_port, a_name)

    if not matched:
        print(
            f"❌ Objetivo desconocido: '{target}'. Opciones válidas: all, conversacional, devops, datosgob"
        )
        return 1

    print("\n" + "=" * 65)
    print("🎉 Recarga de plugins completada satisfactoriamente")
    print("=" * 65)
    return 0
