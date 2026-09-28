# AUDITORÍA TÉCNICA — jg_agente_sdk
### Informe de Auditoría de Seguridad, Calidad e Integración · 27 septiembre 2026

---

## Metadatos

| Campo | Valor |
|---|---|
| **Proyecto** | `jg_agente_sdk` — SDK público PyPI para desarrollo de plugins jg_agente |
| **Versión** | 1.0.0 |
| **Fecha** | 27 septiembre 2026 |
| **Alcance** | Código fuente completo: `jg_sdk/cli.py`, `jg_sdk/contracts.py`, `jg_sdk/models.py`, `jg_sdk/client.py`, `jg_sdk/testing.py`, `pyproject.toml`, `tests/` |
| **Metodología** | Inspección de caja blanca directa. Metodología consolidada de auditorías previas (jg_agente + jg_dashboard) |
| **Auditorías de referencia** | `docs/audit-cierre/AUDIT_CIERRE_GLOBAL.md` · `docs/audit-definitiva/AUDIT_GLOBAL_SISTEMA.md` · `audit2/INFORME_COMPARATIVO_AUDITORIAS.md` |

---

## 1. Resumen Ejecutivo

`jg_agente_sdk` es un paquete Python distribuido mediante PyPI con dos responsabilidades diferenciadas:

1. **Contratos públicos** (`contracts.py`, `models.py`): Interfaces y tipos Pydantic para plugins.
2. **CLI de scaffolding** (`cli.py`): Genera estructuras de proyectos de plugins completas, incluyendo `docker-compose.yml`, `.env`, scripts Bash y configuración de PyPI.

El SDK está **bien estructurado** en su parte de contratos. Las familias de riesgos identificadas en auditorías anteriores (shell injection, traversal, secretos hardcodeados) están **sustancialmente mitigadas en el código principal**. Sin embargo, existen problemas reales en el scaffolding generado que requieren corrección antes de la publicación pública en PyPI.

---

## 2. ANÁLISIS DE SEGURIDAD — CLI

### SDK-SEC-01 — ALTO: .env generado inyecta clave API real del desarrollador

**Archivo:** `cli.py:756-775` (detección de clave) + `cli.py:958-966` (escritura)

```python
# Detección (cli.py:756-775)
detected_groq_key = os.environ.get("GLOBAL_GROQ_API_KEY") or os.environ.get("GROQ_API_KEY", "")
# ... búsqueda en .env de directorios padres ...

# Escritura (cli.py:960-961)
env_content = f"""...
GROQ_API_KEY={detected_groq_key}
GLOBAL_GROQ_API_KEY={detected_groq_key}
..."""
(out_dir / ".env").write_text(env_content, encoding="utf-8")
```

**Flujo de explotación:** `jg plugin init my_plugin` → SDK detecta `GROQ_API_KEY` del entorno → La escribe en `.my_plugin/.env` → El desarrollador ejecuta `git init && git add . && git push` sin revisar → Clave API expuesta en repositorio.

**Defensa existente:** `.gitignore` generado excluye `.env`. **No es defensa suficiente:** El desarrollador puede hacer `git add -f .env` o configurar su cliente git de forma diferente.

**Impacto:** Exposición de clave API real de proveedor LLM.

**Recomendación:** El `.env` generado debe tener `GROQ_API_KEY=` (vacío) con comentario explicativo, igual que el `.env.example` generado. Mostrar en consola que se detectó una clave pero no se inyectará en el archivo.

---

### SDK-SEC-04 — ALTO: Escalada de directorios en búsqueda de .env (misma raíz que SDK-SEC-01)

**Archivo:** `cli.py:760`

```python
for env_dir in [out_dir, *out_dir.parents]:
    cand_env = env_dir / ".env"
    if cand_env.is_file():
        # lee y extrae GROQ_API_KEY del .env encontrado
```

Si el desarrollador ejecuta `jg plugin init` desde dentro del monorepo `javiergalvez-ia/`, el scaffold escala hasta encontrar el `.env` raíz (que contiene la clave real del entorno de producción del desarrollador) y la copia al nuevo plugin.

