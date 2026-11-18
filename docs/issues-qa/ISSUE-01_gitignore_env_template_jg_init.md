# [ISSUE-01] [jg_agente_sdk] fix(cli): Incluir .env en la plantilla .gitignore generada por jg init

- **ID Maestro QA:** `ISSUE-01`
- **Proyecto Destino:** `javiergalvez-ia/jg_agente_sdk`
- **Asignado a:** `cabocom` / Javier Gálvez (`assignee_ids: [553306]`)
- **Milestone:** `QA & Anti-Fallback Hardening (Nov-Dic 2026)`
- **Labels:** `qa-audit, priority::blocker, security`
- **Estado:** `RESUELTO` (Verificado y aprobado por QA `hydrogen`)
- **GitLab Issue Remoto:** [jg_agente_sdk#13](https://gitlab.com/javiergalvez-ia/jg_agente_sdk/-/work_items/13)

---

- **Severidad y Categoría:** `Blocker` | `Seguridad`
- **Consenso de Auditores:** Detectado por: `argon` | Omitido por: `claude-sonnet`, `flash-3.8`, `hydrogen`
- **Evidencia Exacta:**
  - `jg_agente_sdk/jg_sdk/cli/templates/config.py:60-79`
  - `jg_agente_sdk/jg_sdk/cli/init_cmd.py:150`
  ```python
  # jg_agente_sdk/jg_sdk/cli/templates/config.py:60-79
  def get_gitignore_template() -> str:
      """Genera el contenido de .gitignore."""
      return """# Entornos virtuales
  .venv/
  env/
  venv/
  ...
  # Distribución y empaquetado
  dist/
  build/
  *.egg-info/
  """
  ```
- **Solución Técnica Propuesta:**
  1. Añadir `.env`, `.env.*` y `!.env.example` a `get_gitignore_template()` en `jg_agente_sdk/jg_sdk/cli/templates/config.py:60-79`.
  2. Sincronizar la versión hardcodeada `"1.3.0"` en `jg_sdk/cli/parser.py:263` y `jg_sdk/mcp/client.py:94` con `jg_sdk.__version__` (`"2.0.0"`).
- **Criterios de Aceptación (Checklist verificable):**
  - [x] `get_gitignore_template()` incluye `.env` y `!.env.example`.
  - [x] Test unitario en `jg_agente_sdk/tests/test_cli.py` que verifica que `.env` está presente en el `.gitignore` generado por `jg init`.
  - [x] `ruff check .` y `pytest` en `jg_agente_sdk` pasan al 100%.

- **Resolución y Cierre:**
  - **Commit:** `fix(cli): incluir .env en plantilla .gitignore de jg init y sincronizar __version__ (Closes #13)`
  - **Validación QA:** Aprobado unánimemente por auditor QA `hydrogen` (`[QA-APPROVED] ISSUE-01`).
  - **Linters y Tests:** Ruff 100% limpio, 72/72 tests unitarios pasando.
