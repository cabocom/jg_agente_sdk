# [ISSUE-02] [jg_agente_sdk] fix(security): Corregir bloqueo falso con enforce=False, excepción DNS en resolve_and_pin_url y bypass SSRF por redirecciones en McpHttpClient

- **ID Maestro QA:** `ISSUE-02`
- **Proyecto Destino:** `javiergalvez-ia/jg_agente_sdk`
- **Asignado a:** `cabocom` / Javier Gálvez (`assignee_ids: [553306]`)
- **Milestone:** `QA & Anti-Fallback Hardening (Nov-Dic 2026)`
- **Labels:** `qa-audit, priority::critical, security, bug`
- **GitLab Issue Remoto:** [jg_agente_sdk#14](https://gitlab.com/javiergalvez-ia/jg_agente_sdk/-/work_items/14)

---

- **Severidad y Categoría:** `Critical` | `Seguridad` / `Fiabilidad-Bug`
- **Consenso de Auditores:** Detectado por: `argon` | Omitido por: `claude-sonnet`, `flash-3.8`, `hydrogen`
- **Evidencia Exacta:**
  - `jg_agente_sdk/jg_sdk/security/ssrf.py:184-185, 240-260`
  - `jg_agente_sdk/jg_sdk/mcp/client.py:57-67`
  ```python
  # jg_agente_sdk/jg_sdk/security/ssrf.py:184-185, 240-244
  if not self.enforce:
      return True, None, None, None
  ...
  def resolve_and_pin_url(self, url: str) -> tuple[bool, str | None, dict[str, Any] | None]:
      ok, reason, parsed, hostname = self._pre_validate_url(url)
      if not ok or not hostname or parsed is None:
          return False, reason, None
  ```
  ```python
  # jg_agente_sdk/jg_sdk/mcp/client.py:60-67
  self._ssrf_validator.assert_safe_url(self.base_url)
  self._client = httpx.AsyncClient(
      base_url=self.base_url,
      timeout=self.timeout_sec,
      follow_redirects=True,
  ```
- **Solución Técnica Propuesta:**
  1. En `SSRFValidator.resolve_and_pin_url` y `resolve_and_pin_url_async` (`jg_sdk/security/ssrf.py:240-277`), si `not self.enforce`, parsear `urlparse(url)` y retornar `(True, None, _build_pinned_info(...))` sin bloquear; envolver `self.resolve_host(...)` en `try/except SSRFValidationError as exc: return False, str(exc), None` y verificar `if not ips:`.
  2. En `McpHttpClient._get_client` (`jg_sdk/mcp/client.py:57-67`), utilizar `await self._ssrf_validator.validate_url_async(self.base_url)` (no bloqueante) y fijar `follow_redirects=False` (o validar cada redirección mediante event hook de `httpx`).
  3. Reducir los métodos públicos de `SSRFValidator` a `<= 10` conforme a la Regla 8.1 de `AGENTS.md`.
- **Criterios de Aceptación (Checklist verificable):**
  - [ ] `resolve_and_pin_url("http://127.0.0.1:8000")` con `enforce=False` retorna `ok=True`.
  - [ ] `resolve_and_pin_url("https://nonexistent.invalid")` retorna `(False, reason, None)` sin lanzar `SSRFValidationError` no capturada.
  - [ ] `McpHttpClient` rechaza redirecciones HTTP 302 hacia `http://169.254.169.254` o `http://127.0.0.1`.
  - [ ] Nuevos tests en `tests/test_ssrf_shared.py` y `tests/test_mcp_client.py` pasan al 100%.
