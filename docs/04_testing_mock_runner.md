# 04. Testing y Harness de Desarrollo (`MockPluginRunner`)

## 1. Pruebas Aisladas de Plugins sin Dependencias

Uno de los principales beneficios de `jg_agente_sdk` es que permite a los desarrolladores programar y validar plugins en entornos de desarrollo locales **sin necesidad de levantar contenedores Docker, PostgreSQL ni el runtime completo de LangGraph**.

Para ello, el módulo `jg_sdk.testing` proporciona `MockPluginRunner`.

---

## 2. Uso de `MockPluginRunner`

```python
import pytest
from jg_sdk.testing import MockPluginRunner
from jg_plugin_datosgob.plugin import DatosGobPlugin

@pytest.mark.asyncio
async def test_plugin_lifecycle_and_tools():
    plugin = DatosGobPlugin()

    # Uso como context manager asíncrono (ejecuta startup() y shutdown() automáticamente)
    async with MockPluginRunner(plugin) as runner:
        # 1. Validar metadatos
        assert runner.metadata.name == "jg_plugin_datosgob"

        # 2. Listar e inspeccionar herramientas
        tools = runner.list_tools()
        assert len(tools) > 0

        # 3. Invocar una herramienta específica
        tool = runner.get_tool("datosgob_search")
        result = tool.run(query="transporte", limit=5)

        assert result.success is True
        assert len(result.output) > 0
        assert result.duration_ms > 0

        # 4. Validar chequeo de salud
        health = await runner.health_check()
        assert health["status"] == "ok"
```

---

## 3. Pruebas de Reversibilidad y Rollback

Si una herramienta implementa compensación automática ante fallos (`reversible=True`):

```python
def test_tool_rollback_execution():
    tool = runner.get_tool("create_isolated_environment")
    
    # 1. Ejecutar acción mutante
    result = tool.run(env_name="test-env")
    assert result.success is True
    assert result.rollback_context is not None

    # 2. Simular fallo posterior e invocar compensación
    rollback_result = tool.rollback(result.rollback_context)
    assert rollback_result.success is True
    assert rollback_result.metadata["rollback_executed"] is True
```
