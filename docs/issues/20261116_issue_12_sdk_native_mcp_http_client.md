# Issue 03: [jg_agente_sdk] Feat: Implementación del cliente nativo McpHttpClient con Streamable HTTP y Schema Pinning

- **Título:** `[jg_agente_sdk] Feat: Implementación del cliente nativo McpHttpClient con Streamable HTTP y Schema Pinning`
- **Prioridad y Fase:** Crítica | Fase 1: SDK & Cliente MCP
- **Dependencias:** Issue 01 (`[jg_agente_sdk] Fix: Soporte nativo para herramientas asíncronas`), Issue 02 (`[jg_agente_sdk] Refactor: Centralización del módulo unificado de protección SSRF y DNS Pinning`)
- **Contexto Técnico y Archivos Afectados:**
  - Hallazgos del informe: `H-06` (URL de servidor MCP proviene de configuración y no se valida por `SecurityGuard`), `H-09` (`DualPostgresSaver` requiere normalización estricta a tipos primitivos JSON sin bytes ni objetos arbitrarios).
  - Regla estricta 1: Implementación nativa en Python usando exclusivamente `httpx.AsyncClient` + JSON-RPC 2.0 puro (sin la dependencia externa `mcp` de PyPI). Transporte Streamable HTTP (`POST`), Schema Pinning SHA-256 de `(name + description + inputSchema)`, capacidades vacías (`capabilities: {}`), normalización estricta a primitivos JSON y truncado a 64 KB.
  - Archivos a crear/modificar:
    - `jg_agente_sdk/jg_sdk/mcp/__init__.py` (Crear)
    - `jg_agente_sdk/jg_sdk/mcp/schemas.py` (Crear)
    - `jg_agente_sdk/jg_sdk/mcp/client.py` (Crear)
    - `jg_agente_sdk/tests/test_mcp_client.py` (Crear)

---

## Especificación Técnica

### 1. `jg_sdk/mcp/schemas.py`
- Modelos Pydantic v2 para mensajes JSON-RPC 2.0:
  ```python
  class JsonRpcRequest(BaseModel):
      jsonrpc: Literal["2.0"] = "2.0"
      id: str | int
      method: str
      params: dict[str, Any] | None = None

  class JsonRpcResponse(BaseModel):
      jsonrpc: Literal["2.0"] = "2.0"
      id: str | int | None = None
      result: Any = None
      error: dict[str, Any] | None = None
  ```
- Esquemas de respuesta MCP estándar para `initialize`, `tools/list` y `tools/call`.

### 2. `jg_sdk/mcp/client.py`
- Clase `McpHttpClient`:
  ```python
  class McpHttpClient:
      def __init__(
          self,
          base_url: str,
          timeout_sec: float = 30.0,
          max_output_bytes: int = 65536, # 64 KB
          transport: httpx.AsyncBaseTransport | None = None,
          ssrf_validator: SSRFValidator | None = None,
      ) -> None: ...
      
      async def initialize(self) -> dict[str, Any]:
          """Envía método 'initialize' con capabilities: {} (sin sampling/elicitation) y protocolVersion."""
          
      async def list_tools_with_pinning(self) -> list[AgentTool]:
          """Descubre tools remotas y computa el hash SHA-256 de (name + description + inputSchema)."""
          
      def compute_schema_hash(self, tool_def: dict[str, Any]) -> str:
          """Calcula hash determinista SHA-256 canónico del esquema."""
          
      async def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolResult:
          """Invoca la tool remota vía POST JSON-RPC, verifica el schema pinning, normaliza y trunca la salida."""
  ```
- **Protección contra Drift y Rug Pull:**
  - Si el servidor altera dinámicamente el esquema de argumentos o la descripción de una herramienta tras el arranque, `call_tool()` lanza `SchemaDriftError` y bloquea la llamada.
- **Normalización Estricta de Salida:**
  - Todo resultado de `tools/call` se analiza para convertir cualquier contenido a tipos estándar de Python (`dict`, `list`, `str`, `int`, `float`, `bool`, `None`).
  - Si la salida en texto o JSON excede los 64 KB (65.536 bytes), se trunca de forma segura añadiendo el sufijo `... [TRUNCATED_AT_64KB]`.
- **Integración con SSRF:**
  - `McpHttpClient` valida `base_url` contra `SSRFValidator` antes de abrir el socket HTTP, aplicando DNS Pinning.

---

## Criterios de Aceptación (Checklist Verificable)

- [ ] Test unitario con `httpx.MockTransport` que simula el ciclo de vida completo: `initialize` -> `tools/list` -> `tools/call`.
- [ ] Verificación de que `initialize` envía estrictamente `capabilities: {}` (sin declarar capacidades de muestreo o elicitación).
- [ ] Test unitario que valida la detección de *Schema Drift* / *Rug Pull*: si una tool remota modifica su `inputSchema`, `call_tool` falla inmediatamente con `SchemaDriftError`.
- [ ] Test unitario que comprueba el truncado estricto a 64 KB cuando el servidor MCP responde con un payload excesivo.
- [ ] Test unitario que valida que la salida devuelta en `ToolResult.output` es serializable en `msgpack` y JSON sin romper `DualPostgresSaver`.
- [ ] Suite de tests ejecutada con `pytest tests/test_mcp_client.py` pasando al 100% sin dependencias de red ni binarios externos.
