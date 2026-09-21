"""Cliente HTTP asíncrono y utilidades criptográficas HMAC-SHA256 para jg_agente.

Implementa la especificación criptográfica canónica compartida entre el Execution Plane
(jg_agente) y el Control Plane (jg_dashboard / GLOBAL-001):
    canonical_string = f"{METHOD}\n{PATH}\n{TIMESTAMP}\n{SHA256(RAW_BODY)}"
    signature = HMAC-SHA256(canonical_string, secret).hexdigest()
"""

import hashlib
import hmac
import json
import time
from typing import Any, Self
from urllib.parse import urlparse

import httpx

from jg_sdk.models import AgentInput, AgentOutput, ExecutionThreadDetail, UserContext

# Ventana de tolerancia temporal anti-repetición (5 minutos)
DEFAULT_MAX_TIMESTAMP_SKEW_SECONDS = 300


# =====================================================================
# 1. Utilidades Criptográficas HMAC-SHA256
# =====================================================================


def compute_body_sha256(body_bytes: bytes | None) -> str:
    """Calcula el hash SHA-256 en hexadecimal del cuerpo crudo de la petición.

    Para cuerpos vacíos o None, devuelve el hash estándar de b"".
    """
    data = body_bytes or b""
    return hashlib.sha256(data).hexdigest()


def compute_canonical_string(
    method: str,
    path: str,
    timestamp: str | int,
    body_bytes: bytes | None,
) -> str:
    """Construye la cadena canónica normalizada para la firma HMAC-SHA256.

    Formato:
        METHOD\nPATH\nTIMESTAMP\nBODY_SHA256
    """
    norm_method = method.strip().upper()
    # Si viene una URL completa, extraemos sólo el path
    parsed = urlparse(path)
    norm_path = parsed.path if parsed.path else path.strip()
    norm_timestamp = str(timestamp).strip()
    body_hash = compute_body_sha256(body_bytes)

    return f"{norm_method}\n{norm_path}\n{norm_timestamp}\n{body_hash}"


def compute_hmac_signature(secret: str, canonical_string: str) -> str:
    """Calcula la firma HMAC-SHA256 en formato hexadecimal."""
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=canonical_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


def verify_hmac_signature(secret: str, canonical_string: str, received_signature: str) -> bool:
    """Compara en tiempo constante la firma recibida con la firma esperada."""
    expected_signature = compute_hmac_signature(secret, canonical_string)
    return hmac.compare_digest(expected_signature.lower(), received_signature.strip().lower())


def verify_request_signature(
    secret: str,
    method: str,
    path: str,
    timestamp: str | int,
    body_bytes: bytes | None,
    received_signature: str,
    max_skew_seconds: int = DEFAULT_MAX_TIMESTAMP_SKEW_SECONDS,
) -> bool:
    """Verifica la validez de una firma HTTP comprobando también la ventana anti-replay.

    Args:
        secret: Secreto simétrico compartido.
        method: Verbo HTTP (GET, POST, etc.).
        path: Ruta URL de la petición.
        timestamp: Timestamp UNIX epoch enviado en cabecera.
        body_bytes: Cuerpo crudo de la petición.
        received_signature: Firma HMAC enviada en X-Signature.
        max_skew_seconds: Tolerancia máxima en segundos contra replay attacks.

    Returns:
        True si la firma es válida y el timestamp está dentro de la ventana de tolerancia.
    """
    try:
        ts_int = int(str(timestamp).strip())
    except ValueError:
        return False

    current_time = int(time.time())
    if abs(current_time - ts_int) > max_skew_seconds:
        return False

    canonical = compute_canonical_string(method, path, ts_int, body_bytes)
    return verify_hmac_signature(secret, canonical, received_signature)


# =====================================================================
# 2. Excepciones del Cliente
# =====================================================================


class AgentClientError(Exception):
    """Excepción base para errores del cliente HTTP de jg_agente."""


class AgentAuthError(AgentClientError):
    """Error de autenticación o rechazo de firma HMAC por parte del agente."""


