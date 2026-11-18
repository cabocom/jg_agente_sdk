# [ISSUE-04] [jg_agente_sdk] refactor(cli): Unificar detección de paquetes, eliminar acoplamiento a Eloquent en dev_cmd y limpiar except Exception: pass

- **ID Maestro QA:** `ISSUE-04`
- **Proyecto Destino:** `javiergalvez-ia/jg_agente_sdk`
- **Asignado a:** `cabocom` / Javier Gálvez (`assignee_ids: [553306]`)
- **Milestone:** `QA & Anti-Fallback Hardening (Nov-Dic 2026)`
- **Labels:** `qa-audit, priority::high, dry, sonar-debt, solid`
- **Estado:** `RESUELTO` (Verificado y aprobado por QA `hydrogen`)
- **GitLab Issue Remoto:** [jg_agente_sdk#16](https://gitlab.com/javiergalvez-ia/jg_agente_sdk/-/work_items/16)

---

- **Severidad y Categoría:** `Major` | `DRY-Duplicación` / `Complejidad-CodeSmell`
- **Consenso de Auditores:** Detectado por: `argon`, `claude-sonnet`, `hydrogen`, `flash-3.8`
- **Evidencia Exacta:**
  - `jg_agente_sdk/jg_sdk/cli/common.py:34-108, 153-181` (`C901=18`, anidamiento 6, `except Exception: pass` en `:79, 91, 137`)
  - `jg_agente_sdk/jg_sdk/cli/dev_cmd.py:24-60, 136-206` (`returncode` ignorado en `_ensure_venv` `:54-59` y `php artisan tinker --execute=\App\Models\Agent::where(...)` en `:188-204`)
  - `jg_agente_sdk/jg_sdk/cli/reload_cmd.py:46, 74, 84-88` vs `status_cmd.py:59, 67, 83, 87, 121, 149-172` (puertos `8001/8002` vs `8921/8922`)
  - `jg_agente_sdk/jg_sdk/cli/__init__.py:109-142` (`_dispatch_command`, `C901=13`)
- **Solución Técnica Propuesta:**
  1. Extraer un único helper de resolución de `pyproject.toml` y directorio de paquete en `cli/common.py`, reduciendo `_detect_plugin_info` a `<= 40` líneas.
  2. Reemplazar la cadena `if/elif` de `_dispatch_command` por un diccionario de despacho; unificar el mapa de puertos de agentes entre `reload_cmd.py` y `status_cmd.py`; verificar `returncode` en `_ensure_venv`; y eliminar la llamada directa a `php artisan tinker` sobre `\App\Models\Agent` en `dev_cmd.py:188-204`.
- **Criterios de Aceptación (Checklist verificable):**
  - [x] Ninguna función en `jg_sdk/cli/` supera `C901 > 10` ni contiene `except Exception: pass` sin logging/tipado específico.
  - [x] `ruff check .` y `pytest` pasan sin errores en `jg_agente_sdk`.

- **Resolución y Cierre:**
  - **Commit:** `refactor(cli): unificar deteccion de paquetes, eliminar acoplamiento eloquent y limpiar silent catches (Closes #16)`
  - **Validación QA:** Aprobado unánimemente por auditor QA `hydrogen` (`[QA-APPROVED] ISSUE-04`).
  - **Linters y Tests:** Ruff 100% limpio (C901 <= 10 en toda la CLI, cero S110/BLE001), 78/78 tests unitarios pasando.

---
