# [REFACTOR-v2.0] Refactorización Estructural SOLID y Descomposición de `cli.py` (2.663 LOC) en Subcomandos (`jg_agente_sdk`)

- **Estado:** Abierto / Planificado
- **Fecha:** 2026-11-09
- **Proyecto:** `jg_agente_sdk`
- **GitLab Issue:** [jg_agente_sdk#9](https://gitlab.com/javiergalvez-ia/jg_agente_sdk/-/work_items/9)
- **Asignado a:** Javier Gálvez (`@cabocom`)
- **Documento Maestro:** [`docs/refactor.md`](../../../docs/refactor.md)

---

## 1. Contexto y Objetivo (Arquitectura v2.0 SOLID)

Este issue planifica la refactorización estructural v2.0 de `jg_agente_sdk` conforme a las directrices **SOLID** de `AGENTS.md` (Sección 8) y `docs/refactor.md` (máximo **300 LOC por módulo/clase** y **40 LOC por función**).

## 2. Diagnóstico Real de Ficheros Monolíticos (`>300 LOC`)

El 65% de todo el código del SDK reside en un único fichero monolítico:
1. `jg_sdk/cli.py` (**2.663 LOC**, **69 funciones**)
2. `jg_sdk/contracts.py` (**506 LOC**)
3. `jg_sdk/models.py` (**447 LOC**)
4. `jg_sdk/client.py` (**366 LOC**)

## 3. Plan de Refactorización Estructural (Cero Roturas)

- **Fase 1 (Modularización de `jg_sdk/cli.py`):**
  - Transformar `cli.py` en un paquete estructurado `jg_sdk/cli/` con módulos de responsabilidad única (`init_cmd.py`, `scaffold_cmd.py`, `validate_cmd.py`, `contract_cmd.py`, `templates/`).
  - Mantener los puntos de entrada públicos (`main`, helpers importados por tests) re-exportados en `jg_sdk/cli/__init__.py` para garantizar **0 roturas** en pipelines y tests.
- **Fase 2 (Segmentación de `contracts.py`, `models.py` y `client.py`):**
  - Organizar contratos y modelos por dominio manteniendo intactos todos los re-exports en `jg_sdk/__init__.py`, `jg_sdk/contracts.py` y `jg_sdk/models.py` para no afectar el test de paridad `test_contracts_drift.py` de `jg_agente`.

## 4. Estimación con Gemini Flash y Criterios de Aceptación

- **Esfuerzo estimado:** 2 sesiones (~900k – 1,2 M tokens Gemini Flash, ~40 – 60 min).
- **Criterios de cierre:**
  - [ ] Módulos bajo el umbral de 300 LOC y funciones `<40 LOC`.
  - [ ] 100% de tests en verde (`pytest`) y linter limpio (`ruff check .`).
