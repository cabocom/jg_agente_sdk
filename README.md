# jg_agente_sdk

**Software Development Kit Canónico y Contratos Públicos para el Ecosistema jG**  
*Librería de Tipos, Cliente HTTP Firmado, Harness de Testing y CLI de Scaffolding*

---

## 1. Visión General y Propósito

`jg_agente_sdk` es el kit de desarrollo de software público, liviano y desacoplado para el ecosistema agéntico jG. Provee la **Fuente Única de Verdad (Single Source of Truth - SSOT)** para el desarrollo de plugins, herramientas y clientes de integración.

### Principio de Diseño: Cero Dependencias Pesadas
El SDK no contiene ni referencia `langgraph`, `langchain`, checkpointers de base de datos (`DualPostgresSaver`, `MemorySaver`) ni frameworks web pesados (`FastAPI`, `Laravel`). Depende exclusivamente de:
- `pydantic >= 2.0.0`
- `httpx >= 0.25.0`
- Python `>= 3.11`

Esto permite que cualquier desarrollador u organización cree plugins de especialidad e invoque o pruebe herramientas de forma aislada sin levantar contenedores ni bases de datos.

### Documentación Técnica Modular
Estructurada en múltiples idiomas bajo [`docs/`](docs/README.md):
- 🇪🇸 **Español (SSOT):**
  - [01. Guía Rápida de Inicio](docs/es/01_quickstart.md) — Instalación, configuración y primer plugin en 5 minutos.
  - [02. Especificación de Contratos y Modelos](docs/es/02_contracts_spec.md) — `AgentTool`, `ToolResult`, `AgentInput` y `AgentOutput`.
  - [03. Referencia de Línea de Comandos](docs/es/03_cli_reference.md) — CLI de scaffolding, testing y validación de manifiestos.
  - [04. Testing y Harness de Desarrollo](docs/es/04_testing_mock_runner.md) — `MockAgentRunner` y simulación sin infraestructura.
  - [05. Despliegue Local con `jg_agente`](docs/es/05_running_with_jg_agente.md) — Variables de entorno mínimas y ejecución.
- 🇬🇧 **English (Reference):**
  - [01. Quickstart](docs/en/01_quickstart.md) · [02. Contracts](docs/en/02_contracts_spec.md) · [03. CLI](docs/en/03_cli_reference.md) · [04. Testing](docs/en/04_testing_mock_runner.md) · [05. Running](docs/en/05_running_with_jg_agente.md)

---

## 2. Contratos Canónicos de Capacidades

### 2.1 `AgentTool` (`jg_sdk.contracts`)
Descriptor declarativo de una herramienta ejecutable:
```python
class AgentTool(BaseModel):
    name: str  # Identificador único de la herramienta
    description: str  # Descripción funcional clara para el LLM
    category: str = "general"  # Categoría taxonómica
    version: str = "1.0.0"  # Versión semántica
    args_schema: type[BaseModel] | None = None  # Esquema Pydantic de argumentos
    func: Callable[..., Any]  # Función invocable
    risk_level: RiskLevel = RiskLevel.LOW  # LOW, MEDIUM, HIGH, CRITICAL
    required_permissions: list[str] = []  # Scopes RBAC requeridos
    tool_type: ToolType = ToolType.OBSERVER  # observer, actuator, verifier, read, mutation
    read_only: bool = True  # Ausencia de efectos secundarios
    reversible: bool = False  # Capacidad de compensación
    idempotent: bool = True  # Idempotencia de ejecución
    makes_http_requests: bool = False  # Sujeto a validación SSRF
    allow_failure: bool = False  # Si es True, su fallo no interrumpe el plan
    timeout_sec: float = 30.0  # Límite temporal duro
    rollback_func: Callable[[dict], ToolResult] | None = None  # Compensador
```

> **Regla de Validación:** Si `reversible=True`, el validador Pydantic exige obligatoriamente un invocable no nulo en `rollback_func`.

### 2.2 `ToolResult` (`jg_sdk.contracts`)
Resultado estructurado emitido tras la ejecución:
```python
class ToolResult(BaseModel):
    success: bool
    output: Any = ""
    error: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = {}
    rollback_context: dict[str, Any] | None = None
```

---

## 3. Contratos de Comunicación (I/O)

