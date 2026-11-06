# 03. Command Line Interface Reference (`jg` / `jg-sdk-cli`)

The SDK bundles the official CLI utility `jg` (`jg-sdk-cli`) for standardized scaffolding, static inspection, contract verification, and plugin development.

---

## 1. Generating New Plugins (`new`)

Generates a structured plugin package with packaging configuration, typed unit tests, and entry points:

```bash
jg new [OPTIONS] NAME
```

### Arguments & Options:
- `NAME`: Plugin name (e.g. `monitoring` or `jg_plugin_monitoring`).
- `--target-dir PATH`: Target directory to create the project.
- `--template {minimal, standard, full}`:
  - `minimal`: Barebones structure with a single tool.
  - `standard` (default): Includes tools, Pydantic schemas, and unit tests with `pytest`.
  - `full`: Includes reversible tools with `rollback_func`, `ObserverEngine`/`VerifierEngine`, and comprehensive tests.
- `--author TEXT`: Author name or team (default: `"Development Team"`).
- `--description TEXT`: Functional plugin summary.
- `--force`: Overwrites destination files if target directory exists.

### Example:
```bash
jg new sdr_connector --template full --author "Engineering Team"
```

---

## 2. Static Plugin Inspection (`inspect`)

Loads and inspects metadata, tools, argument schemas, and registered engines from a local plugin directory:

```bash
jg inspect ./jg_plugin_datosgob
```

---

## 3. Contract & Safety Verification (`verify`)

Runs automated validation over a plugin package to ensure compliance with Core safety guardrails:
- Verifies that any tool with `reversible=True` provides a valid `rollback_func`.
- Validates that `timeout_sec` is strictly positive and finite.
- Verifies that tool descriptions are non-empty and descriptive for LLM function calling.
- Checks that tool and plugin identifiers follow valid alphanumeric `snake_case` conventions.

---

## 4. Dynamic Symlink Management (`link` / `unlink`)

Easily link and unlink external plugins under development into an active agent instance using portable relative symlinks:

```bash
# Link plugin to agent runtime
jg link ./my_custom_plugin --agent-dir ../jg_agente

# Unlink when done
jg unlink my_custom_plugin --agent-dir ../jg_agente
```
