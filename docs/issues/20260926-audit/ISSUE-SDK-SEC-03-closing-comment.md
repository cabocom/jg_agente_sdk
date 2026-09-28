# Comentario de Cierre: [ISSUE-SDK-SEC-03] jg run ejecuta borrado silencioso en BD vía artisan tinker (GitLab #6)

## Estado: RESUELTO / CERRADO

### Resumen de la Solución
Se ha implementado la documentación técnica y funcional para transparentar la operación de saneamiento de base de datos en `jg run` (`SDK-SEC-03`):

1. **Documentación en Código Fuente:**
   - Se documentó en `jg_sdk/cli.py` (función `handle_run`) que la llamada a `php artisan tinker` ejecuta una consulta DDL/DML determinista y estática cuyo fin es eliminar el agente demo legacy (`a0000000-0000-0000-0000-000000000002`) inyectado por versiones anteriores de la imagen del Dashboard, evitando duplicidades con el agente del plugin.
2. **Documentación en Plantilla de Scaffold (`README.md`):**
   - Se incorporó en la sección de docker-compose del `README.md` generado una explicación clara del ciclo de vida de `jg run` y su tarea de limpieza preventiva para garantizar la higiene del panel de control.
3. **Test Automatizado:**
   - Se añadió la prueba unitaria `test_scaffold_readme_documents_run_lifecycle_cleanup` en `tests/test_cli.py`, comprobando que los scaffolds generados siempre documenten este comportamiento.
4. **Calidad y Linters:** Suite completa superada al 100% (**46 tests unitarios pasando**, linter y formateador Ruff pasando sin observaciones).

### Referencias y Commits
- Commit Solución y Docs: `docs(cli): document artisan tinker database cleanup in jg run and scaffold (SDK-SEC-03, #6)`
- Documentación técnica: `docs/issues/20260926-audit/`

/close
