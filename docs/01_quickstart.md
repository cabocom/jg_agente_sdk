# 01. Guía Rápida de Inicio (`jg_agente_sdk`)

## 1. ¿Qué es `jg_agente_sdk`?

`jg_agente_sdk` es el kit de desarrollo de software público, liviano y desacoplado para el ecosistema jG. Provee los **contratos canónicos**, modelos Pydantic puros, cliente HTTP con firmado automático HMAC-SHA256, utilidades de prueba (`MockAgentRunner`) y la herramienta de línea de comandos (`jg-sdk-cli`).

### Principio de Diseño: Cero Dependencias Pesadas
El SDK no incluye dependencias de LangGraph, LangChain, bases de datos (SQLAlchemy/asyncpg) ni servidores web (FastAPI). Depende exclusivamente de:
- `pydantic >= 2.0.0`
- `httpx >= 0.25.0`
- Python `>= 3.11`

---

## 2. Instalación

```bash
# Instalación local editable durante desarrollo
pip install -e ./jg_agente_sdk

# Verificación de instalación
jg-sdk-cli --help
```

---

## 3. Ejemplo Mínimo de Creación de Herramientas

```python
from pydantic import BaseModel, Field
from jg_sdk.contracts import AgentTool, ToolResult, RiskLevel, ToolType

class HostnameInput(BaseModel):
    hostname: str = Field(..., description="Nombre del host a comprobar")

def ping_check(args: HostnameInput) -> ToolResult:
    # Lógica de comprobación
    return ToolResult(
        success=True,
        output=f"Host {args.hostname} responde en 12ms",
        metadata={"latency_ms": 12.0}
    )

tool = AgentTool(
    name="ping_check",
    description="Comprueba la conectividad de red hacia un host determinado",
    args_schema=HostnameInput,
    func=ping_check,
    risk_level=RiskLevel.LOW,
    tool_type=ToolType.OBSERVER,
    read_only=True,
    timeout_sec=5.0
)

# Ejecución aislada con control de timeouts
res = tool.run(HostnameInput(hostname="api.interno"))
print(res.output)
```

---

## 4. Estructura Básica de un Plugin Oficial

```python
from jg_sdk.contracts import BasePlugin, PluginMetadata, AgentTool, BaseEngine

class NetworkPlugin(BasePlugin):
    def get_plugin_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="jg_plugin_network",
            version="1.0.0",
            description="Herramientas de diagnóstico de red para jg_agente",
            author="Tu Organización",
            tags=["network", "diagnostics"]
        )

    def register_tools(self) -> list[AgentTool]:
        return [tool]

    def register_engines(self) -> dict[str, BaseEngine]:
        return {}
```
