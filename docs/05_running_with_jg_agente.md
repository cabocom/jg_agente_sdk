# 05. Despliegue Local y Ejecución con `jg_agente`

## 1. Contexto de Ejecución de Plugins

Los plugins desarrollados con `jg_agente_sdk` pueden ejecutarse en dos modalidades complementarias:
1. **Modo Aislado / Mock (`MockPluginRunner`):** Para pruebas unitarias rápidas de herramientas y motores sin dependencias externas.
2. **Modo Integrado con el Core (`jg_agente`):** Para probar el ciclo cognitivo completo de razonamiento LangGraph, resolución de intenciones, compuertas de seguridad HITL (Human-In-The-Loop) y paridad de contratos.

Esta guía documenta la configuración mínima requerida para que un desarrollador levante una instancia local de `jg_agente` vinculada a su plugin.

---

## 2. Variables de Entorno Mínimas para Levantar `jg_agente`

Para ejecutar el agente en modo desarrollo sin requerir bases de datos externas (PostgreSQL) ni la consola central (`jg_dashboard`), se debe proveer el siguiente archivo `.env` en la raíz de `jg_agente` o en el entorno de ejecución:

```env
# ==============================================================================
# CONFIGURACIÓN MÍNIMA DE DESARROLLO DE PLUGINS EN jg_agente
# ==============================================================================

# 1. Internacionalización e Idioma del Runtime (ES, EN, FR, DE, IT)
DEFAULT_LOCALE=es

# 2. Descubrimiento y Carga de Plugins
PLUGINS_DIR=../plugins
ENABLED_PLUGINS=mi_plugin_nombre

# 3. Proveedor LLM para Pruebas (Mock o API Real)
LLM_PROVIDER=mock
# Para pruebas con modelo real:
# LLM_PROVIDER=gemini
# LLM_API_KEY=tu_api_key_aqui
# LLM_MODEL=gemini-2.5-flash

# 4. Modo Desacoplado (Sin dependencias de PostgreSQL ni Dashboard)
REQUIRE_DASHBOARD_REGISTRATION=false
CHECKPOINTER_BACKEND=memory
ENABLE_HEARTBEAT=false

# 5. Servidor FastAPI y Logs
AGENT_ID=dev_plugin_agent
AGENT_PORT=8000
ENV=development
DEBUG=true
```

---

## 3. Descripción Detallada de Parámetros

| Variable | Tipo | Valor Recomendado (Dev) | Propósito |
| :--- | :--- | :--- | :--- |
| `DEFAULT_LOCALE` | `str` | `es` \| `en` \| `fr` \| `de` \| `it` | Define el idioma por defecto para directivas de razonamiento, clasificación y aprobaciones HITL. |
| `PLUGINS_DIR` | `path` | `.` o `../plugins` | Ruta al directorio donde residen los paquetes de plugins para autodescubrimiento. |
| `ENABLED_PLUGINS` | `str` | `nombre_del_plugin` o `*` | Filtro de plugins a registrar en el `CapabilityRegistry`. |
| `LLM_PROVIDER` | `str` | `mock` | Motor de lenguaje. `mock` no realiza llamadas externas ni incurre en costes; `gemini` u `openai` ejecutan inferencia real. |
| `REQUIRE_DASHBOARD_REGISTRATION` | `bool` | `false` | Permite el arranque autónomo sin buscar ni autenticar contra `jg_dashboard`. |
| `CHECKPOINTER_BACKEND` | `str` | `memory` | Utiliza `MemorySaver` en RAM para LangGraph en lugar de requerir PostgreSQL. |
| `ENABLE_HEARTBEAT` | `bool` | `false` | Desactiva el hilo de fondo de telemetría hacia el dashboard. |

---

## 4. Internacionalización (i18n) a Nivel de Plugin y Petición

### A. Declaración en el Plugin (`PluginMetadata`)
Un plugin puede indicar en sus metadatos los idiomas que soporta y su idioma preferido:

```python
from jg_sdk.contracts import BasePlugin, PluginMetadata


class MiPlugin(BasePlugin):
    def get_plugin_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="mi_plugin",
            version="1.0.0",
            description="Herramientas de automatización",
            supported_locales=["es", "en", "fr"],
            default_locale="en",
        )
```

Si el agente se inicia cargando este plugin y no se especificó `DEFAULT_LOCALE` en el entorno, adoptará automáticamente el `default_locale` declarado por el plugin (`en`).

### B. Especificación en la Petición (`AgentInput`)
El invocador (Swagger, CLI, tests o clientes HTTP) puede solicitar un idioma específico por cada ejecución:

```json
POST /api/v1/executions
{
  "execution_id": "exec_001",
  "thread_id": "session_001",
  "prompt": "List available server metrics",
  "locale": "en"
}
```

La jerarquía de resolución es:
$$\text{Locale de la Petición} \;\to\; \text{Locale del Plugin} \;\to\; \text{DEFAULT\_LOCALE de entorno} \;\to\; \text{"es"}$$
