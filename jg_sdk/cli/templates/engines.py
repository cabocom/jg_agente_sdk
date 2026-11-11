# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Plantilla de generación de código para engines.py."""

from __future__ import annotations


def get_engines_template(template: str, pkg_name: str, class_prefix: str, raw_slug: str) -> str:
    """Genera el código de engines.py."""
    if template == "standard":
        return f'''"""Motores cognitivos para {pkg_name}."""

from jg_sdk import ObserverEngine


class {class_prefix}Observer(ObserverEngine):
    """Motor de observación de telemetría e incidentes."""

    @property
    def name(self) -> str:
        return "{raw_slug}_observer"

    async def observe(self, state: dict | None = None) -> dict:
        return {{
            "component": "{raw_slug}",
            "status": "operational",
            "telemetry": {{"uptime": 3600, "healthy": True}},
        }}
'''
    elif template == "full":
        return f'''"""Motores cognitivos avanzados para {pkg_name}."""

from jg_sdk import ObserverEngine, PlannerEngine, VerifierEngine


class {class_prefix}Observer(ObserverEngine):
    """Motor de observación para recolectar telemetría."""

    @property
    def name(self) -> str:
        return "{raw_slug}_observer"

    async def observe(self, state: dict | None = None) -> dict:
        return {{
            "component": "{raw_slug}",
            "status": "operational",
            "incidents": [],
        }}


class {class_prefix}Planner(PlannerEngine):
    """Motor de formulación de planes de ejecución."""

    @property
    def name(self) -> str:
        return "{raw_slug}_planner"

    async def plan(self, intent: str, state: dict | None = None) -> list[dict]:
        return [
            {{
                "step": 1,
                "tool": "{raw_slug}_telemetry",
                "args": {{"metric": "system_health"}},
                "description": "Inspección previa",
            }}
        ]


class {class_prefix}Verifier(VerifierEngine):
    """Motor de verificación activa de resultados."""

    @property
    def name(self) -> str:
        return "{raw_slug}_verifier"

    async def verify(self, state: dict | None = None) -> dict:
        return {{
            "resolved": True,
            "verification_status": "PASS",
            "details": "Estado verificado satisfactoriamente.",
        }}
'''
    return ""
