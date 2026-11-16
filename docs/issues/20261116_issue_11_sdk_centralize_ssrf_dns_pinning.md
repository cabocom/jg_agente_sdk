# Issue 02: [jg_agente_sdk] Refactor: Centralización del módulo unificado de protección SSRF y DNS Pinning

- **Título:** `[jg_agente_sdk] Refactor: Centralización del módulo unificado de protección SSRF y DNS Pinning`
- **Prioridad y Fase:** Alta | Fase 0: Remediación Base
- **Dependencias:** Ninguna (Issue raíz de remediación)
- **Contexto Técnico y Archivos Afectados:**
  - Hallazgos del informe: `H-07` (`SSRFSafeAsyncBackend` depende de internals privados de `httpcore._backends.anyio`) y `H-08` (Múltiples plugins (`demoapi`, `aitoday`, `conversational`) duplican privadamente implementaciones completas de SSRF ante la ausencia de utilidades en el SDK).
  - Archivos a crear/modificar:
    - `jg_agente_sdk/jg_sdk/security/__init__.py` (Crear)
    - `jg_agente_sdk/jg_sdk/security/ssrf.py` (Crear)
    - `jg_agente_sdk/tests/test_ssrf_shared.py` (Crear)

---

## Especificación Técnica

### 1. `jg_sdk/security/ssrf.py`
- Extraer y estandarizar la política de IPs prohibidas:
  - Loopback (`127.0.0.0/8`, `::1/128`).
  - Metadatos Cloud (`169.254.0.0/16`, `fe80::/10`).
  - Rangos RFC 1918 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
  - Rangos IPv6 locales únicos (`fc00::/7`).
  - Carrier-grade NAT RFC 6598 (`100.64.0.0/10`) y test networks.
- Crear clase `SSRFValidator`:
  ```python
  class SSRFValidator:
      def __init__(
          self,
          allowed_hosts: Sequence[str] | None = None,
          allowed_networks: Sequence[str | ipaddress.IPv4Network | ipaddress.IPv6Network] | None = None,
          allow_private_networks: bool = False,
          enforce: bool = True,
      ) -> None: ...
      
      def is_ip_blocked(self, ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> tuple[bool, str | None]: ...
      async def validate_url_async(self, url: str, resolve_dns: bool = True) -> tuple[bool, str | None]: ...
      async def resolve_and_pin_url_async(self, url: str) -> tuple[bool, str | None, dict[str, Any] | None]: ...
  ```
- Implementar `SSRFSafeAsyncBackend`:
  - Desacoplarlo de las subclases privadas de `httpcore._backends` mediante una fábrica de transporte o middleware HTTPX (`httpx.AsyncBaseTransport`), o fijar la compatibilidad estricta con la API pública de conexión de `httpcore` documentando la versión mínima requerida.
  - Ofrecer soporte nativo para fijar IP por cabecera `Host` y reescritura segura de socket para mitigar TOCTOU y DNS Rebinding.

---

## Criterios de Aceptación (Checklist Verificable)

- [ ] Suite de pruebas unitarias en `jg_agente_sdk/tests/test_ssrf_shared.py` evaluando:
  - Bloqueo de localhost (`127.0.0.1`, `localhost`, `::1`).
  - Bloqueo de endpoints de metadatos cloud (`169.254.169.254`, `http://instance-data`).
  - Bloqueo de subredes privadas RFC 1918 salvo que `allow_private_networks=True`.
  - Resolución y pinning DNS con resolución asíncrona simulada.
- [ ] Pruebas 100% aisladas sin acceso a red real utilizando mocks de `socket.getaddrinfo`.
- [ ] Linters y pruebas limpias en el SDK: `pytest` pasando con 0 errores y `ruff check .` validado.
