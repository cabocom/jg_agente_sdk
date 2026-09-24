# jg-agente-sdk

[![PyPI version](https://img.shields.io/pypi/v/jg-agente-sdk.svg?color=blue&logo=pypi&logoColor=white)](https://pypi.org/project/jg-agente-sdk/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-7928CA.svg)](LICENSE)
[![Type Checked: mypy](https://img.shields.io/badge/types-mypy-blue.svg)](https://mypy-lang.org/)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Architecture: Open Core](https://img.shields.io/badge/architecture-Open_Core-green.svg)](#1-visión-y-frontera-arquitectónica-open-core)

> **SDK desacoplado, contratos canónicos y CLI de desarrollo para el ecosistema de agentes cognitivos javiergalvez-ia.**

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

Para desarrollo local o si has clonado el repositorio del SDK:
```bash
cd jg_agente_sdk
pip install -e .
```

> **¿Cómo se ejecuta el comando `jg`?**
> Al instalar el SDK (`pip install jg-agente-sdk` o `pip install -e .`), `pip` registra automáticamente el binario ejecutable `jg` (y su alias `jg-sdk`) en tu `$PATH`. Puedes verificarlo de inmediato ejecutando:
> ```bash
> jg --help
> ```

---

## 3. Herramienta de Línea de Comandos (`jg` CLI)

El SDK proporciona la CLI `jg` diseñada bajo la filosofía *"menos es más"*: una interfaz minimalista, moderna y de alto impacto para desarrolladores de plugins y operadores de agentes.

### Resumen de Comandos Principales

| Comando | Propósito | Ejemplo |
| :--- | :--- | :--- |
| `jg init <nombre>` | Inicializa la estructura completa de un nuevo plugin listo para producción. | `jg init monitoring -t standard` |
| `jg run` | Levanta el stack autónomo Docker Compose (Dashboard :8880, Agente :8881). | `jg run` / `jg run -l` / `jg run --down` |
| `jg reload [target]`| Recarga en caliente los plugins de los agentes en ejecución sin reiniciar PostgreSQL ni Dashboard. | `jg reload` / `jg reload devops` |
| `jg status` | Inspecciona el estado de salud en tiempo real de todos los agentes y el Dashboard. | `jg status` |
| `jg test` | Ejecuta la suite de tests unitarios del plugin con Pytest en el entorno virtual. | `jg test` / `jg test -v` |
| `jg dev` | Lanza una subshell o ejecuta herramientas (`ruff`, `mypy`) dentro del entorno `.venv`. | `jg dev` / `jg dev ruff check .` |

---

### 3.1 Inicialización de Plugins (`jg init`)

Genera un plugin estructurado con schemas Pydantic, tests unitarios con `MockPluginRunner` y `docker-compose.yml` autónomo:

```bash
# Plugin estándar con tools + observer + compensación reversible
jg init mi_herramienta

# Plantillas disponibles:
jg init network_monitor --template standard --author "Mi Organización"
jg init simple_lookup   --template minimal
jg init complex_ops     --template full --path ./custom_dir/
```

- `-t, --template [minimal|standard|full]`:
  - `minimal`: Herramientas básicas de solo lectura (`ToolType.READ`).
  - `standard` (por defecto): Herramientas tipadas, motor `ObserverEngine` y función de reversión (`rollback_func`).
  - `full`: Suite completa con `ObserverEngine`, `PlannerEngine`, `VerifierEngine` y herramientas mutacionales.

---

### 3.2 Despliegue Local Autónomo en Docker (`jg run`)

Permite probar y validar el plugin dentro de un entorno Docker idéntico al de producción:

```bash
# Iniciar stack Docker Compose (Dashboard web en :8880, Agente en :8881)
jg run

# Ver logs en tiempo real
jg run -l

# Ver estado de los contenedores
jg run -s

# Detener el entorno Docker
jg run --down
```

---

### 3.3 Recarga en Caliente (`jg reload`)

Cuando realizas cambios en el código de tu plugin, no necesitas reiniciar las bases de datos ni el Dashboard. Ejecuta:

```bash
# Recargar todos los agentes activos
jg reload

# Recargar un agente específico
jg reload conversacional
jg reload devops
jg reload datosgob
```

El comando reinicia el proceso del agente en ~2 segundos, espera a que responda en `/health` y consulta `/capabilities` para confirmar que las nuevas herramientas han sido registradas.

---

### 3.4 Chequeo de Salud y Diagnóstico (`jg status`)

Muestra una panorámica instantánea del estado de los servicios y las capacidades activas:

```bash
jg status
```

Salida esperada:
```text
=================================================================
🩺 Estado de Servicios y Runtimes (javiergalvez-ia)
=================================================================
  ✅ Dashboard (Control Plane)      ONLINE  (http://localhost:8080/up)
  ✅ Dashboard Autónomo             ONLINE  (http://localhost:8880/up)
  ✅ Agente Conversacional          ONLINE  (http://localhost:8001/health)
     └─► Plugins: 1 | Herramientas: 2 | Motores: 0
  ✅ Agente DevOps                  ONLINE  (http://localhost:8002/health)
     └─► Plugins: 1 | Herramientas: 4 | Motores: 3
  ✅ Agente Datos Gob               ONLINE  (http://localhost:8881/health)
     └─► Plugins: 1 | Herramientas: 2 | Motores: 0
=================================================================
```

---

## 4. Guía de Desarrollo de Plugins

### 4.1 Anatomía de un Plugin

Para crear un plugin compatible, crea una clase que herede de `BasePlugin` e implemente los tres métodos obligatorios:
1. `get_plugin_metadata()`: Devuelve una instancia inmutable de `PluginMetadata`.
2. `register_tools()`: Devuelve la lista de instancias `AgentTool`.
3. `register_engines()`: Devuelve un diccionario con los motores de dominio (`ObserverEngine`, `PlannerEngine`, `VerifierEngine` o `BaseEngine`).

### 4.2 Ejemplo de Implementación

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

## 5. Registro y Empaquetado de Plugins

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

## 6. Testing de Plugins con `MockPluginRunner`

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

## 7. Cliente Criptográfico Inter-Servicio (`JGAgentClient`)

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

## 8. Licencia y Modelo Dual (Open Source / Comercial Enterprise)

Este SDK se distribuye bajo un esquema de **Doble Licenciamiento**:

- **Licencia de Código Abierto:** [GNU Affero General Public License v3.0 (AGPL-3.0)](LICENSE) - Copyright (C) 2026 Javier Gálvez.
- **Licencia Comercial Enterprise:** Exención de copyleft para desarrollo corporativo y distribución de plugins propietarios cerrados:
  - **Tarifa:** **200 € / mes** por cada bloque de hasta 3 agentes (sin rappel por volumen).
  - **Mayor volumen:** Si necesita mayor volumen o licenciamiento corporativo global, contacte a través de **[https://javiergalvez.com](https://javiergalvez.com)**.

Para más detalles, consulta [COMMERCIAL_TERMS.md](COMMERCIAL_TERMS.md).


