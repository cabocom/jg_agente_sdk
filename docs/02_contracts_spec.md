# 02. Especificación de Contratos y Modelos Canónicos (`jg_agente_sdk`)

Este documento constituye la **Fuente Única de Verdad (Single Source of Truth - SSOT)** de las interfaces públicas del ecosistema agéntico jG.

---

## 1. Tipologías y Enums Operacionales

### 1.1 `RiskLevel` (`jg_sdk.contracts`)
- `low`: Operaciones de solo lectura o consultas sin impacto ambiental.
- `medium`: Invocaciones que alteran estados temporales sin riesgo destructivo.
- `high`: Mutaciones de configuración, despliegues o escrituras sensibles. Provoca pausa HITL obligatoria.
- `critical`: Modificaciones irreversibles, eliminación de recursos o reinicios de servicio. Provoca pausa HITL obligatoria.

### 1.2 `ToolType` (`jg_sdk.contracts`)
- `observer`: Sensores y recolectores de telemetría de entorno.
- `actuator`: Accionadores que efectúan operaciones sobre sistemas externos.
- `verifier`: Motores de comprobación de post-condiciones.
- `read`: Herramientas de consulta de datos puros.
- `mutation`: Herramientas con efectos secundarios directos.

### 1.3 `ExecutionStatus` (`jg_sdk.contracts`)
- `in_progress`: Tarea actualmente en ejecución.
- `completed`: Tarea finalizada exitosamente.
- `waiting_approval`: Pausada en el nodo `human_approval` por riesgo operacional.
- `failed`: Tarea concluida con error irrecuperable.
- `cancelled`: Tarea rechazada por operador o cancelada deliberadamente.
- `timeout`: Tarea que excedió la ventana temporal límite.

---

## 2. Contratos de Capacidades (`jg_sdk.contracts`)

### 2.1 `AgentTool`
| Campo | Tipo | Requerido | Descripción |
| :--- | :--- | :---: | :--- |
| `name` | `str` | Sí | Nombre canónico de la herramienta (min. 1 char). |
| `description` | `str` | Sí | Descripción funcional detallada para el LLM. |
| `category` | `str` | No (def: `"general"`) | Categoría taxonómica. |
| `version` | `str` | No (def: `"1.0.0"`) | Versión semántica de la herramienta. |
| `args_schema` | `type[BaseModel] \| None` | No | Esquema tipado Pydantic de argumentos. |
| `func` | `Callable[..., Any]` | Sí | Función invocable (síncrona o asíncrona). |
| `risk_level` | `RiskLevel` | No (def: `LOW`) | Nivel de riesgo asignado. |
| `required_permissions` | `list[str]` | No (def: `[]`) | Permisos RBAC requeridos para ejecución. |
| `tool_type` | `ToolType` | No (def: `OBSERVER`)| Clasificación funcional. |
| `read_only` | `bool` | No (def: `True`) | Declara ausencia de efectos secundarios. |
| `reversible` | `bool` | No (def: `False`) | Declara capacidad de compensación ante fallos. |
| `idempotent` | `bool` | No (def: `True`) | Idempotencia ante ejecuciones repetidas. |
| `makes_http_requests` | `bool` | No (def: `False`) | Sujeto a inspección estricta de SSRF. |
| `allow_failure` | `bool` | No (def: `False`) | Si es True, su fallo no interrumpe el plan. |
| `timeout_sec` | `float` | No (def: `30.0`) | Límite temporal duro de invocación. |
| `rollback_func` | `Callable[[dict], ToolResult] \| None` | Condicional | Compensador (obligatorio si `reversible=True`). |

### 2.2 `ToolResult`
- `success` (`bool`): Indicador de éxito de la operación.
- `output` (`Any`): Resultado textual o estructurado para el razonador.
- `error` (`str | None`): Mensaje descriptivo si `success=False`.
- `duration_ms` (`float`): Latencia observada en milisegundos.
- `metadata` (`dict[str, Any]`): Información complementaria de telemetría.
- `rollback_context` (`dict[str, Any] | None`): Estado requerido para una reversión posterior.

---

## 3. Contratos de Comunicación (`jg_sdk.models`)

### 3.1 `AgentInput`
Estímulo normalizado de entrada:
- `execution_id` (`str`): Identificador único de la ejecución.
- `thread_id` (`str`, alias: `session_id`): Identificador del hilo conversacional.
- `correlation_id` (`str | None`): Identificador de traza distribuida.
- `prompt` (`str`, alias: `message`): Instrucción o texto de entrada.
- `parameters` (`dict[str, Any]`): Parámetros complementarios.
- `user_context` (`UserContext | None`): Identidad, rol y permisos del usuario.
- `metadata` (`dict[str, Any]`): Metadatos adicionales de auditoría.
- `callback_url` (`str | None`): URL para notificación asíncrona vía webhook.

### 3.2 `AgentOutput`
Respuesta estructurada emitida por el runtime:
- `execution_id`, `thread_id`, `correlation_id`.
- `status` (`ExecutionStatus`).
- `response` (`str`, alias: `answer`): Mensaje final sintetizado.
- `data` (`dict[str, Any] | None`): Carga de datos o artefactos.
- `execution_time_ms` (`float`): Duración total en milisegundos.
- `requires_approval` (`bool`) y `pending_approval_id` (`str | None`).
- `error` (`str | None`) y `metadata` (`dict[str, Any]`).
- `completed_at` (`datetime`).