Definidos en `jg_sdk.models`:
- **`AgentInput`:** Estímulo normalizado (`execution_id`, `thread_id`, `prompt`, `parameters`, `user_context`, `callback_url`, `metadata`).
- **`AgentOutput`:** Salida sintetizada (`execution_id`, `thread_id`, `status`, `response`, `data`, `execution_time_ms`, `requires_approval`, `pending_approval_id`, `error`).
- **`UserContext`:** Contexto RBAC del usuario solicitante (`user_id`, `username`, `role`, `permissions`).

---

## 4. Cliente HTTP con Firmado Canónico HMAC (`AgentClient`)

El SDK incluye `AgentClient` (`jg_sdk.client`), un cliente HTTP síncrono y asíncrono para interactuar con agentes en red privada calculando automáticamente la firma criptográfica canónica:

```python
from jg_sdk.client import AgentClient
from jg_sdk.models import AgentInput

client = AgentClient(
    base_url="http://jg_agente:8000",
    agent_id="a0000000-0000-0000-0000-000000000001",
    secret="mi_secreto_permanente_64_caracteres",
)

# Invocación síncrona
input_data = AgentInput(
    execution_id="exec-123", thread_id="th-456", prompt="Consultar estado de servicios"
)
output = client.trigger(input_data)
print(output.response)

# Invocación asíncrona
# output = await client.atrigger(input_data)
```

Fórmula de firma generada automáticamente:
$$\text{Signature} = \text{HMAC-SHA256}(\text{METHOD\textbackslash nPATH\textbackslash nTIMESTAMP\textbackslash nSHA256(BODY)}, \text{SECRET})$$

---

## 5. Testing Aislado con `MockPluginRunner`

Permite probar el ciclo de vida completo de un plugin y la ejecución de herramientas sin desplegar FastAPI, LangGraph ni PostgreSQL:

```python
import pytest
from jg_sdk.testing import MockPluginRunner
from mi_plugin.plugin import MiPlugin


@pytest.mark.asyncio
async def test_plugin():
    plugin = MiPlugin()
    async with MockPluginRunner(plugin) as runner:
        tool = runner.get_tool("mi_herramienta")
        res = tool.run(param="valor")
        assert res.success is True
```

---

## 6. CLI de Scaffolding (`jg-sdk-cli`)

Herramienta de consola para generar nuevos plugins de forma estandarizada:

```bash
# Crear un nuevo plugin con plantilla completa
jg-sdk-cli new network_diagnostics --template full --author "Javier Gálvez"

# Inspeccionar herramientas de un plugin local
jg-sdk-cli inspect ./jg_plugin_datosgob

# Validar cumplimiento de contratos
jg-sdk-cli verify ./jg_plugin_datosgob

# Enlazar plugin en desarrollo a una instancia de agente (con comprobaciones de seguridad)
jg link jg_plugin_conversational -t jg_agente/plugins

# Desvincular enlace simbólico sin afectar el código fuente
jg unlink jg_plugin_conversational -t jg_agente/plugins
```

---

## 7. Despliegue Local con `jg_agente` (Variables de Entorno)

Para probar la integración real de un plugin con el motor cognitivo de `jg_agente` en local sin dependencias de infraestructura pesada (PostgreSQL o `jg_dashboard`), consulta la guía completa:
- **[05. Despliegue Local y Ejecución con `jg_agente`](docs/es/05_running_with_jg_agente.md)** (`en`: [05_running_with_jg_agente.md](docs/en/05_running_with_jg_agente.md))

Configuración mínima requerida en `.env`:
```env
DEFAULT_LOCALE=es                 # Idioma del runtime: 'es', 'en', 'fr', 'de', 'it'
PLUGINS_DIR=.                     # Directorio del plugin
ENABLED_PLUGINS=mi_plugin         # Nombre del plugin
LLM_PROVIDER=mock                 # Modo mock determinista sin consumo de API externa
REQUIRE_DASHBOARD_REGISTRATION=false
CHECKPOINTER_BACKEND=memory
```

---

## 8. Verificación de Calidad

La suite del SDK incluye **47 pruebas automatizadas** que validan la serialización de contratos, la firma HMAC y el mock runner:

```bash
pytest tests/
```

---

## 9. Licencia

Distribuido bajo [Licencia MIT](LICENSE). Permite el desarrollo e integración de plugins libres o propietarios sin restricciones copyleft.
