# Contexto de Proyecto: [ISSUE-SDK-SEC-01] Prevención de Inyección de Claves de API en .env de Scaffolding (GitLab #2)

## 1. Identificación y Estado
- **Issue ID:** SDK-SEC-01 (GitLab #2)
- **Vínculo Auditoría:** Auditoría Técnica SDK 2026-09-26 (SDK-SEC-01, SDK-SEC-04, SDK-TEST-01)
- **Componente:** `jg_agente_sdk` (CLI de scaffolding: `jg plugin init`)
- **Severidad / Prioridad:** ALTA / Bloqueante para publicación pública en PyPI
- **CWE:** CWE-312 (Cleartext Storage of Sensitive Information), CWE-200 (Exposure of Sensitive Information to an Unauthorized Actor)
- **Estado:** Implementado / Verificado / Cerrado

## 2. Alineación Arquitectónica y Seguridad
`jg_agente_sdk` es el kit público de desarrollo para plugins del ecosistema `jg_agente`. A través del comando `jg plugin init`, el SDK provee un generador de scaffolding para arrancar nuevos plugins con su estructura de archivos, contenedor Docker y entorno local.

En la auditoría técnica de seguridad (26 de septiembre de 2026), se detectó que el generador inspeccionaba variables de entorno del sistema (`GROQ_API_KEY`, `GLOBAL_GROQ_API_KEY`) y realizaba un recorrido hacia directorios padre (`out_dir.parents`) buscando ficheros `.env`. Si encontraba una clave de API activa de producción o desarrollo, la escribía directamente en el fichero `.env` del plugin recién creado.

Aunque el `.gitignore` generado excluye `.env`, esta práctica representaba una vulnerabilidad de filtrado de credenciales:
1. **Riesgo de commit involuntario:** Forzado de commits (`git add -f`), repositorios mal inicializados o clientes GUI que obvian directivas `.gitignore`.
2. **Escalada de directorios (SDK-SEC-04):** En estructuras monorepo como `javiergalvez-ia/`, el generador leía el `.env` raíz corporativo y clonaba secretos reales a subproyectos.

**Directiva de Blindaje:**
- El archivo `.env` generado debe declararse siempre con variables vacías (`GROQ_API_KEY=`, `GLOBAL_GROQ_API_KEY=`) acompañadas de comentarios de advertencia de seguridad.
- Supresión total del recorrido por árboles de directorios padres para recolectar secretos.
- Emisión de advertencia en consola notificando que, aunque se detecten credenciales en memoria, no serán volcadas a disco.

## 3. Criterios de Aceptación
1. `jg plugin init` no escribe en ningún caso valores reales de API keys en `.env`.
2. Supresión del bucle de escalada de carpetas padre en búsqueda de `.env`.
3. Notificación informativa en salida estándar cuando existen variables de API key presentes en el entorno.
4. Batería de pruebas unitarias de regresión en `tests/test_cli.py` garantizando la ausencia de claves y el formato seguro.
5. Pase al 100% de la suite de linters (Ruff) y pruebas automatizadas (Pytest).
