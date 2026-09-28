# Walkthrough: [ISSUE-SDK-SEC-01] Prevención de Inyección de Claves de API en .env de Scaffolding

## 1. Resumen de Cambios
Se corrigió la vulnerabilidad de fuga de secretos en el comando de scaffolding (`jg plugin init`) en `jg_agente_sdk`:
- Se eliminó la búsqueda y lectura de archivos `.env` en directorios padre (`out_dir.parents`).
- Se aseguró que las variables de claves (`GROQ_API_KEY`, `GLOBAL_GROQ_API_KEY`) se generen siempre vacías en `.env`.
- Se introdujo una advertencia en consola alertando al usuario de que sus claves activas del sistema no se inyectan en ficheros locales.
- Se añadió un test unitario de regresión cubriendo `SDK-TEST-01`.

## 2. Archivos Modificados
- **[jg_sdk/cli.py](../../../jg_sdk/cli.py)**:
  - Líneas 752-766: Sustitución de la búsqueda en directorios padre por detección simple en memoria y emisión de banner de advertencia seguro.
  - Líneas 946-951: `.env` generado con variables vacías y cabecera de seguridad.
- **[tests/test_cli.py](../../../tests/test_cli.py)**:
  - Nueva prueba `test_scaffold_does_not_leak_api_key_in_env` con verificación de claves en entorno, formato del `.env` y captura de logs en `capsys`.

## 3. Verificación y Resultados
Se ejecutó la suite de verificación estándar `scripts/check.sh`:
- **Ruff:** 11 archivos verificados y formateados, 0 errores.
- **Pytest:** 41 pruebas superadas al 100% (incremento de 38 a 41 tests):
  ```bash
  tests/test_cli.py::test_scaffold_does_not_leak_api_key_in_env PASSED
  ============================== 41 passed in 1.48s ==============================
  ```
