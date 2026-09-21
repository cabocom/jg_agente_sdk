# jg-agente-sdk

**SDK desacoplado y contratos públicos para el ecosistema de plugins y clientes de `jg_agente`.**

---

## 1. Visión y Frontera Arquitectónica (Open Core)

`jg-agente-sdk` es la librería pública y desacoplada del ecosistema **javiergalvez-ia**. Proporciona las interfaces formales, modelos canónicos y el cliente de comunicación criptográfica sin exponer ninguna implementación interna del Execution Plane:

- **Cero dependencias del orquestador:** No contiene ni referencia `langgraph`, `langchain`, checkpointers (`DualPostgresSaver`, `MemorySaver`), bases de datos (`asyncpg`, `SQLAlchemy`) ni frameworks web (`fastapi`, `uvicorn`).
- **Dependencias mínimas de producción:** Únicamente `pydantic>=2.5.0` y `httpx>=0.25.0`.
- **Compatibilidad total:** Los plugins desarrollados con este SDK pueden integrarse de forma nativa en `jg_agente` mediante entry-points de Python (`jg_agente.plugins`) o ser testeados en aislamiento absoluto.

---

## 2. Instalación

```bash
pip install jg-agente-sdk
```

Para desarrollo local en este repositorio:
```bash
pip install -e jg_agente_sdk
```

---

## 3. Guía de Desarrollo de Plugins

### 3.1 Anatomía de un Plugin

Para crear un plugin compatible, crea una clase que herede de `BasePlugin` e implemente los tres métodos obligatorios:
1. `get_plugin_metadata()`: Devuelve una instancia inmutable de `PluginMetadata`.
2. `register_tools()`: Devuelve la lista de instancias `AgentTool`.
3. `register_engines()`: Devuelve un diccionario con los motores de dominio (`ObserverEngine`, `PlannerEngine`, `VerifierEngine` o `BaseEngine`).

### 3.2 Ejemplo de Implementación

```python
from pydantic import BaseModel, Field
from jg_sdk import (
    BasePlugin,
    PluginMetadata,
    AgentTool,
    ToolResult,
    RiskLevel,
    ToolType,
    BaseEngine,
    ObserverEngine,
)

# 1. Esquema de argumentos con validación estricta de Pydantic
class PingArgs(BaseModel):
    host: str = Field(..., description="Dirección IP o FQDN a comprobar")
    count: int = Field(default=3, ge=1, le=10, description="Número de paquetes")

# 2. Función ejecutable de la herramienta
def execute_ping(host: str, count: int = 3) -> ToolResult:
    # Lógica de comprobación de conectividad
    return ToolResult(
        success=True,
        output=f"Ping exitoso hacia {host} ({count} paquetes recibidos, 0% packet loss).",
        metadata={"host": host, "count": count},
    )

# 3. Motor de dominio cognitivo (Opcional)
class NetworkObserver(ObserverEngine):
    @property
    def name(self) -> str:
        return "network_observer"

# 4. Clase principal del Plugin
class NetworkPlugin(BasePlugin):
    def get_plugin_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="network-diagnostics",
            version="1.0.0",
            description="Herramientas de telemetría y diagnóstico de red.",
            author="Tu Organización",
            jg_agente_version_min="1.0.0",
            tags=["network", "diagnostics"],
        )

    def register_tools(self) -> list[AgentTool]:
        return [
            AgentTool(
                name="ping_host",
                description="Comprueba la latencia y alcanzabilidad de un host remoto.",
                category="network",
                args_schema=PingArgs,
                func=execute_ping,
                risk_level=RiskLevel.LOW,
                tool_type=ToolType.OBSERVER,
                read_only=True,
                timeout_sec=10.0,
            )
        ]

    def register_engines(self) -> dict[str, BaseEngine]:
        return {"network_observer": NetworkObserver()}

    async def startup(self) -> None:
        # Hook asíncrono para inicializar conexiones o recursos
        pass

    async def shutdown(self) -> None:
        # Hook asíncrono para liberar recursos
        pass

    async def health_check(self) -> dict:
        return {"status": "ok", "plugin": self.name}
```

### 3.3 Herramientas Reversibles y Compensaciones (Rollback)

Si tu herramienta realiza mutaciones (`ToolType.MUTATION` o `read_only=False`) y puede revertir sus efectos ante un fallo posterior en el plan de ejecución, regístrala con `reversible=True` y proporciona `rollback_func`:

