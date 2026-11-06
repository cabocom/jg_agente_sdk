# Documentación Técnica — `jg_agente_sdk`

Kit de Desarrollo Oficial y Fuente Única de Verdad (SSOT) de Contratos Públicos para el ecosistema `javiergalvez-ia`.

---

## 🌐 Estructura Multilingüe

La documentación técnica del SDK está organizada por directorios de idioma (ISO 639-1):

- 🇪🇸 **[Español (Fuente Canónica / SSOT)](es/)**:
  - [01. Guía Rápida de Inicio](es/01_quickstart.md)
  - [02. Especificación de Contratos y Modelos](es/02_contracts_spec.md)
  - [03. Referencia de Línea de Comandos (`jg`)](es/03_cli_reference.md)
  - [04. Testing y Harness de Desarrollo](es/04_testing_mock_runner.md)
  - [05. Despliegue Local y Ejecución con `jg_agente`](es/05_running_with_jg_agente.md)

- 🇬🇧 **[English (International Reference)](en/)**:
  - [01. Quickstart Guide](en/01_quickstart.md)
  - [02. Contracts & Models Specification](en/02_contracts_spec.md)
  - [03. CLI Reference (`jg`)](en/03_cli_reference.md)
  - [04. Testing & Mock Runner](en/04_testing_mock_runner.md)
  - [05. Local Deployment & Execution with `jg_agente`](en/05_running_with_jg_agente.md)

---

## Compilación Unificada

Para compilar la documentación consolidada del SDK para IAs externas y desarrolladores:
```bash
# Compilar versión canónica (español)
./workspace.sh docs jg_agente_sdk --locale=es

# Compilar versión en inglés
./workspace.sh docs jg_agente_sdk --locale=en

# Compilar todos los idiomas
./workspace.sh docs jg_agente_sdk --locale=all
```
