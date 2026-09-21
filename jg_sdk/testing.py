"""Utilidades de testing y harness de desarrollo para plugins de jg_agente.

Permite a los desarrolladores de plugins instanciar sus plugins e invocar
herramientas directamente mediante esquemas y modelos Pydantic, validar
compensaciones (rollbacks) y comprobar el ciclo de vida sin necesidad de
desplegar el orquestador jg_agente, LangGraph ni PostgreSQL.
"""

from typing import Any, Self

from pydantic import BaseModel

from jg_sdk.contracts import (
    AgentTool,
    BaseEngine,
    BasePlugin,
    PluginMetadata,
    ToolResult,
)


class MockPluginRunner:
    """Harness de ejecución y pruebas unitarias/integración para plugins.

    Proporciona un entorno controlado para simular la invocación de herramientas,
    validar esquemas Pydantic y evaluar los hooks de ciclo de vida del plugin.
    """

    def __init__(self, plugin: BasePlugin) -> None:
        """Inicializa el runner con una instancia del plugin bajo prueba."""
        if not isinstance(plugin, BasePlugin):
            raise TypeError(
                f"El plugin suministrado debe ser una subclase de BasePlugin, se recibió {type(plugin)}."
            )
        self.plugin = plugin
        self._metadata: PluginMetadata | None = None
        self._tools: dict[str, AgentTool] = {}
        self._engines: dict[str, BaseEngine] = {}
        self._initialized = False

    async def startup(self) -> None:
        """Inicializa el plugin, indexa sus herramientas/motores y ejecuta el hook startup."""
        self._metadata = self.plugin.get_plugin_metadata()
        self._tools = {t.name: t for t in self.plugin.register_tools()}
        self._engines = self.plugin.register_engines()
        await self.plugin.startup()
        self._initialized = True

    async def shutdown(self) -> None:
        """Ejecuta el hook shutdown del plugin."""
        if self._initialized:
            await self.plugin.shutdown()
            self._initialized = False

    async def health_check(self) -> dict[str, Any]:
        """Ejecuta el chequeo de salud del plugin."""
        return await self.plugin.health_check()

    async def __aenter__(self) -> Self:
        await self.startup()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        await self.shutdown()

    @property
    def metadata(self) -> PluginMetadata:
        """Retorna los metadatos del plugin inspeccionado."""
        if self._metadata is None:
            self._metadata = self.plugin.get_plugin_metadata()
        return self._metadata

    def list_tools(self) -> list[AgentTool]:
        """Devuelve la lista de herramientas registradas por el plugin."""
        if not self._tools:
            self._tools = {t.name: t for t in self.plugin.register_tools()}
        return list(self._tools.values())

    def get_tool(self, name: str) -> AgentTool:
        """Obtiene una herramienta específica por su identificador.

        Raises:
            KeyError: Si la herramienta no fue registrada por el plugin.
        """
        if not self._tools:
            self._tools = {t.name: t for t in self.plugin.register_tools()}
        if name not in self._tools:
            raise KeyError(
                f"Herramienta '{name}' no encontrada en el plugin '{self.plugin.name}'. "
                f"Disponibles: {list(self._tools.keys())}"
            )
        return self._tools[name]

    def list_engines(self) -> dict[str, BaseEngine]:
        """Devuelve el diccionario de motores registrados por el plugin."""
        if not self._engines:
            self._engines = self.plugin.register_engines()
        return dict(self._engines)

    def run_tool(
        self,
        tool_name: str,
        args: dict[str, Any] | BaseModel | None = None,
    ) -> ToolResult:
        """Ejecuta una herramienta validando previamente sus argumentos contra args_schema.

        Args:
            tool_name: Nombre de la herramienta a invocar.
            args: Diccionario de argumentos o instancia de BaseModel.

        Returns:
            ToolResult resultante de la invocación.

        Raises:
            KeyError: Si la herramienta no existe en el plugin.
            ValidationError: Si los argumentos no cumplen con args_schema.
        """
        tool = self.get_tool(tool_name)
        call_kwargs: dict[str, Any] = {}

        if args is not None:
            if isinstance(args, BaseModel):
                # Si se pasó un BaseModel y la tool tiene args_schema
                if tool.args_schema is not None and not isinstance(args, tool.args_schema):
                    # Validar/transformar si es de otro tipo BaseModel
                    validated = tool.args_schema.model_validate(args.model_dump())
                    call_kwargs = validated.model_dump()
                else:
                    call_kwargs = args.model_dump()
            elif isinstance(args, dict):
                # Validar contra el esquema Pydantic si está definido
                if tool.args_schema is not None:
                    validated = tool.args_schema.model_validate(args)
                    call_kwargs = validated.model_dump()
                else:
                    call_kwargs = dict(args)
            else:
                raise TypeError(
                    f"Los argumentos deben ser dict o BaseModel, se recibió {type(args)}."
                )

        return tool.run(**call_kwargs)

    def rollback_tool(
        self,
        tool_name: str,
        rollback_context: dict[str, Any],
    ) -> ToolResult:
        """Invoca la función de compensación (rollback) de una herramienta reversible.

        Args:
            tool_name: Nombre de la herramienta a compensar.
            rollback_context: Diccionario con el contexto capturado durante la ejecución.

        Returns:
            ToolResult emitido por el compensador.
        """
        tool = self.get_tool(tool_name)
        return tool.rollback(rollback_context)