```python
def deploy_service(service_name: str) -> ToolResult:
    # Despliega el servicio y almacena el estado previo en rollback_context
    return ToolResult(
        success=True,
        output=f"Servicio {service_name} desplegado con ID 123",
        rollback_context={"service_id": "123", "previous_version": "v1"},
    )

def rollback_deploy(rollback_context: dict) -> ToolResult:
    service_id = rollback_context["service_id"]
    # Lógica para revertir a previous_version
    return ToolResult(
        success=True,
        output=f"Servicio {service_id} revertido exitosamente a estado anterior.",
    )

deploy_tool = AgentTool(
    name="deploy_service",
    description="Despliega una nueva versión de un servicio.",
    category="devops",
    func=deploy_service,
    risk_level=RiskLevel.HIGH,
    tool_type=ToolType.MUTATION,
    read_only=False,
    reversible=True,
    rollback_func=rollback_deploy,
)
```

---

## 4. Registro y Empaquetado de Plugins

Para que `jg_agente` descubra automáticamente tu plugin instalado vía `pip`, declara el entry-point en el archivo `pyproject.toml` de tu plugin:

```toml
[project]
name = "jg-plugin-network"
version = "1.0.0"
dependencies = [
    "jg-agente-sdk>=1.0.0",
]

[project.entry-points."jg_agente.plugins"]
network = "jg_plugin_network.plugin:NetworkPlugin"
```

El `PluginManager` del orquestador descubrirá el plugin en tiempo de arranque, validará compatibilidad semántica y resolverá el orden topológico de inicialización.

---

## 5. Testing de Plugins con `MockPluginRunner`

El SDK incluye un arnés de pruebas (`MockPluginRunner`) para validar plugins localmente sin necesidad de levantar FastAPI, LangGraph ni PostgreSQL:

```python
import pytest
from jg_sdk.testing import MockPluginRunner
from jg_plugin_network.plugin import NetworkPlugin, PingArgs

@pytest.mark.asyncio
async def test_network_plugin():
    plugin = NetworkPlugin()

    async with MockPluginRunner(plugin) as runner:
        # 1. Comprobar salud y metadatos
        health = await runner.health_check()
        assert health["status"] == "ok"
        assert runner.metadata.name == "network-diagnostics"

        # 2. Invocación pasando un modelo Pydantic directamente
        res = runner.run_tool("ping_host", PingArgs(host="1.1.1.1", count=2))
        assert res.success is True
        assert "1.1.1.1" in str(res.output)

        # 3. Invocación pasando un diccionario (se valida contra args_schema)
        res_dict = runner.run_tool("ping_host", {"host": "8.8.8.8", "count": 1})
        assert res_dict.success is True
```

---

## 6. Cliente Criptográfico Inter-Servicio (`JGAgentClient`)

Para interactuar con la API REST de `jg_agente`, utiliza el cliente asíncrono `JGAgentClient`. Firma criptográficamente cada petición mediante **HMAC-SHA256** siguiendo el estándar canónico compartido con `jg_dashboard`:

$$\text{canonical\_string} = \text{METHOD} + \text{"\\n"} + \text{PATH} + \text{"\\n"} + \text{TIMESTAMP} + \text{"\\n"} + \text{SHA256(RAW\_BODY)}$$

### Uso del Cliente:

```python
import asyncio
from jg_sdk import JGAgentClient, UserContext

async def main():
    async with JGAgentClient(
        base_url="http://localhost:8000",
        agent_id="agente-principal",
        secret="tu_secreto_permanente_hmac",
    ) as client:
        # 1. Verificar estado de salud
        health = await client.health_check()
        print("Salud del agente:", health)

        # 2. Iniciar una ejecución cognitiva
        user = UserContext(user_id="usr_01", username="admin", role="admin")
        output = await client.execute(
            prompt="Verificar estado de los contenedores en producción",
            user_context=user,
        )

        print(f"Estado de la ejecución: {output.status}")
        print(f"Respuesta del agente: {output.response}")

asyncio.run(main())
```

### Tolerancia Anti-Replay

El protocolo valida que el timestamp emitido en la cabecera `X-Timestamp` no exceda una ventana de desfase de 300 segundos (5 minutos), mitigando ataques de repetición.

---

## 7. Licencia y Modelo Dual (Open Source / Comercial Enterprise)

Este SDK se distribuye bajo un esquema de **Doble Licenciamiento**:

- **Licencia de Código Abierto:** [GNU Affero General Public License v3.0 (AGPL-3.0)](LICENSE) - Copyright (C) 2026 Javier Gálvez.
- **Licencia Comercial Enterprise:** Exención de copyleft para desarrollo corporativo y distribución de plugins propietarios cerrados:
  - **Tarifa:** **200 € / mes** por cada bloque de hasta 3 agentes (sin rappel por volumen).
  - **Mayor volumen:** Si necesita mayor volumen o licenciamiento corporativo global, contacte a través de **[https://javiergalvez.com](https://javiergalvez.com)**.

Para más detalles, consulta [COMMERCIAL_TERMS.md](COMMERCIAL_TERMS.md).


