# [REFACTOR-v2.0] Refactorización Estructural SOLID y Descomposición de `cli.py` (2.663 LOC) en Subcomandos (`jg_agente_sdk`)

- **Estado:** Cerrado / Resuelto (v1.2.0 / v1.2.1)
- **Fecha:** 2026-11-09 (Cerrado: 2026-11-11)
- **Proyecto:** `jg_agente_sdk`
- **GitLab Issue:** [jg_agente_sdk#9](https://gitlab.com/javiergalvez-ia/jg_agente_sdk/-/work_items/9)
- **Asignado a:** Javier Gálvez (`@cabocom`)
- **Documento Maestro:** [`docs/refactor.md`](../../../docs/refactor.md)

---

## 1. Contexto y Objetivo (Arquitectura v2.0 SOLID)

Este issue planifica y ejecuta la refactorización estructural v2.0 de `jg_agente_sdk` conforme a las directrices **SOLID** de `AGENTS.md` (Sección 8) y `docs/refactor.md` (máximo **300 LOC por módulo/clase** y **40 LOC por función**).

## 2. Diagnóstico Real de Ficheros Monolíticos (`>300 LOC`)

1. `jg_sdk/cli.py` (**2.663 LOC**, **69 funciones**) -> **RESUELTO: Descompuesto en paquete modular `jg_sdk/cli/`** (máx 266 LOC)
2. `jg_sdk/contracts.py` (**506 LOC**) -> **RESUELTO: Descompuesto en `contracts_enums.py` (64 LOC), `contracts_tools.py` (269 LOC), `contracts_plugins.py` (214 LOC) y fachada `contracts.py` (48 LOC)**
3. `jg_sdk/models.py` (**447 LOC**) -> **RESUELTO: Descompuesto en `models_context.py` (129 LOC), `models_io.py` (133 LOC), `models_execution.py` (228 LOC) y fachada `models.py` (59 LOC)**
4. `jg_sdk/client.py` (**366 LOC**) -> **RESUELTO: Extraído `auth.py` (139 LOC) y `client.py` reducido a 254 LOC**

## 3. Plan de Refactorización Estructural (Cero Roturas)

- [x] **Fase 1 (Modularización de `jg_sdk/cli.py` - COMPLETADA):**
  - Descomposición completa de `cli.py` (2.663 LOC) en un paquete estructurado `jg_sdk/cli/` con módulos de responsabilidad única:
    * `jg_sdk/cli/__init__.py` (165 LOC): Re-exportación completa de la API pública y dispatchers.
    * `jg_sdk/cli/__main__.py` (14 LOC): Punto de entrada para ejecución directa `python -m jg_sdk.cli`.
    * `jg_sdk/cli/build_cmd.py` (151 LOC): Lógica de compilación y etiquetado Docker Compose / Dockerfile.
    * `jg_sdk/cli/clean_cmd.py` (144 LOC): Limpieza de contenedores, cachés y desvinculación de symlinks.
    * `jg_sdk/cli/common.py` (227 LOC): Utilidades compartidas y detección estática de capacidades/metadatos.
    * `jg_sdk/cli/dev_cmd.py` (206 LOC): Subcomandos `install`, `dev`, `run`, `test`.
    * `jg_sdk/cli/init_cmd.py` (175 LOC): Scaffolding determinista de nuevos plugins.
    * `jg_sdk/cli/link_cmd.py` (238 LOC): Enlaces simbólicos relativos, detección de colisiones y gaps de seguridad.
    * `jg_sdk/cli/parser.py` (266 LOC): Árbol declarativo de argumentos y opciones CLI.
    * `jg_sdk/cli/reload_cmd.py` (109 LOC): Hot-reload de plugins en caliente vía socket/API REST.
    * `jg_sdk/cli/status_cmd.py` (184 LOC): Estado contextual e inspección de salud.
    * `jg_sdk/cli/templates/` (Paquete modular de generadores de plantillas, cada uno < 185 LOC).
  - Ningún módulo supera las 300 LOC ni ninguna función supera las 40 LOC.
  - 100% de compatibilidad hacia atrás garantizada: `from jg_sdk.cli import *` y `project.scripts` (`jg = "jg_sdk.cli:main"`).
- [x] **Fase 2 (Segmentación de `contracts.py`, `models.py` y `client.py` - COMPLETADA):**
  - Organización de contratos y modelos por dominio manteniendo intactos todos los re-exports en `jg_sdk/__init__.py`, `jg_sdk/contracts.py` y `jg_sdk/models.py`.
  - Descomposición de `contracts.py` (506 LOC) en `contracts_enums.py` (64 LOC), `contracts_tools.py` (269 LOC) y `contracts_plugins.py` (214 LOC).
  - Descomposición de `models.py` (447 LOC) en `models_context.py` (129 LOC), `models_io.py` (133 LOC) y `models_execution.py` (228 LOC).
  - Descomposición de `client.py` (366 LOC) extrayendo `auth.py` (139 LOC) y reduciendo `client.py` a 254 LOC.
  - 0 archivos > 300 LOC en todo el SDK. 100% de tests unitarios pasando (54/54) y paridad total con `jg_agente`.

## 4. Criterios de Aceptación (Fase 1 y Fase 2)

- [x] Todos los módulos bajo el umbral estricto de 300 LOC (máximo 271 LOC) y funciones `<40 LOC`.
- [x] 100% de tests en verde (`pytest`: 54/54 passing).
- [x] Linter limpio y formateo estricto (`ruff check .`, `ruff format --check .`).
- [x] Cero roturas en tests de drift de `jg_agente` (`test_contracts_drift.py` 8/8 passing).
