# Contexto de Proyecto: [ISSUE-SDK-SEC-02] Advertencia de Credenciales por Defecto en docker-compose.yml (GitLab #4)

## 1. Identificación y Estado
- **Issue ID:** SDK-SEC-02 (GitLab #4)
- **Vínculo Auditoría:** Auditoría Técnica SDK 2026-09-26 (SDK-SEC-02)
- **Componente:** `jg_agente_sdk` (CLI `jg run` y scaffold `docker-compose.yml`)
- **Severidad / Prioridad:** MEDIA / Deuda Técnica de Seguridad
- **CWE:** CWE-1188 (Insecure Default Initialization of Resource), CWE-798 (Use of Hard-coded Credentials)
- **Estado:** Implementado / Verificado / Cerrado

## 2. Alineación Arquitectónica y Seguridad
`jg_agente_sdk` genera mediante `jg plugin init` un entorno local autónomo de desarrollo basado en Docker Compose, que orquesta:
1. Control Plane (`jg_dashboard` Laravel).
2. Execution Plane (`jg_agente` FastAPI/LangGraph con el plugin montado).
3. Bases de datos PostgreSQL independientes para Dashboard y Agente.

Para garantizar una experiencia de desarrollo local inmediata ("cero fricción"), el archivo `docker-compose.yml` incluye valores de fallback por defecto para variables como `APP_KEY`, `JG_AGENTE_SECRET` (`secret_dev_token_12345`) y `ADMIN_DEFAULT_PASSWORD` (`admin123456`).

### Vector de Riesgo
Si un desarrollador o equipo de operaciones despliega el archivo `docker-compose.yml` generado en un servidor accesible externamente, pre-producción o producción sin definir un archivo `.env` con contraseñas seguras, el sistema arrancará con credenciales públicas y conocidas en el repositorio de código abierto del SDK.

### Directiva de Mitigación
1. **Defensa en Tiempo de Ejecución (`jg run`):** Emitir advertencias visibles y destacadas en consola cada vez que el stack autónomo es iniciado, recordando que las credenciales activas son exclusivas para desarrollo local.
2. **Documentación en Archivo:** Incluir comentarios de seguridad explícitos en el bloque `environment:` de cada servicio en la plantilla de `docker-compose.yml`.
3. **Indicador de Contraseña Insegura:** Etiquetar claramente en la consola que la contraseña `admin123456` es insegura por defecto.

## 3. Criterios de Aceptación
1. El comando `jg run` muestra el banner:
   ```text
   ⚠️  Stack iniciado con credenciales de DESARROLLO. Configura el .env antes de desplegar en producción.
   ```
2. La plantilla generada de `docker-compose.yml` contiene la advertencia `ADVERTENCIA DE SEGURIDAD (SDK-SEC-02)`.
3. Batería de pruebas unitarias que verifique la presencia del banner en consola y las directivas en `docker-compose.yml`.
4. Pase al 100% de la suite de linters (Ruff) y pruebas automatizadas (Pytest).
