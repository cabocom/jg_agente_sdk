# Walkthrough: [ISSUE-SDK-SEC-02] Advertencia de Credenciales por Defecto en docker-compose.yml

## 1. Resumen de Cambios
Se implementó la señalización de seguridad para credenciales por defecto de desarrollo:
- Inclusión de comentarios de advertencia en la plantilla generada de `docker-compose.yml`.
- Emisión de banner preventivo en `handle_run` tanto al iniciar el stack como en el resumen final de credenciales.
- Dos nuevas pruebas unitarias en `tests/test_cli.py` garantizando la presencia del banner en consola y de las advertencias en el archivo generado.

## 2. Archivos Modificados
- **[jg_sdk/cli.py](../../../jg_sdk/cli.py)**:
  - Líneas 810-813: Comentario `ADVERTENCIA DE SEGURIDAD (SDK-SEC-02)` en el bloque `environment:` de `jg_dashboard`.
  - Líneas 1150-1153: Banner de advertencia en la salida inicial de `handle_run`.
  - Líneas 1176-1180: Bloque destacado de aviso de seguridad en el resumen final.
  - Línea 1188: Calificación explícita de `admin123456 (insegura por defecto)` y `SOLO DESARROLLO LOCAL`.
- **[tests/test_cli.py](../../../tests/test_cli.py)**:
  - `test_scaffold_docker_compose_security_warnings`: Comprueba que `docker-compose.yml` contenga las notas de advertencia.
  - `test_cli_run_prints_security_warning_banner`: Comprueba que `jg run` imprima el banner de credenciales de desarrollo.

## 3. Verificación y Resultados
Se ejecutó la suite de verificación con Ruff y Pytest:
```bash
bash scripts/check.sh
```
Resultado:
- **Ruff:** 11 archivos verificados y formateados, 0 errores.
- **Pytest:** 44 pruebas unitarias pasando al 100%:
  ```bash
  tests/test_cli.py::test_scaffold_docker_compose_security_warnings PASSED
  tests/test_cli.py::test_cli_run_prints_security_warning_banner PASSED
  ============================== 44 passed in 0.87s ==============================
  ```
