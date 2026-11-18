# Backlog QA & Seguridad Consolidado — `jg_agente_sdk`

**Repositorio GitLab:** `https://gitlab.com/javiergalvez-ia/jg_agente_sdk`  
**Responsable Asignado:** `cabocom` / Javier Gálvez (`assignee_ids: [553306]`)  
**Total de Issues en `jg_agente_sdk`:** **4**

## Índice de Issues de Remediación

| ID | Severidad | Categoría | Título | Consenso Modelos | Archivo Local | Issue GitLab |
| :--- | :---: | :--- | :--- | :--- | :--- | :--- |
| `ISSUE-01` | **Blocker** | `Seguridad` | fix(cli): Incluir .env en la plantilla .gitignore generada por jg init | Detectado por: `argon` — Omitido por: `claude-sonnet`, `flash-3.8`, `hydrogen` | [ISSUE-01_gitignore_env_template_jg_init.md](./ISSUE-01_gitignore_env_template_jg_init.md) | [#13](https://gitlab.com/javiergalvez-ia/jg_agente_sdk/-/work_items/13) |
| `ISSUE-02` | **Critical** | `Seguridad / Fiabilidad-Bug` | fix(security): Corregir bloqueo falso con enforce=False, excepción DNS en resolve_and_pin_url y bypass SSRF por redirecciones en McpHttpClient | Detectado por: `argon` — Omitido por: `claude-sonnet`, `flash-3.8`, `hydrogen` | [ISSUE-02_ssrf_enforce_false_dns_mcp_redirects.md](./ISSUE-02_ssrf_enforce_false_dns_mcp_redirects.md) | [#14](https://gitlab.com/javiergalvez-ia/jg_agente_sdk/-/work_items/14) |
| `ISSUE-03` | **Critical** | `Seguridad / Fiabilidad-Bug` | feat(auth): Soportar firma canónica HMAC de 5 componentes con X-Nonce en jg_sdk.auth y JGAgentClient | Detectado por: `argon` — Omitido por: `claude-sonnet`, `flash-3.8`, `hydrogen` | [ISSUE-03_hmac_5_components_x_nonce_sdk.md](./ISSUE-03_hmac_5_components_x_nonce_sdk.md) | [#15](https://gitlab.com/javiergalvez-ia/jg_agente_sdk/-/work_items/15) |
| `ISSUE-04` | **Major** | `DRY-Duplicación / Complejidad-CodeSmell` | refactor(cli): Unificar detección de paquetes, eliminar acoplamiento a Eloquent en dev_cmd y limpiar except Exception: pass | Detectado por: `argon`, `claude-sonnet`, `hydrogen`, `flash-3.8` | [ISSUE-04_cli_dry_eloquent_coupling_silent_catches.md](./ISSUE-04_cli_dry_eloquent_coupling_silent_catches.md) | [#16](https://gitlab.com/javiergalvez-ia/jg_agente_sdk/-/work_items/16) |
