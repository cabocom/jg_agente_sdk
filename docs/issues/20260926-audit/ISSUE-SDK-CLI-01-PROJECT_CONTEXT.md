# Contexto de Proyecto: [ISSUE-SDK-CLI-01] Documentación Explícita de Comandos Arbitrarios en jg dev (GitLab #5)

## 1. Identificación y Estado
- **Issue ID:** SDK-CLI-01 (GitLab #5)
- **Vínculo Auditoría:** Auditoría Técnica SDK 2026-09-26 (SDK-CLI-01)
- **Componente:** `jg_agente_sdk` (CLI subcomando `jg dev`)
- **Severidad / Prioridad:** MEDIA / Deuda Técnica de Documentación y Usabilidad
- **Estado:** Implementado / Verificado / Cerrado

## 2. Alineación Arquitectónica y Usabilidad
El kit `jg_agente_sdk` provee herramientas CLI ergonómicas para que el desarrollador interactúe con el entorno virtual aislado (`.venv`) del plugin que está construyendo.

El subcomando `jg dev [COMANDO...]` cumple dos funciones:
1. **Modo Interactivo:** Sin argumentos, levanta una subshell enriquecida con las variables de entorno del entorno virtual (`VIRTUAL_ENV`, `PATH`).
2. **Modo Directo:** Con argumentos (e.g. `jg dev pytest`, `jg dev ruff check .`), transfiere directamente la lista de parámetros a `subprocess.run(cmd, env=new_env, cwd=plugin_root)`.

### Hallazgo de Auditoría
En la auditoría técnica de septiembre de 2026, se constató que `dev_parser` carecía de una descripción explícita en su ayuda (`--help`) indicando que ejecuta comandos arbitrarios sin filtrado o whitelist. Esto podía inducir a error a operadores o desarrolladores respecto al alcance y comportamiento del comando.

### Directiva de Resolución
- **Claridad Absoluta en `--help`:** Incorporar una descripción detallada en `dev_parser` con ejemplos prácticos de uso (`pytest`, `ruff check .`, `python -m ...`).
- **Preservación de Flexibilidad:** No restringir arbitrariamente los binarios ejecutables, ya que el desarrollador requiere libertad total para invocar herramientas de testing, cobertura, formateo o profiling dentro de su `.venv`.
- **Trazabilidad en Código:** Documentar en el docstring de `handle_dev` la nota de diseño intencional.

## 3. Criterios de Aceptación
1. `jg dev --help` muestra la descripción detallada con ejemplos claros de ejecución de comandos arbitrarios.
2. `handle_dev` documenta formalmente en su docstring la decisión de diseño.
3. Test automatizado en `tests/test_cli.py` validando la presencia de la descripción y ejemplos en la salida de ayuda.
4. Pase al 100% de la suite de linters (Ruff) y pruebas automatizadas (Pytest).
