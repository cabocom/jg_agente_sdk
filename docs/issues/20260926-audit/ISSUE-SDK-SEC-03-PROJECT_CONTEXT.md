# Contexto de Proyecto: [ISSUE-SDK-SEC-03] Documentación de Limpieza de BD en jg run (GitLab #6)

## 1. Identificación y Estado
- **Issue ID:** SDK-SEC-03 (GitLab #6)
- **Vínculo Auditoría:** Auditoría Técnica SDK 2026-09-26 (SDK-SEC-03)
- **Componente:** `jg_agente_sdk` (CLI `jg run` y scaffold `README.md`)
- **Severidad / Prioridad:** BAJA / Transparencia Operativa
- **Estado:** Implementado / Verificado / Cerrado

## 2. Alineación Arquitectónica y Operaciones
En el ciclo de arranque del entorno autónomo (`jg run`), `jg_agente_sdk` orquesta la inicialización de los contenedores Docker y coordina la consistencia entre el Control Plane (`jg_dashboard`) y el Execution Plane (`jg_agente`).

### Propósito de la Operación en BD
En las imágenes iniciales de `jg_dashboard`, los seeders de base de datos creaban por defecto un agente de demostración con identificador fijo:
`a0000000-0000-0000-0000-000000000002`

Al desplegar un plugin con su propio agente (`a0000000-0000-0000-0000-000000000001`), la presencia de este registro huérfano provocaba duplicidades visuales en el panel web y confusión en el seguimiento de ejecuciones. Para garantizar un entorno prístino, `handle_run` ejecuta un comando idempotente vía `php artisan tinker`:
```php
\App\Models\Agent::where('agent_id', 'a0000000-0000-0000-0000-000000000002')->delete();
```

### Hallazgo de Auditoría
La auditoría determinó que:
- La instrucción es completamente estática y no recibe datos de usuario (descartando cualquier riesgo de inyección de comandos o código).
- No obstante, al ejecutarse de manera silenciosa (`capture_output=True`) sin documentación, constituía una "sorpresa operativa" para los desarrolladores.

### Directiva de Mitigación
1. **Documentación en Código Fuente:** Añadir comentarios explicativos exhaustivos en `handle_run` detallando el propósito y alcance de la operación.
2. **Documentación en Scaffold (`README.md`):** Explicar en la sección del entorno Docker Compose del README generado qué hace internamente el ciclo de vida de `jg run`.
3. **Prueba de Integridad:** Verificar mediante test automatizado que el scaffold incluye dicha documentación.

## 3. Criterios de Aceptación
1. El bloque de limpieza en `handle_run` cuenta con comentarios claros sobre la depuración del agente legacy.
2. La plantilla `README.md` generada documenta la limpieza preventiva en el ciclo de vida de `jg run`.
3. Test automatizado en `tests/test_cli.py` certificando la presencia de las explicaciones en el README.
4. Pase al 100% de la suite de linters (Ruff) y pruebas automatizadas (Pytest).
