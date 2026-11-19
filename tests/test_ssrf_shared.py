# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Tests unitarios para el validador SSRF y DNS Pinning unificado."""

import socket
from unittest.mock import patch

import pytest

from jg_sdk.security.ssrf import (
    DEFAULT_BLOCKED_HOSTNAMES,
    SSRFValidationError,
    SSRFValidator,
)


@pytest.fixture
def validator() -> SSRFValidator:
    """Instancia del validador SSRF por defecto."""
    return SSRFValidator()


def test_scheme_validation(validator: SSRFValidator) -> None:
    """Verifica el filtrado estricto de esquemas URI."""
    with pytest.raises(SSRFValidationError, match="no autorizado"):
        validator.assert_safe_url("file:///etc/passwd")

    with pytest.raises(SSRFValidationError, match="no autorizado"):
        validator.assert_safe_url("ftp://example.com/file.txt")

    with pytest.raises(SSRFValidationError, match="no autorizado"):
        validator.assert_safe_url("gopher://127.0.0.1:70")


def test_blocked_hostnames(validator: SSRFValidator) -> None:
    """Verifica el bloqueo de hostnames conocidos."""
    for host in DEFAULT_BLOCKED_HOSTNAMES:
        with pytest.raises(SSRFValidationError, match="prohibido por política SSRF"):
            validator.assert_safe_url(f"http://{host}/api")


def test_blocked_ip_literals(validator: SSRFValidator) -> None:
    """Verifica el bloqueo de IPs privadas, loopback y metadata sin llamar a DNS."""
    blocked_ips = [
        "127.0.0.1",
        "127.0.0.2",
        "10.0.0.1",
        "172.16.0.5",
        "192.168.1.1",
        "169.254.169.254",
        "::1",
        "fe80::1",
    ]
    for ip in blocked_ips:
        with pytest.raises(
            SSRFValidationError, match="bloqueada por pertenecer a rango restringido"
        ):
            validator.assert_safe_ip(ip)

        with pytest.raises(
            SSRFValidationError, match="bloqueada por pertenecer a rango restringido"
        ):
            target_url = f"http://[{ip}]/metrics" if ":" in ip else f"http://{ip}/metrics"
            validator.assert_safe_url(target_url, resolve_dns=False)


@pytest.mark.asyncio
async def test_resolve_and_pin_public_host(validator: SSRFValidator) -> None:
    """Verifica resolución DNS exitosa y pinning a IP pública simulada."""
    fake_dns_result = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))]

    with patch("socket.getaddrinfo", return_value=fake_dns_result):
        ok, reason, pin_info = await validator.resolve_and_pin_url_async(
            "https://api.example.com/v1/resource?id=123"
        )

        assert ok is True
        assert reason is None
        assert pin_info is not None
        assert pin_info["pinned_url"] == "https://93.184.216.34/v1/resource?id=123"
        assert pin_info["headers"]["Host"] == "api.example.com"
        assert pin_info["dns_pin_map"]["api.example.com"] == "93.184.216.34"


@pytest.mark.asyncio
async def test_resolve_and_pin_rebinding_attack(validator: SSRFValidator) -> None:
    """Verifica detección de DNS Rebinding que resuelve a IP privada."""
    fake_dns_result = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))]

    with patch("socket.getaddrinfo", return_value=fake_dns_result):
        ok, reason, pin_info = await validator.resolve_and_pin_url_async(
            "https://attacker-dns-rebinding.com/v1"
        )
        assert ok is False
        assert reason is not None
        assert "bloqueada" in reason
        assert pin_info is None


def test_custom_allowed_networks() -> None:
    """Verifica que se pueden permitir redes específicas de forma controlada."""
    custom_val = SSRFValidator(allowed_networks=["10.0.0.0/24"])
    # 10.0.0.5 está explícitamente permitida
    ok, reason = custom_val.validate_ip("10.0.0.5")
    assert ok is True
    assert reason is None

    # 10.0.1.5 sigue bloqueada por RFC1918
    ok, reason = custom_val.validate_ip("10.0.1.5")
    assert ok is False
    assert reason is not None


def test_resolve_and_pin_enforce_false() -> None:
    """Verifica que enforce=False permite fijar URLs locales sin bloqueo."""
    val = SSRFValidator(enforce=False)
    ok, reason, pin_info = val.resolve_and_pin_url("http://127.0.0.1:8000/api")
    assert ok is True
    assert reason is None
    assert pin_info is not None
    assert pin_info["pinned_ip"] == "127.0.0.1"


def test_resolve_and_pin_nonexistent_host() -> None:
    """Verifica que un host inexistente devuelve ok=False sin lanzar excepción no capturada."""
    val = SSRFValidator(enforce=True)
    ok, reason, pin_info = val.resolve_and_pin_url("https://nonexistent.invalid/test")
    assert ok is False
    assert reason is not None
    assert "Fallo en resolución DNS" in reason or "gaierror" in reason
    assert pin_info is None


def test_resolve_and_pin_nonexistent_host_enforce_false() -> None:
    """Verifica que enforce=False ante fallo DNS devuelve ok=False sin inventar IP 127.0.0.1."""
    val = SSRFValidator(enforce=False)
    ok, reason, pin_info = val.resolve_and_pin_url("https://nonexistent.invalid/test")
    assert ok is False
    assert reason is not None
    assert "Fallo en resolución DNS" in reason or "gaierror" in reason
    assert pin_info is None
