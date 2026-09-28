# Contexto de Proyecto: [ISSUE-SDK-TEST-01] Test de Regresión para Prevenir Inyección de Claves API en .env (GitLab #7)

## 1. Identificación y Estado
- **Issue ID:** SDK-TEST-01 (GitLab #7)
- **Vínculo Auditoría:** Auditoría Técnica SDK 2026-09-26 (SDK-TEST-01, vinculado a SDK-SEC-01 y SDK-SEC-04)
- **Componente:** `jg_agente_sdk` (Suite de tests unitarios: `tests/test_cli.py`)
- **Severidad / Prioridad:** INFO / Deuda Técnica de Calidad y Prevención de Regresiones
- **Estado:** Implementado / Verificado / Cerrado

## 2. Alineación Arquitectónica y Calidad Continua
La auditoría de seguridad del SDK (26 de septiembre de 2026) identificó como vulnerabilidad bloqueante (`SDK-SEC-01`) la inyección de claves API del sistema en el archivo `.env` creado por el comando de scaffolding (`jg plugin init`).

Para garantizar que futuras iteraciones o refactorizaciones del código fuente en `jg_sdk/cli.py` no reintroduzcan inadvertidamente este comportamiento:
- Es mandatorio contar con pruebas automatizadas en la suite de integración continua (CI) que simulen entornos contaminados con credenciales reales.
- Las pruebas deben certificar tanto la ausencia de las cadenas confidenciales en el archivo `.env` resultante como la presencia de la estructura canónica vacía (`GROQ_API_KEY=`).

## 3. Criterios de Aceptación
1. Implementación de `test_scaffold_env_does_not_inject_real_api_key` en `tests/test_cli.py`.
2. Verificación de que claves inyectadas vía `monkeypatch.setenv` en `GROQ_API_KEY` y `GLOBAL_GROQ_API_KEY` no aparecen en el fichero `.env` generado.
3. Pase al 100% de la suite de linters (Ruff) y pruebas automatizadas (Pytest).
