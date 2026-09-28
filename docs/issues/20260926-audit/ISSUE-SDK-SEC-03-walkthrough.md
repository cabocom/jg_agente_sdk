# Walkthrough: [ISSUE-SDK-SEC-03] Documentación de Limpieza de BD en jg run

## 1. Resumen de Cambios
Se documentó formalmente el comportamiento operativo de depuración de base de datos en `jg run`:
- Se agregaron comentarios técnicos en `jg_sdk/cli.py` explicando el propósito de la llamada a `artisan tinker` para depurar el agente legacy `a0000000-0000-0000-0000-000000000002`.
- Se incorporó en el `README.md` del scaffold una sección que explica el ciclo de vida de `jg run` y la limpieza automática de registros para evitar colisiones.
- Se añadió la prueba unitaria `test_scaffold_readme_documents_run_lifecycle_cleanup` en `tests/test_cli.py`.

## 2. Archivos Modificados
- **[jg_sdk/cli.py](../../../jg_sdk/cli.py)**:
  - Comentarios técnicos en bloque de `subprocess.run` con `artisan tinker`.
  - Plantilla `readme_content`: sección 5 con viñeta descriptiva del ciclo de vida de `jg run`.
- **[tests/test_cli.py](../../../tests/test_cli.py)**:
  - Nueva prueba `test_scaffold_readme_documents_run_lifecycle_cleanup`.

## 3. Verificación y Resultados
Se ejecutó la suite de verificación con Ruff y Pytest:
```bash
bash scripts/check.sh
```
Resultado:
- **Ruff:** 11 archivos verificados y formateados, 0 errores.
- **Pytest:** 46 pruebas unitarias pasando al 100%:
  ```bash
  tests/test_cli.py::test_scaffold_readme_documents_run_lifecycle_cleanup PASSED
  ============================== 46 passed in 0.89s ==============================
  ```
