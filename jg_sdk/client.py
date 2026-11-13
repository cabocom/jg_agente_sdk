# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Cliente HTTP asíncrono y utilidades criptográficas HMAC-SHA256 para jg_agente.

Implementa la especificación criptográfica canónica compartida entre el Execution Plane
(jg_agente) y el Control Plane (jg_dashboard / GLOBAL-001):
    canonical_string = f"{METHOD}\\n{PATH}\\n{TIMESTAMP}\\n{SHA256(RAW_BODY)}"
    signature = HMAC-SHA256(canonical_string, secret).hexdigest()
"""

import json
import time
from typing import Any, Self

import httpx

from jg_sdk.auth import (
    DEFAULT_MAX_TIMESTAMP_SKEW_SECONDS,
    AgentAuthError,
    AgentClientError,
    AgentResponseError,
    compute_body_sha256,
    compute_canonical_string,
    compute_hmac_signature,
    verify_hmac_signature,
    verify_request_signature,
)
from jg_sdk.models import AgentInput, AgentOutput, ExecutionThreadDetail, UserContext

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
        json_data: Any = None,
        content: bytes | None = None,
        correlation_id: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Ejecuta una petición HTTP asíncrona autenticada con firma HMAC-SHA256."""
        # 1. Resolver el cuerpo crudo en bytes para la firma
        body_bytes: bytes | None = None
        if content is not None:
            body_bytes = content
        elif json_data is not None:
            # Serialización canónica estándar (sin espacios redundantes)
            body_bytes = json.dumps(json_data, separators=(",", ":")).encode("utf-8")

        # 2. Generar cabeceras autenticadas
        req_headers = self._build_signed_headers(
            method=method,
            path=path,
            body_bytes=body_bytes,
            correlation_id=correlation_id,
            extra_headers=extra_headers,
        )

        if json_data is not None and "Content-Type" not in req_headers:
            req_headers["Content-Type"] = "application/json"

        # 3. Despachar petición
        url = f"{self.base_url}{path}"
        try:
            resp = await self._client.request(
                method=method,
                url=url,
                content=body_bytes,
                headers=req_headers,
            )
        except httpx.RequestError as exc:
            raise AgentClientError(f"Error de red al conectar con jg_agente: {exc}") from exc

        # 4. Manejo de errores de transporte y autenticación
        if resp.status_code in (401, 403):
            raise AgentAuthError(
                f"Error de autenticación inter-servicio ({resp.status_code}): {resp.text}"
            )

        if resp.is_error:
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
        data = resp.json()
        return ExecutionThreadDetail.model_validate(data)

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

__all__ = [
    "DEFAULT_MAX_TIMESTAMP_SKEW_SECONDS",
    "AgentAuthError",
    "AgentClient",
    "AgentClientError",
    "AgentResponseError",
    "JGAgentClient",
    "compute_body_sha256",
    "compute_canonical_string",
    "compute_hmac_signature",
    "verify_hmac_signature",
    "verify_request_signature",
]
