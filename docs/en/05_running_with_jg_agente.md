# 05. Local Deployment and Execution with `jg_agente`

## 1. Plugin Execution Modes

Plugins authored with `jg_agente_sdk` can be executed in two complementary workflows:
1. **Isolated / Mock Mode (`MockPluginRunner`):** For fast, unit-level validation of tools and engines with zero external dependencies.
2. **Integrated Mode (`jg_agente`):** For end-to-end testing within the LangGraph cognitive loop, intent classification, Human-in-the-Loop (HITL) gates, and multi-turn workflows.

This guide documents the minimal environment configuration required to run a local `jg_agente` runtime attached to your plugin.

---

## 2. Minimal Environment Configuration for `jg_agente`

To boot the agent in local development mode without requiring external databases (PostgreSQL) or control plane servers (`jg_dashboard`), place the following `.env` file in the root of `jg_agente` or export them in your shell:

```env
# ==============================================================================
# MINIMAL PLUGIN DEVELOPMENT ENVIRONMENT FOR jg_agente
# ==============================================================================

# 1. Language & Internationalization (en, es, fr, de, it)
DEFAULT_LOCALE=en

# 2. Plugin Discovery & Loading
PLUGINS_DIR=../plugins
ENABLED_PLUGINS=my_plugin_name

# 3. LLM Provider (Mock or Real API)
LLM_PROVIDER=mock
# For live model testing:
# LLM_PROVIDER=gemini
# LLM_API_KEY=your_api_key_here
# LLM_MODEL=gemini-2.5-flash

# 4. Standalone Mode (Zero dependencies on PostgreSQL or Dashboard)
REQUIRE_DASHBOARD_REGISTRATION=false
CHECKPOINTER_BACKEND=memory
ENABLE_HEARTBEAT=false

# 5. FastAPI Server & Logging
AGENT_ID=dev_plugin_agent
AGENT_PORT=8000
ENV=development
DEBUG=true
```

---

## 3. Configuration Reference

| Variable | Type | Recommended (Dev) | Purpose |
| :--- | :--- | :--- | :--- |
| `DEFAULT_LOCALE` | `str` | `en` \| `es` \| `fr` \| `de` \| `it` | Default language for cognitive directives, prompts, intent classification, and HITL approvals. |
| `PLUGINS_DIR` | `path` | `.` or `../plugins` | Path to directory containing discoverable plugin packages. |
| `ENABLED_PLUGINS` | `str` | `plugin_name` or `*` | Specific plugins to load into the `CapabilityRegistry`. |
| `LLM_PROVIDER` | `str` | `mock` | Language model provider. `mock` runs deterministically at zero cost. |
| `REQUIRE_DASHBOARD_REGISTRATION` | `bool` | `false` | Enables autonomous startup without registering with `jg_dashboard`. |
| `CHECKPOINTER_BACKEND` | `str` | `memory` | Uses in-memory state persistence (`MemorySaver`) rather than PostgreSQL. |
| `ENABLE_HEARTBEAT` | `bool` | `false` | Disables background heartbeat pings to the dashboard. |
| `AGENT_PORT` | `int` | `8000` | HTTP listening port for execution requests. |

---

## 4. Starting the Local Agent

```bash
cd jg_agente

# 1. Create and activate virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt
pip install -e ../jg_agente_sdk
pip install -e /path/to/your/plugin

# 3. Launch agent
python -m app.main
```

---

## 5. Testing Invocations via CLI or HTTP

Using the SDK's CLI:
```bash
# Ping agent health
jg ping --url http://127.0.0.1:8000

# Execute command in English
jg run "Run diagnostics on server" --url http://127.0.0.1:8000 --locale en
```

Using cURL:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/executions \
  -H "Content-Type: application/json" \
  -d '{
    "execution_id": "test-exec-01",
    "thread_id": "test-th-01",
    "prompt": "Run diagnostics on server",
    "locale": "en"
  }'
```

Resolution cascade for `locale`:
$$\text{Request Locale} \;\to\; \text{Plugin Default Locale} \;\to\; \text{Environment DEFAULT\_LOCALE} \;\to\; \text{"es"}$$
