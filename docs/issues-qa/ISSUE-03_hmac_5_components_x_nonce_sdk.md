# [ISSUE-03] [jg_agente_sdk] feat(auth): Soportar firma canónica HMAC de 5 componentes con X-Nonce en jg_sdk.auth y JGAgentClient

- **ID Maestro QA:** `ISSUE-03`
- **Proyecto Destino:** `javiergalvez-ia/jg_agente_sdk`
- **Asignado a:** `cabocom` / Javier Gálvez (`assignee_ids: [553306]`)
- **Milestone:** `QA & Anti-Fallback Hardening (Nov-Dic 2026)`
- **Labels:** `qa-audit, priority::critical, security, bug`
- **Estado:** `RESUELTO` (Verificado y aprobado por QA `hydrogen`)
- **GitLab Issue Remoto:** [jg_agente_sdk#15](https://gitlab.com/javiergalvez-ia/jg_agente_sdk/-/work_items/15)

---

- **Severidad y Categoría:** `Critical` | `Seguridad` / `Fiabilidad-Bug`
- **Consenso de Auditores:** Detectado por: `argon` | Omitido por: `claude-sonnet`, `flash-3.8`, `hydrogen`
- **Evidencia Exacta:**
  - `jg_agente_sdk/jg_sdk/auth.py:34-52`
  - `jg_agente_sdk/jg_sdk/client.py:72, 93-118`
  ```python
  # jg_agente_sdk/jg_sdk/auth.py:34-52
  def compute_canonical_string(
      method: str,
      path: str,
      timestamp: str,
      body_sha256: str,
  ) -> str:
      return f"{norm_method}\n{norm_path}\n{norm_ts}\n{norm_hash}"
  ```
- **Solución Técnica Propuesta:**
  1. Añadir el parámetro opcional `nonce: str | None = None` a `compute_canonical_string`, `compute_hmac_signature` y `verify_hmac_signature` en `jg_sdk/auth.py` (idéntico al contrato de `jg_agente/app/security/auth.py:83-120`).
  2. Generar y enviar `X-Nonce` (UUIDv4) por defecto en `JGAgentClient._build_signed_headers` (`jg_sdk/client.py:93-118`) e inicializar `self._client` de forma perezosa (`lazy`) en lugar de en `__init__` (`jg_sdk/client.py:72`).
- **Criterios de Aceptación (Checklist verificable):**
  - [x] `JGAgentClient` incluye `X-Nonce` y firma los 5 componentes (`METHOD\nPATH\nTIMESTAMP\nBODY_SHA256\nNONCE`).
  - [x] Tests de paridad en `jg_agente_sdk/tests/test_client_hmac.py` validando firmas con y sin `nonce`.

- **Resolución y Cierre:**
  - **Commit:** `feat(auth): soportar firma canónica hmac de 5 componentes con x-nonce y lazy client (Closes #15)`
  - **Validación QA:** Aprobado unánimemente por auditor QA `hydrogen` (`[QA-APPROVED] ISSUE-03`).
  - **Linters y Tests:** Ruff 100% limpio, 78/78 tests unitarios pasando.
