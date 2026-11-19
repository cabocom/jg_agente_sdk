# [ISSUE-02] [jg_agente_sdk] fix(security): Corregir bloqueo falso con enforce=False, excepción DNS en resolve_and_pin_url y bypass SSRF por redirecciones en McpHttpClient

- **ID Maestro QA:** `ISSUE-02`
- **Proyecto Destino:** `javiergalvez-ia/jg_agente_sdk`
- **Asignado a:** `cabocom` / Javier Gálvez (`assignee_ids: [553306]`)
- **Milestone:** `QA & Anti-Fallback Hardening (Nov-Dic 2026)`
- **Labels:** `qa-audit, priority::critical, security, bug`
- **Estado:** `RESUELTO` (Verificado y aprobado por QA `hydrogen` y supervisión `claude-sonnet`)
- **GitLab Issue Remoto:** [jg_agente_sdk#14](https://gitlab.com/javiergalvez-ia/jg_agente_sdk/-/work_items/14)

---

- **Severidad y Categoría:** `Critical` | `Seguridad` / `Fiabilidad-Bug`
- **Consenso de Auditores:** Detectado por: `argon` | Supervisado por: `claude-sonnet`
- **Evidencia Exacta:**
  - `jg_agente_sdk/jg_sdk/security/ssrf.py:184-185, 240-260`
  - `jg_agente_sdk/jg_sdk/mcp/client.py:57-67`
- **Solución Técnica Implementada:**
  1. En `SSRFValidator.resolve_and_pin_url` y `resolve_and_pin_url_async` (`jg_sdk/security/ssrf.py`), si `not self.enforce`, parsear `urlparse(url)` y retornar `(True, None, _build_pinned_info(...))` sin bloquear; si la resolución DNS falla o la lista está vacía, retornar `(False, f"Fallo en resolución DNS para '{hostname}': {exc}", None)` capturando `(SSRFValidationError, OSError)` sin inventar ninguna IP `127.0.0.1` por defecto (resolución de hallazgo H-1).
  2. En `McpHttpClient` (`jg_sdk/mcp/client.py`), centralizar la validación de redirecciones en `_assert_redirect_safe` (resolución de hallazgo H-2), validando de forma no bloqueante contra SSRF.
  3. Fijar `follow_redirects=False` por defecto en `McpHttpClient`, rechazando cualquier 3xx con `McpClientError` explícito para evitar fugas silenciosas de llamadas JSON-RPC (resolución de hallazgo H-3), permitiendo el seguimiento solo si el consumidor lo habilita explícitamente (`follow_redirects=True`).
  4. Reducir los métodos públicos de `SSRFValidator` a `<= 10` y los métodos a `<= 40` líneas conforme a las directrices SOLID de `AGENTS.md`.
- **Criterios de Aceptación (Checklist verificable):**
  - [x] `resolve_and_pin_url("http://127.0.0.1:8000")` con `enforce=False` retorna `ok=True`.
  - [x] `resolve_and_pin_url("https://nonexistent.invalid")` retorna `(False, reason, None)` tanto con `enforce=True` como con `enforce=False`.
  - [x] `McpHttpClient` rechaza redirecciones HTTP 302 hacia `http://169.254.169.254` o `http://127.0.0.1`.
  - [x] `McpHttpClient` con `follow_redirects=False` (default) rechaza redirecciones 3xx seguras con `McpClientError`.
  - [x] `McpHttpClient` con `follow_redirects=True` sigue redirecciones seguras y bloquea las inseguras.
  - [x] Helper `_assert_redirect_safe` unifica la validación anti-SSRF de redirecciones.
  - [x] Suite completa de 81 tests unitarios pasando al 100% y Ruff 100% limpio sin observaciones.

- **Resolución y Cierre:**
  - **Commit:** `fix(security): corregir falso bloqueo enforce=False, dns catch y ssrf redirects en mcp (Closes #14)`
  - **Ajustes de Supervisión:** Erradicado fallback silencioso H-1 en `_handle_unforced_pin`, DRY en `_assert_redirect_safe` H-2 y cobertura completa de redirección H-3.
