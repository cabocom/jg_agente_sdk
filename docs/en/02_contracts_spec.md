# 02. Canonical Contracts and Models Specification (`jg_agente_sdk`)

This document serves as the **Single Source of Truth (SSOT)** for all public interfaces in the jG agent ecosystem.

---

## 1. Typologies & Operational Enums

### 1.1 `RiskLevel` (`jg_sdk.contracts`)
- `low`: Read-only queries or harmless operations.
- `medium`: Operations mutating transient state without catastrophic impact.
- `high`: Configuration updates, deployments, or sensitive writes. Triggers mandatory HITL pause.
- `critical`: Irreversible operations, resource destruction, or service halts. Triggers mandatory HITL pause.

### 1.2 `ToolType` (`jg_sdk.contracts`)
- `observer`: Environmental sensors and telemetry gatherers.
- `actuator`: Actuators performing operations on external systems.
- `verifier`: Post-condition and verification engines.
- `read`: Pure data inspection tools.
- `mutation`: Tools with direct side effects.

### 1.3 `ExecutionStatus` (`jg_sdk.contracts`)
- `in_progress`: Task is currently executing.
- `completed`: Task finished successfully.
- `waiting_approval`: Suspended at `human_approval` node due to risk level.
- `failed`: Task halted due to an unrecoverable error.
- `cancelled`: Rejected by operator or explicitly cancelled.
- `timeout`: Task exceeded max runtime threshold.

---

## 2. Capability Contracts (`jg_sdk.contracts`)

### 2.1 `AgentTool`
| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `name` | `str` | Yes | Canonical tool identifier (min. 1 char). |
| `description` | `str` | Yes | Detailed functional explanation for LLMs. |
| `category` | `str` | No (def: `"general"`) | Taxonomic category. |
| `version` | `str` | No (def: `"1.0.0"`) | Semantic tool version. |
| `args_schema` | `type[BaseModel] \| None` | No | Pydantic typed input schema. |
| `func` | `Callable[..., Any]` | Yes | Callable function (sync or async). |
| `risk_level` | `RiskLevel` | No (def: `LOW`) | Operational risk level. |
| `required_permissions` | `list[str]` | No (def: `[]`) | RBAC permissions required. |
| `tool_type` | `ToolType` | No (def: `OBSERVER`)| Functional classification. |
| `read_only` | `bool` | No (def: `True`) | Declares zero side-effects. |
| `reversible` | `bool` | No (def: `False`) | Declares rollback capability on failure. |
| `idempotent` | `bool` | No (def: `True`) | Safe to re-run with identical parameters. |
| `makes_http_requests` | `bool` | No (def: `False`) | Enforces SSRF and DNS pinning checks. |
| `allow_failure` | `bool` | No (def: `False`) | If True, failure does not break the plan. |
| `timeout_sec` | `float` | No (def: `30.0`) | Hard execution timeout in seconds. |
| `rollback_func` | `Callable[[dict], ToolResult] \| None` | Conditional | Rollback handler (required if `reversible=True`). |

### 2.2 `ToolResult`
- `success` (`bool`): Operation outcome indicator.
- `output` (`Any`): Textual or structured result for the reasoning node.
- `error` (`str | None`): Error description if `success=False`.
- `duration_ms` (`float`): Latency in milliseconds.
- `metadata` (`dict[str, Any]`): Telemetry and debug info.
- `rollback_context` (`dict[str, Any] | None`): State preserved for potential Saga rollback.

### 2.3 `PluginMetadata`
- `name` (`str`): Unique package name.
- `version` (`str`): SemVer string.
- `description` (`str`): Plugin overview.
- `author` (`str`): Maintainer identity.
- `supported_locales` (`list[str]`): Supported interaction languages (e.g. `["en", "es"]`).
- `default_locale` (`str | None`): Native locale preference for prompts and tools.
- `tags` (`list[str]`): Discoverability tags.

---

## 3. Communication Contracts (`jg_sdk.models`)

### 3.1 `AgentInput`
Normalized input payload:
- `execution_id` (`str`): Unique execution UUID.
- `thread_id` (`str`, alias: `session_id`): Conversation or thread identifier.
- `correlation_id` (`str | None`): Distributed tracing ID (`X-Correlation-ID`).
- `prompt` (`str`, alias: `message`): Normalized user command.
- `locale` (`str`, def: `"es"`): Interaction language code (`'es'`, `'en'`, `'fr'`, `'de'`, `'it'`).
- `parameters` (`dict[str, Any]`): Additional context parameters.
- `user_context` (`UserContext | None`): User identity, roles, and permissions.
- `metadata` (`dict[str, Any]`): Audit metadata.
- `callback_url` (`str | None`): Target for async webhook delivery.

### 3.2 `AgentOutput`
Structured agent response:
- `execution_id`, `thread_id`, `correlation_id`.
- `status` (`ExecutionStatus`).
- `response` (`str`, alias: `answer`): Final synthesised output.
- `data` (`dict[str, Any] | None`): Structured payload or artifacts.
- `execution_time_ms` (`float`): End-to-end runtime duration in milliseconds.
- `requires_approval` (`bool`) & `pending_approval_id` (`str | None`).
- `error` (`str | None`) & `metadata` (`dict[str, Any]`).
- `completed_at` (`datetime`).
