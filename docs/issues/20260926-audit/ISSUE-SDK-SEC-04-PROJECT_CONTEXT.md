# Contexto de Proyecto: [ISSUE-SDK-SEC-04] Prevención de Escalada de Directorios en Búsqueda de .env (GitLab #3)

## 1. Identificación y Estado
- **Issue ID:** SDK-SEC-04 (GitLab #3)
- **Vínculo Auditoría:** Auditoría Técnica SDK 2026-09-26 (SDK-SEC-04, SDK-SEC-01, SDK-TEST-01)
- **Componente:** `jg_agente_sdk` (CLI de scaffolding: `jg plugin init`)
- **Severidad / Prioridad:** ALTA / Bloqueante para publicación pública en PyPI
- **CWE:** CWE-200 (Exposure of Sensitive Information to an Unauthorized Actor), CWE-552 (Files or Directories Accessible to External Parties)
- **Estado:** Implementado / Verificado / Cerrado

## 2. Alineación Arquitectónica y Seguridad
`jg_agente_sdk` proporciona a la comunidad el comando CLI `jg plugin init` para generar la estructura inicial de plugins compatibles con el runtime de `jg_agente`.

En la auditoría técnica de seguridad (26 de septiembre de 2026), se detectó que el generador realizaba una búsqueda recursiva ascendente en la jerarquía del sistema de archivos (`[out_dir, *out_dir.parents]`) inspeccionando cualquier fichero `.env` existente hasta alcanzar la raíz del disco.

### Vector de Riesgo en Entornos Monorepo y Corporativos
En arquitecturas basadas en monorepos (como `javiergalvez-ia/`) o estaciones de desarrollo con repositorios anidados:
1. El desarrollador ejecuta `jg plugin init nuevo_plugin` dentro de una subcarpeta del workspace (e.g. `jg_agente_sdk/`).
2. El generador escalaba directorios padre hasta encontrar `/Users/.../javiergalvez-ia/.env`, el cual alberga claves API reales (`GROQ_API_KEY`) y configuraciones de producción.
3. Estos secretos y configuraciones eran extraídos silenciosamente y clonados dentro del `.env` del plugin generado.
4. Si el nuevo plugin era inicializado para un repositorio público o independiente, las credenciales del monorepo corporativo quedaban comprometidas.

### Directiva de Blindaje
- **Eliminación Total de la Escalada:** El generador no debe jamás inspeccionar directorios superiores ni salir del ámbito del directorio destino del plugin.
- **Aislamiento de Configuración:** Las variables de entorno de proveedores LLM se leen exclusivamente de variables de proceso activas (`os.environ`) para mensajes informativos, sin volcar secretos a disco ni heredar configuraciones de archivos padre.

## 3. Criterios de Aceptación
1. Supresión definitiva de `for env_dir in [out_dir, *out_dir.parents]` en `jg_sdk/cli.py`.
2. Verificación de que archivos `.env` en directorios contenedores (raíz de monorepos) son completamente ignorados.
3. Test automatizado de regresión que recree una estructura monorepo con `.env` padre y certifique que el plugin generado no adopta claves ni modelos del padre.
4. Paso al 100% de la suite de linters (Ruff) y pruebas automatizadas (Pytest).
