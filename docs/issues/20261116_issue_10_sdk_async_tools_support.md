# Issue 01: [jg_agente_sdk] Fix: Soporte nativo para herramientas asíncronas (async def) en AgentTool y MockPluginRunner

- **Título:** `[jg_agente_sdk] Fix: Soporte nativo para herramientas asíncronas (async def) en AgentTool y MockPluginRunner`
- **Prioridad y Fase:** Alta | Fase 0: Remediación Base
- **Dependencias:** Ninguna (Issue raíz de remediación)
- **Contexto Técnico y Archivos Afectados:**
  - Hallazgos del informe: `H-10` (`AgentTool.run()` usa `ThreadPoolExecutor` sincrónico y devuelve corutinas sin resolver si la función es asíncrona) y `H-11` (`MockPluginRunner` no soporta ejecución asíncrona ni inyección de transportes mock).
  - Archivos a modificar:
    - `jg_agente_sdk/jg_sdk/contracts_tools.py`
    - `jg_agente_sdk/jg_sdk/testing.py`
    - `jg_agente_sdk/tests/test_contracts.py`

---

## Especificación Técnica

### 1. `jg_sdk/contracts_tools.py`
- Añadir detección automática de corutinas mediante `inspect.iscoroutinefunction(self.func)`.
- Añadir método asíncrono público a `AgentTool`:
  ```python
  async def run_async(self, *args: Any, **kwargs: Any) -> ToolResult:
      """Ejecuta la herramienta de forma asíncrona respetando timeouts con asyncio.wait_for."""
  ```
- Modificar `AgentTool.run()`:
  - Si `self.func` es una función asíncrona (`async def`) y se llama a `run()` en un hilo sin bucle de eventos activo, debe ejecutar `asyncio.run(_exec_async())`.
  - Si ya existe un bucle de eventos corriendo en el hilo actual, debe lanzar `RuntimeError("Herramienta asíncrona invocada vía run() sincrónico dentro de un bucle de eventos activo. Utilice await tool.run_async(...)")` o ejecutar la corutina concurrentemente sin bloquear el loop.
- Normalizar la captura de excepciones y el cálculo determinista de `duration_ms`.

### 2. `jg_sdk/testing.py`
- Enriquecer `MockPluginRunner`:
  ```python
  async def run_tool_async(
      self,
      tool_name: str,
      args: dict[str, Any] | BaseModel | None = None,
  ) -> ToolResult:
      """Ejecuta una herramienta de forma asíncrona validando args contra args_schema."""
  ```
- Permitir registrar instancias de transporte mock o inyectar dependencias contextuales durante `startup()`.

---

## Criterios de Aceptación (Checklist Verificable)

- [ ] `pytest tests/test_contracts.py` ejecuta tests para herramientas sincrónicas (`def`) y asíncronas (`async def`), verificando que ambas devuelven `ToolResult` válidos sin devolver objetos `coroutine`.
- [ ] Test unitario que valida que `run_async()` aplica el timeout configurado en `tool.timeout_sec` mediante `asyncio.wait_for` y devuelve `ToolResult(success=False, error="TimeoutError...")` en caso de excederse.
- [ ] Test unitario con `MockPluginRunner.run_tool_async()` ejecutando herramientas con esquema Pydantic y comprobando la validación estricta de argumentos.
- [ ] Linters y tipado estricto limpios: `ruff check .` sin warnings y `mypy --strict` pasando en `jg_agente_sdk`.