**Escenario concreto:** Desarrollador ejecuta `jg plugin init mi_plugin` desde `/Users/javiergalvez/Documents/Code/javiergalvez-ia/jg_agente_sdk/`. El scaffold sube hasta `/Users/javiergalvez/Documents/Code/javiergalvez-ia/.env` y extrae la clave real.

**Clasificación:** VULNERABILIDAD (filtrado de credenciales a archivos potencialmente versionados).

---

### SDK-SEC-02 — MEDIO: docker-compose.yml generado con credenciales inseguras sin advertencia

**Archivo:** `cli.py:824-839`

```yaml
APP_KEY: "${APP_KEY:-base64:u/pQ9k8q3N0vQzW3mY8l4xJ1t5R6w7y8z9a0b1c2d3E=}"
JG_AGENTE_SECRET: "${JG_AGENTE_SECRET:-secret_dev_token_12345}"
ADMIN_DEFAULT_PASSWORD: "${ADMIN_DEFAULT_PASSWORD:-admin123456}"
PERMANENT_AGENT_SECRET: "${JG_AGENTE_SECRET:-secret_dev_token_12345}"
```

Si el desarrollador despliega el `docker-compose.yml` generado en producción sin definir las variables de entorno, el sistema arranca con credenciales conocidas públicamente en el repositorio del SDK.

**Clasificación:** DEUDA TÉCNICA — funcional para desarrollo, peligroso si se reutiliza sin modificar en producción.

**Recomendación:** Añadir banner en `jg run` advirtiendo que los valores por defecto son solo para desarrollo local.

---

### SDK-SEC-03 — BAJO: artisan tinker ejecuta borrado silencioso en cada jg run

**Archivo:** `cli.py:1163-1179`

```python
subprocess.run(
    [
        "docker",
        "compose",
        "exec",
        "-T",
        "jg_dashboard",
        "php",
        "artisan",
        "tinker",
        "--execute=\\App\\Models\\Agent::where('agent_id', 'a0000000-0000-0000-0000-000000000002')->delete();",
    ],
    cwd=plugin_root,
    capture_output=True,
)
```

Operación DDL silenciosa en cada inicio. La cadena es estática (no hay input de usuario). No es inyección, pero es sorprendente y puede causar confusión.

**Clasificación:** RIESGO OPERATIVO BAJO.

---

### SDK-CLI-01 — MEDIO: `jg dev CMD` ejecuta comandos arbitrarios sin documentación explícita

**Archivo:** `cli.py:1083`

```python
res = subprocess.run(cmd, env=new_env, cwd=plugin_root)
```

`cmd` viene directamente de `args.command` (entrada del usuario). En el uso normal (`jg dev pytest`, `jg dev ruff check .`) esto es correcto. No hay filtering porque es intencional. **El problema es documentación:** el help no indica que este subcomando ejecuta comandos arbitrarios.

**Clasificación:** DEUDA TÉCNICA.

---

## 3. ANÁLISIS DE PACKAGING Y PYPI

### 3.1 Dependencias (pyproject.toml)

```toml
dependencies = [
    "pydantic>=2.5.0",
    "httpx>=0.25.0",
]
```

**Evaluación:** Mínimas y correctas. Sin rangos excesivamente anchos ni paquetes abandonados.

### 3.2 Archivos publicados

```toml
[tool.setuptools.packages.find]
where = ["."]
include = ["jg_sdk*"]
exclude = ["tests*"]
```

**Evaluación:** Tests excluidos correctamente. No hay riesgo de publicar archivos sensibles (`.env`, credenciales, etc.) porque no hay `MANIFEST.in` que los incluya. Los directorios `dist/` y `*.egg-info/` son artefactos locales no distribuidos.

### SDK-PKG-01 — INFO: Classifier "Production/Stable" prematuro

`Development Status :: 5 - Production/Stable` en v1.0.0 de un SDK en ecosistema en desarrollo activo puede crear expectativas incorrectas. Clasificación: MEJORA DE PRODUCTO.

---

## 4. ANÁLISIS DEL CLIENTE HMAC (client.py)

La implementación HMAC es correcta y simétrica con la del ecosistema:

