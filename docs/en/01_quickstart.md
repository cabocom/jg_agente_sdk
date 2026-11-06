# 01. Quickstart Guide (`jg_agente_sdk`)

## 1. What is `jg_agente_sdk`?

`jg_agente_sdk` is the official public, lightweight, decoupled software development kit for the jG ecosystem. It provides the **canonical contracts**, pure Pydantic models, HTTP client with automatic HMAC-SHA256 request signing, testing harness (`MockAgentRunner`), and the command-line interface (`jg` / `jg-sdk-cli`).

### Core Design Principle: Zero Heavy Dependencies
The SDK intentionally avoids heavy dependencies on LangGraph, LangChain, databases (SQLAlchemy/asyncpg), or web servers (FastAPI). It strictly relies on:
- `pydantic >= 2.0.0`
- `httpx >= 0.25.0`
- Python `>= 3.11`

---

## 2. Installation

```bash
# Editable local installation for plugin development
pip install -e ./jg_agente_sdk

# Verify CLI availability
jg --help
```

---

## 3. Minimal Tool Creation Example

```python
from pydantic import BaseModel, Field
from jg_sdk.contracts import AgentTool, ToolResult, RiskLevel, ToolType


class HostnameInput(BaseModel):
    hostname: str = Field(..., description="Target hostname to check")


def ping_check(args: HostnameInput) -> ToolResult:
    # Execution logic
    return ToolResult(
        success=True, output=f"Host {args.hostname} responded in 12ms", metadata={"latency_ms": 12.0}
    )


tool = AgentTool(
    name="ping_check",
    description="Checks network reachability for a target host",
    args_schema=HostnameInput,
    func=ping_check,
    risk_level=RiskLevel.LOW,
    tool_type=ToolType.OBSERVER,
    read_only=True,
    timeout_sec=5.0,
)

# Isolated execution with built-in timeout control
res = tool.run(HostnameInput(hostname="internal.api"))
print(res.output)
```

---

## 4. Official Plugin Structure

```python
from jg_sdk.contracts import BasePlugin, PluginMetadata, AgentTool, BaseEngine


class NetworkPlugin(BasePlugin):
    def get_plugin_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="jg_plugin_network",
            version="1.0.0",
            description="Network diagnostics tools for jg_agente",
            author="Your Organization",
            supported_locales=["en", "es"],
            default_locale="en",
            tags=["network", "diagnostics"],
        )

    def register_tools(self) -> list[AgentTool]:
        return [tool]

    def register_engines(self) -> dict[str, BaseEngine]:
        return {}
```

---

## 5. Running `jg_agente` with your Plugin

To test your plugin within the full cognitive reasoning graph of `jg_agente` locally:
- **[05. Local Deployment & Execution with `jg_agente`](05_running_with_jg_agente.md)**

Minimal local environment configuration (`.env`):
```env
DEFAULT_LOCALE=en
PLUGINS_DIR=.
ENABLED_PLUGINS=jg_plugin_network
LLM_PROVIDER=mock
REQUIRE_DASHBOARD_REGISTRATION=false
CHECKPOINTER_BACKEND=memory
AGENT_PORT=8000
```
