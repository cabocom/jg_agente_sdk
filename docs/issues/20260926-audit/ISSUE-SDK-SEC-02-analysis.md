# Análisis Técnico: [ISSUE-SDK-SEC-02] Credenciales por Defecto en docker-compose.yml

## 1. Diagnóstico del Estado Previo
En la plantilla generada por `jg_sdk/cli.py:824-839`, se configuraban variables con sintaxis de sustitución Bash:
```yaml
APP_KEY: "${APP_KEY:-base64:u/pQ9k8q3N0vQzW3mY8l4xJ1t5R6w7y8z9a0b1c2d3E=}"
JG_AGENTE_SECRET: "${JG_AGENTE_SECRET:-secret_dev_token_12345}"
ADMIN_DEFAULT_PASSWORD: "${ADMIN_DEFAULT_PASSWORD:-admin123456}"
PERMANENT_AGENT_SECRET: "${JG_AGENTE_SECRET:-secret_dev_token_12345}"
```

Y al invocar `jg run`, el CLI imprimía las credenciales y URLs de acceso sin ninguna indicación de que los valores por defecto representaban un riesgo crítico de seguridad en entornos compartidos o productivos.

## 2. Vectores de Riesgo
1. **Reutilización inadvertida en producción (CWE-1188 / CWE-798):** Desarrolladores que copian el `docker-compose.yml` para desplegar en VPS o Kubernetes sin definir variables en `.env`.
2. **Exposición de tokens HMAC compartidos:** `JG_AGENTE_SECRET` por defecto permitiría a cualquier actor en la red firmar peticiones contra `/executions/*` del agente.
3. **Acceso administrativo trivial:** La contraseña `admin123456` para `admin@local.test` facilitaría ataques de fuerza bruta inmediata o acceso directo.

## 3. Alternativas Evaluadas
- **Alternativa A (Exigir configuración obligatoria de .env antes de arrancar):**
  - *Desventaja:* Degrada significativamente la experiencia del desarrollador (DX) que desea evaluar un plugin recién creado en 30 segundos.
- **Alternativa B (Generación aleatoria de secretos en cada `init`):**
  - *Desventaja:* Desincronización entre servicios si los contenedores no leen las mismas variables de `.env` o si se reconstruyen parcialmente.
- **Alternativa C (Fallbacks de desarrollo + Banners de advertencia preventiva - Seleccionada):**
  - *Ventajas:* Mantiene la experiencia de desarrollo local inmediata sin fricción, mientras advierte enérgicamente en consola y en el propio código fuente que dichos valores no deben alcanzar entornos de producción.

## 4. Plan de Acción
1. Añadir banners de advertencia de seguridad en `handle_run` (al inicio y en el bloque resumen de puertos/credenciales).
2. Insertar comentarios de seguridad en los bloques de variables de entorno de `docker_compose_content`.
3. Añadir pruebas unitarias automatizadas en `tests/test_cli.py`.
4. Verificar con Ruff y Pytest.