class AgentResponseError(AgentClientError):
    """Respuesta con código de error HTTP emitida por el agente."""

    def __init__(self, status_code: int, detail: str, body: Any = None) -> None:
        super().__init__(f"HTTP {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail
        self.body = body


# =====================================================================
# 3. Cliente Asíncrono JGAgentClient
# =====================================================================


class JGAgentClient:
    """Cliente HTTP asíncrono para interactuar con la API REST de jg_agente.

    Genera automáticamente las cabeceras criptográficas de autenticación inter-servicio:
    - X-Agent-ID: Identificador único del agente destinatario.
    - X-Timestamp: Timestamp UNIX epoch actual.
    - X-Signature: Firma HMAC-SHA256 de la cadena canónica normalizada.
    - X-Correlation-ID: (Opcional) Identificador de trazabilidad distribuida.
    """

    def __init__(
        self,
        base_url: str,
        agent_id: str,
        secret: str,
        timeout: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Inicializa el cliente de comunicación con jg_agente.

        Args:
            base_url: URL base del servicio (e.g. "http://127.0.0.1:8000").
            agent_id: Identificador del agente registrado.
            secret: Secreto permanente compartido para la firma HMAC.
            timeout: Tiempo máximo de espera por petición en segundos.
            client: Instancia personalizada opcional de httpx.AsyncClient.
        """
        self.base_url = base_url.rstrip("/")
        self.agent_id = agent_id
        self.secret = secret
        self.timeout = timeout
        self._custom_client = client is not None
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self) -> Self:
        if not self._custom_client and self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        if not self._custom_client:
            await self.close()

    async def close(self) -> None:
        """Cierra la sesión HTTP asíncrona subyacente."""
        if not self._client.is_closed:
            await self._client.aclose()

    def _build_signed_headers(
        self,
        method: str,
        path: str,
        body_bytes: bytes | None,
        correlation_id: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """Calcula y devuelve las cabeceras HTTP firmadas requeridas por el Execution Plane."""
        timestamp = int(time.time())
        canonical_str = compute_canonical_string(method, path, timestamp, body_bytes)
        signature = compute_hmac_signature(self.secret, canonical_str)

        headers: dict[str, str] = {
            "X-Agent-ID": self.agent_id,
            "X-Timestamp": str(timestamp),
            "X-Signature": signature,
        }

        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id

        if extra_headers:
            headers.update(extra_headers)

        return headers

    async def request(
        self,
        method: str,
        path: str,
        *,
        json_data: Any = None,
        body_bytes: bytes | None = None,
        correlation_id: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Envía una petición HTTP autenticada con firma canónica HMAC-SHA256."""
        norm_path = path if path.startswith("/") else f"/{path}"
        url = f"{self.base_url}{norm_path}"

        raw_body: bytes | None = None
        req_headers: dict[str, str] = dict(headers or {})

        if json_data is not None:
            raw_body = json.dumps(json_data).encode("utf-8")
            req_headers["Content-Type"] = "application/json"
        elif body_bytes is not None:
            raw_body = body_bytes

        signed_headers = self._build_signed_headers(
            method=method,
            path=norm_path,
            body_bytes=raw_body,
            correlation_id=correlation_id,
            extra_headers=req_headers,
        )

        resp = await self._client.request(
            method=method.upper(),
            url=url,
            content=raw_body,
            headers=signed_headers,
        )

        if resp.status_code == 401:
            raise AgentAuthError(f"Rechazo de autenticación HMAC por el agente: {resp.text}")
        if resp.status_code >= 400:
            raise AgentResponseError(
                status_code=resp.status_code,
                detail=resp.text,
                body=resp.text,
            )

        return resp

    async def execute(
        self,
        prompt: str,
        thread_id: str | None = None,
        execution_id: str | None = None,
        user_context: UserContext | None = None,
        parameters: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        callback_url: str | None = None,
    ) -> AgentOutput:
        """Inicia una ejecución cognitiva enviando un AgentInput al agente.

        Args:
            prompt: Instrucción textual principal.
            thread_id: ID de hilo conversacional (se genera uno si es None).
            execution_id: ID de ejecución (se genera uno si es None).
            user_context: Contexto de identidad y permisos del usuario.
            parameters: Parámetros opcionales del flujo.
            correlation_id: ID de correlación distribuida.
            callback_url: URL de notificación para finalización asíncrona.

        Returns:
            Instancia de AgentOutput con el resultado de la ejecución.
        """
        import uuid

        t_id = thread_id or f"thread_{uuid.uuid4().hex[:12]}"
        e_id = execution_id or f"exec_{uuid.uuid4().hex[:12]}"

        agent_input = AgentInput(
            execution_id=e_id,
            thread_id=t_id,
            correlation_id=correlation_id,
            prompt=prompt,
            parameters=parameters or {},
            user_context=user_context,
            callback_url=callback_url,
        )

        payload = agent_input.model_dump(mode="json")
        resp = await self.request(
            method="POST",
            path="/executions/trigger",
            json_data=payload,
            correlation_id=correlation_id,
        )
        data = resp.json()
        return AgentOutput.model_validate(data)

    async def get_execution(self, thread_id: str) -> ExecutionThreadDetail:
        """Consulta el estado actual e historial de un hilo de ejecución."""
        resp = await self.request(
            method="GET",
            path=f"/executions/{thread_id}",
        )
        return ExecutionThreadDetail.model_validate(resp.json())

    async def approve(
        self,
        thread_id: str,
        approved: bool = True,
        approver: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Emite una decisión de aprobación humana (HITL) para una ejecución pausada."""
        endpoint = "approve" if approved else "reject"
        payload = {
            "approver": approver,
            "notes": notes,
        }
        resp = await self.request(
            method="POST",
            path=f"/executions/{thread_id}/{endpoint}",
            json_data=payload,
        )
        return resp.json()

    async def cancel(self, thread_id: str) -> dict[str, Any]:
        """Cancela la ejecución de un hilo activo."""
        resp = await self.request(
            method="POST",
            path=f"/executions/{thread_id}/reject",
        )
        return resp.json()

    async def health_check(self) -> dict[str, Any]:
        """Verifica la operatividad del Execution Plane."""
        resp = await self.request(method="GET", path="/health")
        return resp.json()


# Alias conveniente
AgentClient = JGAgentClient
