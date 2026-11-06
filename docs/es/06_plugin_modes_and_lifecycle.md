# 06. Modos de Trabajo y Ciclo de Vida de Plugins

Esta guía documenta los diferentes modelos de ejecución disponibles para desarrollar plugins en la plataforma `jg_agente` y explica el ciclo de vida estandarizado de desarrollo, inspección y desmantelamiento limpio mediante la CLI `jg`.

---

## 1. Filosofía de Arquitectura y Desacoplamiento

Los plugins desarrollados con `jg_agente_sdk` son librerías Python puras que implementan contratos de capacidades (`AgentTool`, `BaseEngine`, `BasePlugin`). Para su ejecución e inferencia cognitiva, dependen de un runtime de ejecución (`jg_agente`) impulsado por FastAPI y LangGraph.

Para facilitar la experiencia de desarrollo, el SDK permite operar en dos modalidades complementarias:

```text
+---------------------------------------------------------------------------------+
|                                MODOS DE TRABAJO                                 |
+---------------------------------------------------------------------------------+
|  MODO 1: AUTÓNOMO (Standalone)             MODO 2: COMPARTIDO (Monorepo)        |
|                                                                                 |
|  +------------------------------+          +---------------------------------+  |
|  | jg_plugin_<nombre>           |          | jg_agente (Runtime Central)     |  |
|  |  - docker-compose.yml propio |          |  - plugins/                     |  |
|  |    * jg_dashboard (:8880)    |          |    └── symlink -> jg_plugin_... |  |
|  |    * jg_agente (:8881)       |          +---------------------------------+  |
|  |    * PostgreSQL interno      |                                               |
|  +------------------------------+          Plugins conviven enlazados           |
|                                            en un único runtime.                 |
|  Stack aislado por plugin.                 Ideal para integración global.       |
|  Arranque con 'jg run'.                    Vinculación con 'jg link'.           |
+---------------------------------------------------------------------------------+
```

---

## 2. Los Dos Modos de Trabajo

### Modo 1: Autónomo (Standalone)

En este modo, el plugin dispone de su propio entorno aislado orquestado por un archivo `docker-compose.yml` en la raíz de su repositorio (generado automáticamente al ejecutar `jg init`).

- **Control Plane Local:** Panel Web HITL en `http://localhost:8880/admin` (credenciales por defecto: `admin@local.test` / `admin123456`).
- **Execution Plane Local:** Runtime `jg_agente` exclusivo para este plugin en `http://localhost:8881`.
- **Persistencia Aislada:** PostgreSQL en red interna Docker sin colisión de puertos.

#### Comandos Clave en Modo Autónomo:
```bash
# Iniciar el stack autónomo en segundo plano
jg run

# Ver logs en tiempo real
jg run -l

# Inspeccionar estado de los servicios autónomos
jg run -s

# Detener el stack autónomo
jg run --down
```

### Modo 2: Compartido / Integrado (Monorepo)

En este modo, el plugin no requiere levantar contenedores adicionales. Se conecta directamente a una instancia en ejecución de `jg_agente` (o a uno de los agentes especializados del ecosistema como `jg_agente_conversacional` o `jg_agente_devops`) mediante **enlaces simbólicos relativos portables** dentro del directorio `plugins/` del agente.

#### Comandos Clave en Modo Compartido:
```bash
# Vincular el plugin al agente en desarrollo (crea symlink)
jg link

# Recargar los plugins en caliente en el agente sin reiniciar bases de datos
jg reload

# Desvincular el plugin del agente
jg unlink <nombre_plugin>
```

---

## 3. Inspección Contextual con `jg status`

El comando `jg status` es inteligente y sensible al contexto del directorio de trabajo:

1. **Si se ejecuta dentro de la carpeta de un plugin (`jg_plugin_*`):**
   Inspecciona exclusivamente el estado de **ese plugin**:
   - Detecta si está en modo Autónomo o Compartido.
   - Comprueba si existe un symlink activo en `jg_agente/plugins/`.
   - Consulta al daemon de Docker si existen contenedores asociados a este plugin (activos o detenidos).
   - Verifica la respuesta HTTP de su endpoint de salud (`/health`) y capacidades cargadas (`/capabilities`).
   - Diagnostica si el plugin está en uso o si su estado es completamente limpio.

2. **Si se ejecuta en una carpeta raíz o no perteneciente a un plugin (o con el flag `-g` / `--global`):**
   Inspecciona la salud global de todos los servicios del ecosistema `javiergalvez-ia` (`jg_hub`, `jg_dashboard`, agentes cognitivos y bases de datos).

---

## 4. Limpieza y Desmantelamiento con `jg clean`

Cuando un desarrollador finaliza el trabajo sobre un plugin, desea archivarlo en Git o eliminar su carpeta local, antes existía el riesgo de dejar contenedores Docker huérfanos, volúmenes retenidos o symlinks rotos en el agente.

El comando `jg clean` (disponible también como `jg plugin clean`) unifica y automatiza todo el proceso de desmantelamiento en un solo paso:

```bash
# Limpiar el plugin del directorio actual
jg clean

# O especificar el nombre del plugin desde cualquier directorio
jg clean <nombre_plugin>

# Limpiar eliminando también el entorno virtual (.venv)
jg clean --all
```

### ¿Qué ejecuta `jg clean` de forma determinista?

1. **Apagado de Docker Compose:** Si el plugin cuenta con `docker-compose.yml`, ejecuta `docker compose down` eliminando redes y contenedores locales.
2. **Eliminación de Contenedores Host:** Busca y elimina de forma forzada cualquier contenedor Docker asociado (`jg_agente_<slug>`, `jg_dashboard_<slug>`, etc.).
3. **Desvinculación Segura (Unlink):** Elimina los enlaces simbólicos del plugin que existan en el directorio `plugins/` del agente.
4. **Purga de Cachés:** Elimina directorios `__pycache__`, `.pytest_cache`, `.ruff_cache` y metadatos de empaquetado `.egg-info`. Si se especifica `--all`, elimina también el `.venv`.
5. **Certificación de Estado Seguro:** Muestra un informe confirmando que no quedan recursos residuales y que la carpeta puede archivarse o eliminarse mediante `rm -rf` sin impacto en el resto del sistema.

