# Comentario de Cierre: [ISSUE-SDK-SEC-04] Escalada de directorios en búsqueda de .env filtra claves del monorepo (GitLab #3)

## Estado: RESUELTO / CERRADO

### Resumen de la Solución
Se ha eliminado completamente el comportamiento de escalada ascendente en el árbol de directorios durante el scaffolding de plugins:

1. **Supresión de Búsqueda Ascendente:** Se eliminó la iteración sobre `[out_dir, *out_dir.parents]` que abría e inspeccionaba archivos `.env` en directorios padre hasta la raíz del disco.
2. **Blindaje de Monorepos:** La ejecución de `jg plugin init` desde cualquier subdirectorio del monorepo `javiergalvez-ia/` o entornos corporativos anidados ya no lee ni replica secretos o variables del `.env` corporativo raíz.
3. **Valores por Defecto Deterministas:** El modelo LLM por defecto se resuelve de forma determinista (`openai/gpt-oss-120b`) o mediante la variable de proceso `LLM_MODEL`, sin dependencias en el sistema de archivos externo.
4. **Test Automatizado de Regresión:** Se añadió el test unitario `test_scaffold_does_not_traverse_parent_env` en `tests/test_cli.py`, validando que un `.env` raíz en estructura monorepo es estrictamente ignorado por el scaffold anidado.
5. **Calidad y Linters:** Suite completa superada al 100% (42 tests unitarios pasando, linter y formateador Ruff pasando sin advertencias).

### Referencias y Commits
- Commit Solución Base: `e752815` (`fix(cli): prevent leaking API keys into generated .env (SDK-SEC-01, SDK-SEC-04)`)
- Commit Test & Doc: `tests/test_cli.py` (`test_scaffold_does_not_traverse_parent_env`)
- Documentación técnica: `docs/issues/20260926-audit/`
- CWE: CWE-200, CWE-552

/close
