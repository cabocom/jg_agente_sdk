# 04. Testing and Development Harness (`MockPluginRunner`)

## 1. Isolated Plugin Testing Without Heavy Dependencies

One of the premier benefits of `jg_agente_sdk` is enabling plugin developers to write and thoroughly test tools locally **without requiring Docker containers, PostgreSQL, or full LangGraph runtimes**.

The `jg_sdk.testing` module provides the `MockPluginRunner` harness for fast, unit-level testing.

---

## 2. Using `MockPluginRunner`

```python
import pytest
from jg_sdk.testing import MockPluginRunner
from jg_plugin_datosgob.plugin import DatosGobPlugin


@pytest.mark.asyncio
async def test_plugin_lifecycle_and_tools():
    plugin = DatosGobPlugin()

    # Async context manager handles startup() and shutdown() cleanly
    async with MockPluginRunner(plugin) as runner:
        # 1. Validate metadata
        assert runner.metadata.name == "jg_plugin_datosgob"

        # 2. List and inspect registered capabilities
        tools = runner.list_tools()
        assert len(tools) > 0

        # 3. Invoke a specific tool
        tool = runner.get_tool("datosgob_search")
        result = tool.run(query="transportation", limit=5)

        assert result.success is True
        assert len(result.output) > 0
        assert result.duration_ms > 0

        # 4. Check plugin health
        health = await runner.health_check()
        assert health["status"] == "ok"
```

---

## 3. Testing Reversibility & Rollbacks

When a tool implements Saga compensating actions (`reversible=True`):

```python
def test_tool_rollback_execution():
    tool = runner.get_tool("create_isolated_environment")
    
    # 1. Execute mutating action
    result = tool.run(env_name="test-env")
    assert result.success is True
    assert result.rollback_context is not None

    # 2. Simulate subsequent failure and invoke compensating rollback
    rollback_res = tool.rollback(result.rollback_context)
    assert rollback_res.success is True
```
