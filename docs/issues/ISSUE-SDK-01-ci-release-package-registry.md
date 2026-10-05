# RESOLUCIÓN ISSUE jg_agente_sdk#1: ci/release: Configurar pipeline de publicación de paquetes y paridad de contratos con jg_agente

**ID del Issue:** [jg_agente_sdk#1](https://gitlab.com/javiergalvez-ia/jg_agente_sdk/-/work_items/1)  
**Fecha:** 5 de octubre de 2026  
**Autor:** Javier Gálvez / Asistente  
**Estado:** Resuelto / Listo para validación en GitLab CI  

---

## 1. Contexto y Objetivos

`jg_agente_sdk` es el kit de desarrollo canónico para plugins y clientes externos. El motor central `jg_agente` hereda de sus contratos públicos (`AgentTool`, `ToolResult`, `AgentInput`, `AgentOutput`, etc.).

El objetivo es permitir que `jg_agente` pueda instalar el SDK de forma reproducible en sus pipelines de CI/CD para validar la paridad de contratos y prevenir cualquier deriva entre ambas bases de código.

---

## 2. Tareas Realizadas

### A. Configuración de Pipeline de Release en `.gitlab-ci.yml` (`jg_agente_sdk`)
Se añadió la etapa `release` con el job `release:package_registry`:
- Se ejecuta automáticamente ante la creación de tags semánticos (ej. `v1.0.0` o `v*.*.*`).
- Compila los paquetes (`sdist` y `wheel`) mediante `python -m build`.
- Publica los artefactos en el **GitLab Package Registry** del proyecto utilizando autenticación nativa de CI:
  ```bash
  TWINE_PASSWORD=${CI_JOB_TOKEN} TWINE_USERNAME=gitlab-ci-token python -m twine upload --repository-url ${CI_API_V4_URL}/projects/${CI_PROJECT_ID}/packages/pypi dist/*
  ```
- Mantiene aislada la publicación en PyPI oficial (`publish:pypi`), la cual solo se dispara si la variable `$PYPI_TOKEN` está configurada o mediante ejecución manual controlada.

### B. Reactivación y Protección del Test de Deriva de Contratos en `jg_agente`
Se activó el archivo de pruebas `jg_agente/tests/test_contracts_drift.py`:
- Valida la paridad estructural estricta (100%) entre Core y SDK para:
  1. `RiskLevel` (valores de enum)
  2. `ToolType` (valores de enum)
  3. `ExecutionStatus` (valores de enum)
  4. `AgentTool` (campos del modelo Pydantic)
  5. `ToolResult` (campos del modelo Pydantic)
  6. `AgentInput` (campos del modelo Pydantic)
  7. `AgentOutput` (campos del modelo Pydantic)
  8. `UserContext` (campos del modelo Pydantic)
- Si `jg_sdk` está presente, ejecuta las 8 aserciones de paridad; si el entorno es mínimo y no tiene el SDK instalado, se omite de forma segura (`@pytest.mark.skipif(not HAS_JG_SDK)`).

### C. Actualización de Pipeline en `jg_agente` (`.gitlab-ci.yml`)
En la etapa `test:pytest` de `jg_agente`, se añadió la instalación automática del SDK mediante `${CI_JOB_TOKEN}`:
```yaml
before_script:
  - python -m pip install --upgrade pip
  - pip install .[dev]
  - pip install "git+https://gitlab-ci-token:${CI_JOB_TOKEN}@gitlab.com/javiergalvez-ia/jg_agente_sdk.git" || echo "⚠️ Advertencia: No se pudo clonar jg_agente_sdk con CI_JOB_TOKEN (se omite test de deriva si no está instalado)"
```

---

## 3. Acción Manual Requerida por el Usuario en la Interfaz Web de GitLab

Para que `jg_agente` tenga permisos de lectura/clonación sobre `jg_agente_sdk` utilizando su token efímero de pipeline (`${CI_JOB_TOKEN}`):

1. Acceder al repositorio de `jg_agente_sdk` en GitLab:
   `https://gitlab.com/javiergalvez-ia/jg_agente_sdk`
2. Navegar a:
   **Settings > CI/CD > Job token permissions**
3. Añadir a la lista de proyectos autorizados (allowlist):
   `javiergalvez-ia/jg_agente`
4. Guardar cambios.
