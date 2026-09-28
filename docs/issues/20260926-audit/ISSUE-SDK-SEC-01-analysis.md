# Análisis Técnico: [ISSUE-SDK-SEC-01] Fuga de Credenciales en Scaffold CLI (.env)

## 1. Diagnóstico del Estado Previo
En la versión 1.0.0 inicial de `jg_sdk/cli.py`, la función `generate_plugin_scaffold`:
- Inspeccionaba `os.environ.get("GLOBAL_GROQ_API_KEY")` y `os.environ.get("GROQ_API_KEY")`.
- Si estaban vacías, ejecutaba un bucle recursivo sobre `[out_dir, *out_dir.parents]` abriendo cualquier fichero `.env` en los directorios superiores para parsear valores de `GROQ_API_KEY` o `GLOBAL_GROQ_API_KEY`.
- Escribía el valor extraído en el archivo `.env` de destino:
  ```python
  GROQ_API_KEY={detected_groq_key}
  GLOBAL_GROQ_API_KEY={detected_groq_key}
  ```

## 2. Vectores de Riesgo Identificados
1. **Exposición en repositorios (CWE-312 / CWE-200):** Si el desarrollador ejecuta `git add .` ignorando advertencias o usa `git add -f`, la clave real termina en el control de versiones (GitLab/GitHub).
2. **Filtración cruzada de monorepo (SDK-SEC-04):** En entornos como `javiergalvez-ia/`, ejecutar el CLI dentro de `jg_agente_sdk/` leía el `.env` de la raíz del monorepo e inyectaba tokens reales a carpetas temporales o de plugins experimentales.
3. **Falsa sensación de seguridad:** Depender exclusivamente de `.gitignore` no cumple con el principio de defensa en profundidad.

## 3. Alternativas Evaluadas
- **Alternativa A (Prompt interactivo):** Solicitar al desarrollador si desea copiar la clave. *Descartada:* Hace que el CLI no sea idóneo para automatizaciones o scripts no interactivos (CI/CD).
- **Alternativa B (Cifrado local):** Guardar claves en keyring local. *Descartada:* Complejidad innecesaria y dependencia externa no deseada para un SDK ligero.
- **Alternativa C (Plantilla vacía con advertencia preventiva - Seleccionada):**
  - Mantener variables vacías (`GROQ_API_KEY=`, `GLOBAL_GROQ_API_KEY=`) con instrucciones claras en el `.env`.
  - Informar por consola en caso de detectar claves en el entorno.
  - Eliminar por completo la inspección en directorios padre.

## 4. Plan de Acción
1. Refactorizar el bloque de detección en `jg_sdk/cli.py:752-775` eliminando el bucle de parents.
2. Actualizar el contenido de `env_content` en `jg_sdk/cli.py` fijando las variables de claves a vacío.
3. Añadir test unitario de regresión en `tests/test_cli.py` (`SDK-TEST-01`).
4. Verificar con `scripts/check.sh` (Ruff + Pytest).
