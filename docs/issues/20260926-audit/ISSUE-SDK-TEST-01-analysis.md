# Análisis Técnico: [ISSUE-SDK-TEST-01] Cobertura de Regresión para Generación Segura de .env

## 1. Diagnóstico del Estado Previo
Con anterioridad a la resolución de `SDK-SEC-01`, la suite de tests en `tests/test_cli.py` validaba:
- La creación de directorios del plugin (`pyproject.toml`, `README.md`, `.gitignore`, `install.sh`).
- Permisos de ejecución de scripts Bash.
- Subcomandos de ayuda y respuesta a flags CLI.

Sin embargo, ninguna prueba comprobaba el contenido específico del archivo `.env` generado cuando el proceso que ejecuta `jg plugin init` dispone de claves reales en sus variables de entorno del sistema operativo (`os.environ`).

## 2. Especificación del Test de Regresión
El test debe:
1. Utilizar `monkeypatch.setenv` para fijar claves secretas simuladas de producción (`sk-test-real-key-12345`).
2. Invocar `generate_plugin_scaffold` en un directorio temporal aislado provisto por `tmp_path`.
3. Leer el contenido de `.env`.
4. Asegurar mediante aserciones estrictas que:
   - La cadena secreta no está presente en el archivo.
   - La variable `GROQ_API_KEY=` se encuentra vacía para configuración manual segura por parte del usuario.

## 3. Plan de Mitigación
1. Integrar el test con la signatura exacta propuesta en la auditoría en `tests/test_cli.py`.
2. Ejecutar y certificar con Ruff y Pytest.