| Aspecto | Estado |
|---|---|
| Comparación en tiempo constante | ✅ `hmac.compare_digest` |
| Ventana anti-replay 300s | ✅ Implementado |
| Normalización de método HTTP | ✅ `.upper()` en firma y petición |
| Extracción de path de URLs completas | ✅ `urlparse` |
| Comparación case-insensitive | ✅ `.lower()` en ambos lados |
| Anti-replay con nonces | ❌ No implementado (consistente con todo el ecosistema — ACEPTADO) |

---

## 5. ANÁLISIS DE CONTRATOS (contracts.py, models.py)

### 5.1 Correctos

- `AgentTool.run()` implementa timeout mediante `ThreadPoolExecutor` — correcta para funciones síncronas.
- Validadores de `func` y `rollback_func` verifican que sean callables.
- `PluginMetadata` usa `frozen=True` — es inmutable post-creación.
- `BasePlugin` es correctamente abstracta con `@abstractmethod`.

### 5.2 Observaciones no bloqueantes

- `ToolResult` con `extra="allow"` es flexible pero no valida campos adicionales. Aceptado por diseño.
- `UserContext.permissions` acepta cualquier lista de strings sin validación semántica. El runtime es responsable de la validación RBAC.

---

## 6. ANÁLISIS DE TESTS

| Suite | Cobertura | Calidad |
|---|---|---|
| `test_contracts.py` | AgentTool, ToolResult, PluginMetadata, engines | Buena — cubre validadores y edge cases |
| `test_client_hmac.py` | Firma HMAC, anti-replay, casos límite | Muy buena — cubre timestamp fuera de ventana, firma incorrecta |
| `test_cli.py` | Scaffold con templates minimal/standard/full | Buena — verifica estructura generada |
| `test_plugin_example.py` | Plugin completo con MockPluginRunner | Buena — demuestra flujo correcto |

**SDK-TEST-01 — INFO:** No hay test que verifique que el `.env` generado no contiene claves API reales. Dado SDK-SEC-01, este test sería útil para prevenir regresiones.

---

## 7. INTEGRACIÓN SDK → RUNTIME

| Aspecto | Estado |
|---|---|
| Contrato BasePlugin | ✅ Simétrico con runtime |
| Entry points PyPI `jg_agente.plugins` | ✅ Formato correcto |
| `PLUGIN_CLASS` para autodescubrimiento local | ✅ Consistente con plugin real |
| Formato AgentInput/AgentOutput | ✅ Compatible con API del agente |
| Firma HMAC del cliente | ✅ Compatible con autenticación del agente |

---

## 8. TABLA DE ISSUES

| ID | Severidad | Categoría | Requiere corrección antes de publicar |
|---|---|---|---|
| SDK-SEC-01 | **ALTO** | VULNERABILIDAD | **SÍ — BLOQUEANTE** |
| SDK-SEC-04 | **ALTO** | VULNERABILIDAD | **SÍ — misma raíz que SDK-SEC-01** |
| SDK-SEC-02 | MEDIO | DEUDA TÉCNICA | Documentar antes de publicar |
| SDK-CLI-01 | MEDIO | DEUDA TÉCNICA | Documentar en próxima iteración |
| SDK-SEC-03 | BAJO | RIESGO OPERATIVO | No bloqueante |
| SDK-PKG-01 | INFO | MEJORA | No bloqueante |
| SDK-HMAC-01 | INFO | ACEPTADO POR DISEÑO | No aplica |
| SDK-TEST-01 | INFO | DEUDA TÉCNICA | Deseable |

---

## 9. DECISIÓN

```
CORREGIR 1 COSA Y PUBLICAR
```

**Corrección bloqueante (SDK-SEC-01 + SDK-SEC-04):** El scaffold no debe inyectar claves API reales en `.env` generado. Solución: generar `.env` con los mismos valores vacíos que `.env.example`. Eliminar o deshabilitar la búsqueda de claves en directorios padres, o convertirla en opt-in con confirmación explícita del usuario.

El resto del SDK (contratos, cliente HMAC, tests, packaging) está listo para producción.

---

*Auditoría realizada mediante inspección directa del código fuente. Referencias a líneas exactas de `cli.py`.*
