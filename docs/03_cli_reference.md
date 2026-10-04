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

```bash
jg-sdk-cli verify ./mi_plugin
```
