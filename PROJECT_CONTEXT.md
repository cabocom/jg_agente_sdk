# CONTEXTO DE PROYECTO: jg_agente_sdk

**Versión del documento:** 1.1.1  
**Fecha de consolidación:** 7 de noviembre de 2026  
**Componente:** SDK Público de Desarrollo y Biblioteca Cliente (Plugin Development & Execution Client)  
**Stack Tecnológico:** Python >= 3.11, Pydantic v2, HTTPX, Setuptools, Ruff, Pytest  
**Estado:** Producción / Consolidado como Fuente Única de Verdad (SSOT).  
- **Fuente Única de Verdad (SSOT):** Define todos los contratos públicos canónicos del ecosistema (`AgentTool`, `ToolResult`, `RiskLevel`, `ToolType`, `ExecutionStatus`, `BasePlugin`, `BaseEngine`, `PluginMetadata`, `AgentInput`, `AgentOutput`).
- **Soporte de Internacionalización (i18n):**
  * `AgentInput`: Campo `locale: str = Field(default="es")` para propagar el idioma de la interacción.
  * `PluginMetadata`: Campos `supported_locales: list[str] = Field(default_factory=lambda: ["es"])` y `default_locale: Optional[str] = None` para declarar idiomas nativos del plugin.
- **Guía de Variables de Entorno del Agente (`docs/es/05_running_with_jg_agente.md` / `docs/en/05_running_with_jg_agente.md`):** Documentación exhaustiva de las variables mínimas para que un desarrollador de plugins levante un runtime de `jg_agente` en local.
- **Modos de Trabajo y Ciclo de Vida (`docs/es/06_plugin_modes_and_lifecycle.md` / `docs/en/06_plugin_modes_and_lifecycle.md`):** Especificación completa de los modos de trabajo con plugins (Autónomo vs Compartido) y ciclo de vida de desarrollo, inspección contextual y desmantelamiento limpio.
- **Desacoplamiento Absoluto:** Cero dependencias de frameworks pesados (sin LangChain, LangGraph, FastAPI, SQLAlchemy ni bases de datos).
- **Tipado Estricto (PEP 561):** Incluye marcador `py.typed` para autocompletado y validación estática transparente con MyPy en cualquier consumidor.
- **Herramienta de Línea de Comandos (`jg` / `jg-sdk`):** CLI integrado para invocación interactiva de agentes, ping de salud, inspección de capacidades, soporte de parámetros descriptivos, scaffolding seguro (`jg plugin init`), alertas de credenciales de desarrollo y saneamiento de BD documentado (`jg run`), ejecución flexible en `.venv` (`jg dev`), vinculación segura de plugins (`jg link` / `jg unlink`), empaquetado de imágenes Docker inmutables (`jg plugin build` / `jg build`), inspección contextual de plugins vs ecosistema (`jg status`), y desmantelamiento limpio y determinista (`jg clean` / `jg plugin clean`).
- **Cliente HTTP con Firma HMAC-SHA256:** `AgentClient` implementa la especificación criptográfica de firma simétrica canónica y prevención de replay attacks requerida por `jg_agente`.
- **Suite de Calidad Automatizada:** Script de validación `scripts/check.sh` con Ruff (linter y formateo) y Pytest pasando al 100% (54 tests unitarios).

---

## 1. Propósito del Proyecto

`jg_agente_sdk` es el kit de desarrollo oficial del ecosistema jG. Su propósito es doble:

1. **Para Desarrolladores de Plugins:** Proporcionar las interfaces abstractas (`BasePlugin`, `BaseEngine`) y los modelos de datos tipados (`AgentTool`, `ToolResult`, `PluginMetadata`) necesarios para construir nuevas herramientas y extensiones cognitivas para el agente sin necesidad de clonar ni conocer las tripas del motor `jg_agente`.
2. **Para Clientes y Sistemas Consumidores:** Proporcionar un cliente HTTP (`AgentClient`) robusto, asíncrono y autenticado mediante firma HMAC para disparar ejecuciones, consultar hilos conversacionales y validar la salud de los agentes.

---

## 2. Principios Arquitectónicos Fundamentales

1. **Ligereza Extrema:**
   El SDK debe instalarse en segundos en cualquier entorno, microservicio o función serverless. Sus únicas dependencias de producción son `pydantic` (validación estructural) y `httpx` (cliente de red moderno).

2. **Modelo de "Caja Negra" (Black-Box Mental Model):**
   El SDK no expone ni referencia jamás la lógica propietaria interna de `jg_agente` (nodos de LangGraph, prompts de sistema, esquemas de bases de datos internas ni políticas de seguridad reservadas). Esto permite que el Core se distribuya ofuscado o como binario privativo sin comprometer la extensibilidad del sistema.

3. **Inversión de Dependencias (El Core consume al SDK):**
   El SDK nunca importa código de `jg_agente`. Es el Core (`jg_agente`) quien instala e importa `jg_agente_sdk` para heredar de sus contratos y añadir adaptadores internos como LangChain (`as_langchain_tool`).

4. **Compatibilidad hacia Atrás y Versionado Semántico:**
   Cualquier cambio en la firma de `AgentTool` o `ToolResult` debe mantener compatibilidad estricta para evitar romper plugins existentes de terceros.

---

## 3. Estructura de Módulos

```text
jg_agente_sdk/
├── jg_sdk/
│   ├── __init__.py         # Re-exportación unificada de contratos y cliente
│   ├── client.py           # AgentClient con firma criptográfica HMAC-SHA256
│   ├── cli.py              # CLI ejecutable 'jg' (ping, run, list-tools)
│   ├── contracts.py        # Contratos canónicos: AgentTool, ToolResult, BasePlugin, RiskLevel
│   ├── models.py           # Modelos de I/O: AgentInput, AgentOutput, UserContext, ExecutionStatus
│   └── py.typed            # Marcador PEP 561 de tipado estático
├── tests/                  # Suite de 53 tests unitarios (CLI, HMAC, contratos, plugins, seguridad)
├── docs/                   # Documentación técnica multilingüe (es/en) y resolución de issues
│   ├── README.md           # Índice de navegación entre idiomas
│   ├── es/                 # Documentación canónica en español (SSOT)
│   ├── en/                 # English technical documentation
│   └── issues/             # Issues documentados con análisis, walkthrough y cierre
├── scripts/
│   └── check.sh            # Pipeline de verificación (Ruff + Pytest)
├── pyproject.toml          # Metadatos del paquete y configuración de empaquetado
└── README.md               # Guía completa de uso para desarrollo de plugins y cliente
```

---

## 4. Matriz de Responsabilidades

| Responsabilidad | SDK (`jg_agente_sdk`) | Core (`jg_agente`) |
| :--- | :--- | :--- |
| **Definición de Contratos Públicos** | **Fuente Única de Verdad (SSOT)** | Hereda y consume |
| **Adaptación a LangChain / LangGraph** | Prohibido (desacoplado) | **Exclusiva** (`as_langchain_tool`) |
| **Ejecución y Compensación de Tools** | Implementa método base `run()` y `rollback()` | Ejecuta bajo sandbox y timeout |
| **Firma Criptográfica HMAC-SHA256** | Genera firmas en peticiones cliente | Valida firmas en peticiones entrantes |
| **CLI de Gestión Ligera (`jg`)** | **Exclusiva** | Ninguna (opera como servicio backend) |
