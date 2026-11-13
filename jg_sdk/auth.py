# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Utilidades criptográficas HMAC-SHA256 y excepciones del cliente HTTP."""

import hashlib
import hmac
import time
from typing import Any
from urllib.parse import urlparse

# Ventana de tolerancia temporal anti-repetición (5 minutos)
DEFAULT_MAX_TIMESTAMP_SKEW_SECONDS = 300


# =====================================================================
# 1. Utilidades Criptográficas HMAC-SHA256
# =====================================================================


def compute_body_sha256(body_bytes: bytes | None) -> str:
    """Calcula el hash SHA-256 en hexadecimal del cuerpo crudo de la petición.

    Para cuerpos vacíos o None, devuelve el hash estándar de b"".
    """
    data = body_bytes or b""
    return hashlib.sha256(data).hexdigest()


def compute_canonical_string(
    method: str,
    path: str,
    timestamp: str | int,
    body_bytes: bytes | None,
) -> str:
    """Construye la cadena canónica normalizada para la firma HMAC-SHA256.

    Formato:
        METHOD\\nPATH\\nTIMESTAMP\\nBODY_SHA256
    """
    norm_method = method.strip().upper()
    # Si viene una URL completa, extraemos sólo el path
    parsed = urlparse(path)
    norm_path = parsed.path if parsed.path else path.strip()
    norm_timestamp = str(timestamp).strip()
    body_hash = compute_body_sha256(body_bytes)

    return f"{norm_method}\n{norm_path}\n{norm_timestamp}\n{body_hash}"


def compute_hmac_signature(secret: str, canonical_string: str) -> str:
    """Calcula la firma HMAC-SHA256 en formato hexadecimal."""
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=canonical_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


def verify_hmac_signature(secret: str, canonical_string: str, received_signature: str) -> bool:
    """Compara en tiempo constante la firma recibida con la firma esperada."""
    expected_signature = compute_hmac_signature(secret, canonical_string)
    return hmac.compare_digest(expected_signature.lower(), received_signature.strip().lower())


def verify_request_signature(
    secret: str,
    method: str,
    path: str,
    timestamp: str | int,
    body_bytes: bytes | None,
    received_signature: str,
    max_skew_seconds: int = DEFAULT_MAX_TIMESTAMP_SKEW_SECONDS,
) -> bool:
    """Verifica la validez de una firma HTTP comprobando también la ventana anti-replay.

    Args:
        secret: Secreto simétrico compartido.
        method: Verbo HTTP (GET, POST, etc.).
        path: Ruta URL de la petición.
        timestamp: Timestamp UNIX epoch enviado en cabecera.
        body_bytes: Cuerpo crudo de la petición.
        received_signature: Firma HMAC enviada en X-Signature.
        max_skew_seconds: Tolerancia máxima en segundos contra replay attacks.

    Returns:
        True si la firma es válida y el timestamp está dentro de la ventana de tolerancia.
    """
    try:
        ts_int = int(str(timestamp).strip())
    except ValueError:
        return False

    current_time = int(time.time())
    if abs(current_time - ts_int) > max_skew_seconds:
        return False

    canonical = compute_canonical_string(method, path, ts_int, body_bytes)
    return verify_hmac_signature(secret, canonical, received_signature)


# =====================================================================
# 2. Excepciones del Cliente
# =====================================================================


class AgentClientError(Exception):
    """Excepción base para errores del cliente HTTP de jg_agente."""


class AgentAuthError(AgentClientError):
    """Error de autenticación o rechazo de firma HMAC por parte del agente."""


class AgentResponseError(AgentClientError):
    """Respuesta con código de error HTTP emitida por el agente."""

    def __init__(self, status_code: int, detail: str, body: Any = None) -> None:
        super().__init__(f"HTTP {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail
        self.body = body


__all__ = [
    "DEFAULT_MAX_TIMESTAMP_SKEW_SECONDS",
    "AgentAuthError",
    "AgentClientError",
    "AgentResponseError",
    "compute_body_sha256",
    "compute_canonical_string",
    "compute_hmac_signature",
    "verify_hmac_signature",
    "verify_request_signature",
]
