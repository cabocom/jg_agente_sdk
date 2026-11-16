# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Módulo de seguridad unificado y políticas de red para jg_sdk."""

from jg_sdk.security.ssrf import (
    DEFAULT_ALLOWED_SCHEMES,
    DEFAULT_BLOCKED_HOSTNAMES,
    DEFAULT_BLOCKED_NETWORKS,
    RFC1918_NETWORKS,
    SSRFValidationError,
    SSRFValidator,
)

__all__ = [
    "DEFAULT_ALLOWED_SCHEMES",
    "DEFAULT_BLOCKED_HOSTNAMES",
    "DEFAULT_BLOCKED_NETWORKS",
    "RFC1918_NETWORKS",
    "SSRFValidationError",
    "SSRFValidator",
]
