# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Módulo unificado de mitigación SSRF, resolución DNS y fijado de IP (DNS Pinning)."""

import asyncio
import ipaddress
import logging
import socket
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger("jg_sdk.security.ssrf")


class SSRFValidationError(ValueError):
    """Excepción lanzada cuando una URL, IP o destino vulnera la política SSRF."""

    def __init__(self, message: str, target: str | None = None) -> None:
        super().__init__(message)
        self.target = target


# fmt: off
DEFAULT_BLOCKED_NETWORKS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    ipaddress.ip_network("127.0.0.0/8"), ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("10.0.0.0/8"), ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"), ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"), ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"), ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"), ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"), ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("255.255.255.255/32"), ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("::/128"), ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("fc00::/7"), ipaddress.ip_network("ff00::/8"),
    ipaddress.ip_network("2001:db8::/32"),
]

DEFAULT_BLOCKED_HOSTNAMES: set[str] = {
    "localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback",
    "metadata.google.internal", "metadata", "instance-data",
}
# fmt: on

DEFAULT_ALLOWED_SCHEMES: set[str] = {"http", "https"}

RFC1918_NETWORKS: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...] = tuple(
    ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7")
)


def _build_pinned_info(parsed: Any, hostname: str, chosen_ip: str) -> dict[str, Any]:
    """Construye metadatos de conexión fijada por DNS Pinning."""
    scheme = (parsed.scheme or "http").lower()
    port = parsed.port or (443 if scheme == "https" else 80)
    std_port = (scheme == "https" and port == 443) or (scheme == "http" and port == 80)
    host_header = hostname if std_port else f"{hostname}:{port}"

    ip_obj = ipaddress.ip_address(chosen_ip)
    ip_host = f"[{chosen_ip}]" if ip_obj.version == 6 else chosen_ip
    netloc = f"{ip_host}:{parsed.port}" if parsed.port else ip_host
    pinned_url = urlunparse(
        (parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
    )

    return {
        "hostname": hostname,
        "pinned_ip": chosen_ip,
        "port": port,
        "scheme": scheme,
        "pinned_url": pinned_url,
        "host_header": host_header,
        "headers": {"Host": host_header},
        "dns_pin_map": {hostname.lower(): chosen_ip},
    }


class SSRFValidator:
    """Validador central de destinos de red contra ataques SSRF y DNS Rebinding."""

    def __init__(
        self,
        allowed_hosts: Sequence[str] | None = None,
        allowed_networks: Sequence[str | ipaddress.IPv4Network | ipaddress.IPv6Network]
        | None = None,
        allow_private_networks: bool = False,
        enforce: bool = True,
    ) -> None:
        self.allowed_hosts: set[str] = {
            h.lower().strip() for h in (allowed_hosts or []) if h.strip()
        }
        self.allowed_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        for net in allowed_networks or []:
            if isinstance(net, (ipaddress.IPv4Network, ipaddress.IPv6Network)):
                self.allowed_networks.append(net)
            elif isinstance(net, str) and net.strip():
                self.allowed_networks.append(ipaddress.ip_network(net.strip(), strict=False))
        self.allow_private_networks = allow_private_networks
        self.enforce = enforce

    def _is_ip_allowed_explicitly(self, ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """Comprueba si una dirección IP se encuentra en los rangos CIDR autorizados."""
        return any(ip in net for net in self.allowed_networks)

    is_ip_allowed_explicitly = _is_ip_allowed_explicitly

    def is_ip_blocked(
        self, ip: ipaddress.IPv4Address | ipaddress.IPv6Address
    ) -> tuple[bool, str | None]:
        """Verifica si una IP está en rangos no autorizados."""
        mapped = getattr(ip, "ipv4_mapped", None)
        if mapped is not None:
            blocked, reason = self.is_ip_blocked(mapped)
            return (True, f"{reason} (IPv4 mapeada: {ip})") if blocked else (False, None)

        if self._is_ip_allowed_explicitly(ip):
            return False, None

        for blocked_net in DEFAULT_BLOCKED_NETWORKS:
            if ip in blocked_net:
                if self.allow_private_networks and blocked_net in RFC1918_NETWORKS:
                    continue
                return True, f"IP {ip} bloqueada por pertenecer a rango restringido {blocked_net}"

        return False, None

    def validate_ip(self, ip_str: str) -> tuple[bool, str | None]:
        """Valida una dirección IP representada como texto."""
        if not self.enforce:
            return True, None
        try:
            ip_obj = ipaddress.ip_address(ip_str.strip())
            blocked, reason = self.is_ip_blocked(ip_obj)
            return (False, reason) if blocked else (True, None)
        except ValueError:
            return False, f"Dirección IP no válida: '{ip_str}'"

    def is_host_allowed_explicitly(self, hostname: str) -> bool:
        """Verifica si el hostname o un sufijo de dominio está en la allowlist."""
        host_lower = hostname.lower().strip()
        if host_lower in self.allowed_hosts:
            return True
        for allowed in self.allowed_hosts:
            if allowed.startswith(".") and host_lower.endswith(allowed):
                return True
            if allowed.startswith("*.") and host_lower.endswith(allowed[1:]):
                return True
        return False

    def resolve_host(self, hostname: str, port: int = 80) -> list[str]:
        """Resuelve el hostname a direcciones IP mediante DNS sincrónico."""
        try:
            addr_info = socket.getaddrinfo(hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
            return list(dict.fromkeys(str(item[4][0]) for item in addr_info if item and item[4]))
        except socket.gaierror as exc:
            raise SSRFValidationError(
                f"Fallo en resolución DNS para '{hostname}': {exc}", target=hostname
            ) from exc

    async def resolve_host_async(self, hostname: str, port: int = 80) -> list[str]:
        """Resuelve el hostname a direcciones IP de forma asíncrona."""
        return await asyncio.to_thread(self.resolve_host, hostname, port)

    def _pre_validate_url(self, url: str) -> tuple[bool, str | None, Any, str | None]:
        if not url or not isinstance(url, str):
            return False, "URL vacía o de tipo incorrecto", None, None
        parsed = urlparse(url.strip())
        scheme = (parsed.scheme or "").lower()
        if scheme not in DEFAULT_ALLOWED_SCHEMES:
            return (
                False,
                f"Esquema de protocolo no autorizado '{scheme}'. Permitidos: {DEFAULT_ALLOWED_SCHEMES}",
                None,
                None,
            )
        hostname = parsed.hostname
        if not hostname:
            return False, f"URL sin hostname válido: '{url}'", None, None
        if not self.enforce:
            return True, None, parsed, hostname
        if self.is_host_allowed_explicitly(hostname):
            return True, None, parsed, hostname
        if hostname.lower() in DEFAULT_BLOCKED_HOSTNAMES or any(
            hostname.lower().endswith(sfx) for sfx in (".local", ".internal", ".localhost")
        ):
            return False, f"Hostname '{hostname}' prohibido por política SSRF", None, None
        return True, None, parsed, hostname

    def validate_url(self, url: str, resolve_dns: bool = True) -> tuple[bool, str | None]:
        """Valida una URL comprobando esquema, hostname y resolución DNS."""
        ok, reason, parsed, hostname = self._pre_validate_url(url)
        if not ok or not hostname or not self.enforce:
            return ok, reason
        if self.is_host_allowed_explicitly(hostname):
            return True, None
        try:
            ip_obj = ipaddress.ip_address(hostname)
            blocked, reason = self.is_ip_blocked(ip_obj)
            return (False, reason) if blocked else (True, None)
        except ValueError:
            pass
        if not resolve_dns:
            return True, None
        try:
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            ips = self.resolve_host(hostname, port)
            for ip_str in ips:
                blocked, reason = self.is_ip_blocked(ipaddress.ip_address(ip_str))
                if blocked:
                    return False, f"Resolución DNS de '{hostname}' vulnera política: {reason}"
            return True, None
        except (SSRFValidationError, OSError) as exc:
            return False, str(exc)

    async def validate_url_async(
        self, url: str, resolve_dns: bool = True
    ) -> tuple[bool, str | None]:
        """Valida una URL de forma asíncrona."""
        return await asyncio.to_thread(self.validate_url, url, resolve_dns)

    def _handle_unforced_pin(
        self, parsed: Any, hostname: str
    ) -> tuple[bool, str | None, dict[str, Any] | None]:
        try:
            ip_obj = ipaddress.ip_address(hostname)
            chosen_ip = str(ip_obj)
        except ValueError:
            try:
                port = parsed.port or (443 if parsed.scheme == "https" else 80)
                ips = self.resolve_host(hostname, port)
                if not ips:
                    return False, f"No se obtuvieron direcciones IP para '{hostname}'", None
                chosen_ip = ips[0]
            except (SSRFValidationError, OSError) as exc:
                return False, f"Fallo en resolución DNS para '{hostname}': {exc}", None
        return True, None, _build_pinned_info(parsed, hostname, chosen_ip)

    def _resolve_and_check_dns(
        self, parsed: Any, hostname: str
    ) -> tuple[bool, str | None, dict[str, Any] | None]:
        try:
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            ips = self.resolve_host(hostname, port)
            if not ips:
                return False, f"No se obtuvieron direcciones IP para '{hostname}'", None
        except SSRFValidationError as exc:
            return False, str(exc), None
        except OSError as exc:
            return False, f"Fallo en resolución DNS para '{hostname}': {exc}", None

        for ip_str in ips:
            blocked, b_reason = self.is_ip_blocked(ipaddress.ip_address(ip_str))
            if blocked:
                return False, f"Resolución DNS '{hostname}' vulnera política: {b_reason}", None
        return True, None, _build_pinned_info(parsed, hostname, ips[0])

    def resolve_and_pin_url(self, url: str) -> tuple[bool, str | None, dict[str, Any] | None]:
        """Valida la URL y genera metadatos de fijado de IP para mitigar DNS Rebinding."""
        ok, reason, parsed, hostname = self._pre_validate_url(url)
        if not ok or not hostname or parsed is None:
            return False, reason, None
        if not self.enforce:
            return self._handle_unforced_pin(parsed, hostname)
        try:
            ip_obj = ipaddress.ip_address(hostname)
            blocked, b_reason = self.is_ip_blocked(ip_obj)
            if blocked:
                return False, b_reason, None
            return True, None, _build_pinned_info(parsed, hostname, str(ip_obj))
        except ValueError:
            pass
        return self._resolve_and_check_dns(parsed, hostname)

    async def resolve_and_pin_url_async(
        self, url: str
    ) -> tuple[bool, str | None, dict[str, Any] | None]:
        """Valida la URL y fija la IP asíncronamente."""
        return await asyncio.to_thread(self.resolve_and_pin_url, url)

    def assert_safe_url(self, url: str, resolve_dns: bool = True) -> None:
        """Lanza SSRFValidationError si la URL no es segura."""
        is_safe, reason = self.validate_url(url, resolve_dns=resolve_dns)
        if not is_safe:
            raise SSRFValidationError(reason or "Destino no permitido por SSRF", target=url)

    def _assert_safe_ip(self, ip_str: str) -> None:
        """Lanza SSRFValidationError si la dirección IP no es segura."""
        is_safe, reason = self.validate_ip(ip_str)
        if not is_safe:
            raise SSRFValidationError(reason or "Dirección IP no permitida por SSRF", target=ip_str)

    assert_safe_ip = _assert_safe_ip
