# 06. Plugin Modes and Lifecycle

This guide documents the execution models available for developing plugins with `jg_agente_sdk` and explains the standardized lifecycle for development, inspection, and clean teardown using the `jg` CLI.

---

## 1. Architecture Philosophy & Decoupling

Plugins developed with `jg_agente_sdk` are pure Python libraries implementing capability contracts (`AgentTool`, `BaseEngine`, `BasePlugin`). For cognitive inference and execution, they rely on the `jg_agente` runtime powered by FastAPI and LangGraph.

The SDK supports two complementary operating modes:

```text
+---------------------------------------------------------------------------------+
|                                 OPERATING MODES                                 |
+---------------------------------------------------------------------------------+
|  MODE 1: STANDALONE                         MODE 2: SHARED (Monorepo)           |
|                                                                                 |
|  +------------------------------+          +---------------------------------+  |
|  | jg_plugin_<name>             |          | jg_agente (Central Runtime)     |  |
|  |  - Own docker-compose.yml    |          |  - plugins/                     |  |
|  |    * jg_dashboard (:8880)    |          |    └── symlink -> jg_plugin_... |  |
|  |    * jg_agente (:8881)       |          +---------------------------------+  |
|  |    * Internal PostgreSQL     |                                               |
|  +------------------------------+          Plugins coexist linked               |
|                                            in a single runtime.                 |
|  Isolated per-plugin stack.                Ideal for global integration.        |
|  Start with 'jg run'.                      Link with 'jg link'.                 |
+---------------------------------------------------------------------------------+
```

---

## 2. The Two Operating Modes

### Mode 1: Standalone

In standalone mode, the plugin has its own isolated environment orchestrated by a `docker-compose.yml` file generated during `jg init`.

- **Local Control Plane:** Web HITL Panel at `http://localhost:8880/admin` (`admin@local.test` / `admin123456`).
- **Local Execution Plane:** Dedicated `jg_agente` runtime at `http://localhost:8881`.
- **Isolated Storage:** PostgreSQL in a private Docker bridge network.

#### Key Commands in Standalone Mode:
```bash
# Start standalone stack in background
jg run

# Follow real-time logs
jg run -l

# Check service status
jg run -s

# Stop standalone stack
jg run --down
```

### Mode 2: Shared / Integrated (Monorepo)

In shared mode, the plugin links directly to an active `jg_agente` instance using **portable relative symlinks** in `plugins/`.

#### Key Commands in Shared Mode:
```bash
# Link plugin to agent runtime
jg link

# Hot-reload agent plugins without restarting databases
jg reload

# Unlink plugin
jg unlink <plugin_name>
```

---

## 3. Contextual Inspection with `jg status`

`jg status` adapts dynamically to the current working directory:

1. **Inside a plugin directory (`jg_plugin_*`):**
   Inspects only **this specific plugin**:
   - Detects Standalone vs Shared mode.
   - Checks symlink status in `jg_agente/plugins/`.
   - Queries Docker for associated containers.
   - Performs HTTP healthcheck (`/health`) and capability inspection (`/capabilities`).
   - Diagnoses whether the plugin is `🟢 CLEAN` (safe to delete/archive) or `🟠 IN USE`.

2. **Outside a plugin directory (or with `-g` / `--global`):**
   Inspects the global ecosystem status (`jg_hub`, `jg_dashboard`, cognitive agents, and databases).

---

## 4. Teardown & Clean with `jg clean`

The `jg clean` command (also available as `jg plugin clean`) unifies cleanup into a single step:

```bash
# Clean plugin in current directory
jg clean

# Clean specific plugin by name from anywhere
jg clean <plugin_name>

# Also remove .venv directory
jg clean --all
```

### Deterministic actions executed by `jg clean`:
1. **Docker Compose Teardown:** Runs `docker compose down` if local compose file exists.
2. **Container Removal:** Stops and removes associated containers (`jg_agente_<slug>`, etc.).
3. **Safe Unlink:** Deletes symlinks from `jg_agente/plugins/`.
4. **Cache Purge:** Removes `__pycache__`, `.pytest_cache`, `.ruff_cache`, and `.egg-info` directories (and `.venv` with `--all`).
5. **Safety Certificate:** Confirms the repository can be safely archived or removed with `rm -rf`.

