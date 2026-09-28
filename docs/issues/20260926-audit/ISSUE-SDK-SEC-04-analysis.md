# Análisis Técnico: [ISSUE-SDK-SEC-04] Escalada de Directorios en Búsqueda de .env Filtra Claves del Monorepo

## 1. Diagnóstico del Estado Previo
En `jg_sdk/cli.py:756-775`, el método `generate_plugin_scaffold` implementaba el siguiente patrón de resolución de entorno:

```python
for env_dir in [out_dir, *out_dir.parents]:
    cand_env = env_dir / ".env"
    if cand_env.is_file():
        for line in cand_env.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("GLOBAL_GROQ_API_KEY=") or line.startswith("GROQ_API_KEY="):
                ...
            elif line.startswith("LLM_MODEL="):
                ...
```

### Problemas Críticos
1. **Ruptura de Fronteras de Aislamiento (CWE-552):** Un comando destinado a generar un proyecto aislado exploraba hacia arriba todo el árbol de carpetas hasta la raíz (`/`), violando el principio de menor privilegio sobre el sistema de archivos del usuario.
2. **Filtración Silenciosa de Secretos:** Si existía un archivo `.env` en la raíz de la máquina, en el directorio Home (`~/.env`) o en la raíz de un monorepo (`/monorepo/.env`), los valores eran leídos sin consentimiento explícito del desarrollador.
3. **Acoplamiento de Entornos:** Los plugins generados heredaban de forma involuntaria modelos y configuraciones de proyectos completamente ajenos.

## 2. Alternativas Evaluadas
- **Alternativa A (Preguntar al usuario interactivamente):**
  - *Desventaja:* Rompe la idoneidad del CLI para scripting automatizado, pipelines de CI/CD o testing sin TTY interactivo.
- **Alternativa B (Limitar a `out_dir`):**
  - *Desventaja:* `out_dir` es una carpeta recién creada (habitualmente vacía), por lo que buscar un `.env` dentro de ella carece de utilidad funcional.
- **Alternativa C (Eliminar por completo la búsqueda en disco y usar fallbacks canónicos - Seleccionada):**
  - *Ventajas:* Comportamiento determinista, predecible y seguro. Cero lecturas arbitrarias del sistema de archivos superior. Las claves se mantienen vacías en la plantilla y el modelo por defecto es el canónico del SDK (`openai/gpt-oss-120b`).

## 3. Plan de Mitigación
1. Eliminar por completo el bucle `for env_dir in [out_dir, *out_dir.parents]:`.
2. Leer únicamente de variables de proceso activas (`os.environ`) para emitir una advertencia de seguridad si hay credenciales cargadas.
3. Establecer modelo por defecto seguro (`detected_llm_model = os.environ.get("LLM_MODEL") or "openai/gpt-oss-120b"`).
4. Implementar test de regresión automatizado reproduciendo un entorno monorepo con `.env` raíz sensible.
