# 03. Referencia de Línea de Comandos (`jg-sdk-cli`)

El SDK incluye la utilidad de consola `jg-sdk-cli` para scaffolding estandarizado, inspección y verificación de plugins compatibles.

---

## 1. Generación de Nuevos Plugins (`new`)

Crea un proyecto de plugin estructurado con configuración de empaquetado, suite de tests unitarios y puntos de entrada configurados:

```bash
jg-sdk-cli new [OPCIONES] NOMBRE
```

### Argumentos y Opciones:
- `NOMBRE`: Nombre del plugin (ej. `monitoring` o `jg_plugin_monitoring`).
- `--target-dir RUTA`: Directorio destino donde se generará el proyecto.
- `--template {minimal, standard, full}`:
  - `minimal`: Estructura básica con una sola herramienta.
  - `standard` (por defecto): Incluye herramientas, modelos Pydantic y tests unitarios con `pytest`.
  - `full`: Incluye herramientas reversibles con `rollback_func`, motores `ObserverEngine`/`VerifierEngine` y tests exhaustivos.
- `--author TEXTO`: Autor o equipo responsable (default: `"Equipo de Desarrollo"`).
- `--description TEXTO`: Descripción funcional del plugin.
- `--force`: Sobrescribe archivos si el directorio destino existe y no está vacío.

### Ejemplo de Uso:
```bash
jg-sdk-cli new sdr_connector --template full --author "Javier Gálvez"
```

---

## 2. Inspección Estática de Plugins (`inspect`)

Carga e inspecciona los metadatos, herramientas, esquemas de entrada y motores registrados en un plugin local:

```bash
jg-sdk-cli inspect ./jg_plugin_datosgob
```

---

## 3. Verificación de Contratos y Linting (`verify`)

Ejecuta una batería de validaciones sobre un paquete de plugin para garantizar que cumple las directivas de seguridad del Core:
- Comprueba que toda herramienta con `reversible=True` implemente `rollback_func`.
- Valida que `timeout_sec` sea positivo y finito.
- Verifica que las descripciones de herramientas no estén vacías (necesario para el function calling del LLM).
- Comprueba que los identificadores de herramientas y plugins contengan únicamente caracteres alfanuméricos válidos en snake_case.

---

## 4. Enlace Simbólico Dinámico (`link` / `unlink`)

Permite vincular y desvincular plugins externos en desarrollo dentro del directorio de plugins de una instancia de agente mediante enlaces simbólicos relativos portables.

### 4.1 Enlazar un Plugin (`link`)

```bash
jg link [OPCIONES] ORIGEN_PLUGIN
# O alternativamente:
jg plugin link [OPCIONES] ORIGEN_PLUGIN
```

#### Argumentos y Opciones:
- `ORIGEN_PLUGIN`: Ruta o nombre del plugin a enlazar (ej. `jg_plugin_conversational` o `../mi_plugin`).
- `-t`, `--target-dir RUTA`: Directorio `plugins/` del agente destino (por defecto busca `jg_agente/plugins` o `./plugins`).
- `-f`, `--force`: Ignora las advertencias de brecha de seguridad y sobreescribe symlinks existentes.

#### Políticas de Validación y Seguridad:
1. **Colisión de Motores Exclusivos:** Si dos plugins intentan registrar simultáneamente el mismo motor cognitivo exclusivo (`ObserverEngine`, `PlannerEngine` o `VerifierEngine`), el comando aborta la operación para evitar comportamientos no deterministas.
2. **Brecha de Confianza / Mínimo Privilegio:** Si un plugin con capacidades de red pública abierta (conversacional, web) se intenta enlazar junto a un plugin con acceso a recursos críticos del sistema (ej. Docker socket proxy), el CLI bloquea la vinculación por defecto para proteger el agente, requiriendo `--force` para anular dicha restricción.

### 4.2 Desvincular un Plugin (`unlink`)

```bash
jg unlink [OPCIONES] NOMBRE_PLUGIN
# O alternativamente:
jg plugin unlink [OPCIONES] NOMBRE_PLUGIN
```

Elimina de forma segura el enlace simbólico del directorio del agente sin alterar el código fuente del plugin externo. Protege directorios reales que no sean symlinks impidiendo borrados accidentales de código.

