# Análisis Técnico: [ISSUE-SDK-SEC-03] Ejecución Silenciosa de Limpieza en BD vía artisan tinker

## 1. Diagnóstico del Estado Previo
En `jg_sdk/cli.py:1163-1179`:
```python
# Limpieza preventiva de agentes demo huérfanos en imágenes anteriores del dashboard
subprocess.run(
    [
        "docker",
        "compose",
        "-f",
        str(compose_file),
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

### Características
- **Seguridad:** Inyección descartada al ser una cadena literal constante sin intercalación de variables externas.
- **Transparencia:** Al usar `capture_output=True` y carecer de mención en la documentación del usuario, cualquier desarrollador inspeccionando procesos Docker o logs de base de datos se sorprendía al ver una mutación DDL/DML automática.

## 2. Alternativas Evaluadas
- **Alternativa A (Eliminar la invocación a tinker):**
  - *Desventaja:* Provocaría regresiones visuales y de configuración para desarrolladores que utilicen imágenes de Dashboard donde el agente demo predeterminado permanezca en la base de datos PostgreSQL, colisionando con el nuevo agente.
- **Alternativa B (Documentación Explícita en Código y README - Seleccionada):**
  - *Ventajas:* Conserva la higiene operativa y la robustez del entorno local autónomo mientras proporciona total claridad y transparencia tanto al desarrollador del SDK como al usuario del plugin.

## 3. Plan de Mitigación
1. Ampliar los comentarios en `jg_sdk/cli.py` alrededor de la llamada `artisan tinker`.
2. Incluir en la plantilla de `README.md` del scaffold (sección 5) un punto específico sobre el ciclo de vida de `jg run` y la depuración del agente `a0000000-0000-0000-0000-000000000002`.
3. Crear test unitario en `tests/test_cli.py`.
4. Verificar con Ruff y Pytest.
