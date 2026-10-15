# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez <contacto@javiergalvez.com>
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Tests de cálculo criptográfico HMAC-SHA256, anti-replay y cliente JGAgentClient."""

import hashlib
import hmac
import time
import unittest

import httpx

from jg_sdk.client import (
    AgentAuthError,
    AgentResponseError,
    JGAgentClient,
    compute_body_sha256,
    compute_canonical_string,
    compute_hmac_signature,
    verify_hmac_signature,
    verify_request_signature,
)
from jg_sdk.models import AgentOutput, ExecutionStatus


class TestHMACCryptography(unittest.TestCase):
    """Valida la especificación criptográfica canónica HMAC-SHA256."""

    def test_compute_body_sha256_empty(self) -> None:
        expected = hashlib.sha256(b"").hexdigest()
        self.assertEqual(compute_body_sha256(None), expected)
        self.assertEqual(compute_body_sha256(b""), expected)

    def test_compute_body_sha256_payload(self) -> None:
        payload = b'{"prompt": "hola"}'
        expected = hashlib.sha256(payload).hexdigest()
        self.assertEqual(compute_body_sha256(payload), expected)

    def test_canonical_string_format(self) -> None:
        method = "post"
        path = "/api/v1/executions"
        timestamp = 1700000000
        body_bytes = b'{"test": 123}'
        body_hash = hashlib.sha256(body_bytes).hexdigest()

        canonical = compute_canonical_string(method, path, timestamp, body_bytes)
        expected = f"POST\n/api/v1/executions\n1700000000\n{body_hash}"
        self.assertEqual(canonical, expected)

    def test_canonical_string_with_full_url(self) -> None:
        url = "http://127.0.0.1:8000/api/v1/executions"
        canonical = compute_canonical_string("get", url, 1700000000, None)
        empty_hash = hashlib.sha256(b"").hexdigest()
        self.assertEqual(canonical, f"GET\n/api/v1/executions\n1700000000\n{empty_hash}")

    def test_hmac_signature_generation_and_verification(self) -> None:
        secret = "secret-key-123456"
        canonical = "POST\n/api/v1/executions\n1700000000\ne3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

        expected = hmac.new(
            secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        sig = compute_hmac_signature(secret, canonical)
        self.assertEqual(sig, expected)
        self.assertTrue(verify_hmac_signature(secret, canonical, sig))
        self.assertFalse(verify_hmac_signature("wrong-secret", canonical, sig))
        self.assertFalse(verify_hmac_signature(secret, canonical, "bad_signature"))

    def test_verify_request_signature_anti_replay(self) -> None:
        secret = "super-secret"
        method = "POST"
        path = "/api/v1/executions"
        body = b'{"msg": "test"}'
        current_time = int(time.time())

        # 1. Petición en tiempo presente (válida)
        canonical_now = compute_canonical_string(method, path, current_time, body)
        sig_now = compute_hmac_signature(secret, canonical_now)
        self.assertTrue(
            verify_request_signature(
                secret, method, path, current_time, body, sig_now, max_skew_seconds=300
            )
        )

        # 2. Petición dentro de la ventana de tolerancia (e.g. 150 segundos antes)
        ts_valid_past = current_time - 150
        canonical_past = compute_canonical_string(method, path, ts_valid_past, body)
        sig_past = compute_hmac_signature(secret, canonical_past)
        self.assertTrue(
            verify_request_signature(
                secret, method, path, ts_valid_past, body, sig_past, max_skew_seconds=300
            )
        )

        # 3. Petición fuera de la ventana de tolerancia (> 300 segundos, ataque de repetición)
        ts_expired = current_time - 305
        canonical_exp = compute_canonical_string(method, path, ts_expired, body)
        sig_exp = compute_hmac_signature(secret, canonical_exp)
        self.assertFalse(
            verify_request_signature(
                secret, method, path, ts_expired, body, sig_exp, max_skew_seconds=300
            )
        )

        # 4. Timestamp malformado
        self.assertFalse(
            verify_request_signature(secret, method, path, "not-a-number", body, sig_now)
        )


class TestJGAgentClient(unittest.IsolatedAsyncioTestCase):
    """Valida el comportamiento y transporte de JGAgentClient."""

    async def test_signed_headers_generation(self) -> None:
        client = JGAgentClient(
            base_url="http://agent.local:8000",
            agent_id="test-agent-01",
            secret="shared-key",
        )
        headers = client._build_signed_headers(
            method="POST",
            path="/api/v1/executions",
            body_bytes=b"test-body",
            correlation_id="corr-xyz",
        )

        self.assertEqual(headers["X-Agent-ID"], "test-agent-01")
        self.assertIn("X-Timestamp", headers)
        self.assertIn("X-Signature", headers)
        self.assertEqual(headers["X-Correlation-ID"], "corr-xyz")

        # Comprobar que la firma en X-Signature sea válida
        ts = int(headers["X-Timestamp"])
        canonical = compute_canonical_string("POST", "/api/v1/executions", ts, b"test-body")
        expected_sig = compute_hmac_signature("shared-key", canonical)
        self.assertEqual(headers["X-Signature"], expected_sig)
        await client.close()

    async def test_execute_success_with_mock_transport(self) -> None:
        captured_requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured_requests.append(request)
            mock_output = {
                "execution_id": "exec_123",
                "thread_id": "thread_456",
                "status": "completed",
                "response": "Ejecución completada con éxito.",
                "data": {"key": "val"},
                "execution_time_ms": 150.0,
            }
            return httpx.Response(200, json=mock_output)

        mock_transport = httpx.MockTransport(handler)
        async_client = httpx.AsyncClient(transport=mock_transport)

        client = JGAgentClient(
            base_url="http://agent.local",
            agent_id="agent-01",
            secret="agent-secret",
            client=async_client,
        )

        output = await client.execute(
            prompt="Desplegar cluster",
            thread_id="thread_456",
            execution_id="exec_123",
        )

        self.assertIsInstance(output, AgentOutput)
        self.assertEqual(output.status, ExecutionStatus.COMPLETED)
        self.assertEqual(output.response, "Ejecución completada con éxito.")

        self.assertEqual(len(captured_requests), 1)
        req = captured_requests[0]
        self.assertEqual(req.headers.get("X-Agent-ID"), "agent-01")
        self.assertIn("X-Signature", req.headers)
        await client.close()

    async def test_client_auth_error_on_401(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, text="Signature mismatch")

        mock_transport = httpx.MockTransport(handler)
        async_client = httpx.AsyncClient(transport=mock_transport)

        client = JGAgentClient(
            base_url="http://agent.local",
            agent_id="agent-01",
            secret="bad-secret",
            client=async_client,
        )

        with self.assertRaises(AgentAuthError):
            await client.health_check()
        await client.close()

    async def test_client_response_error_on_500(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error")

        mock_transport = httpx.MockTransport(handler)
        async_client = httpx.AsyncClient(transport=mock_transport)

        client = JGAgentClient(
            base_url="http://agent.local",
            agent_id="agent-01",
            secret="agent-secret",
            client=async_client,
        )

        with self.assertRaises(AgentResponseError) as ctx:
            await client.cancel(thread_id="thread_123")
        self.assertEqual(ctx.exception.status_code, 500)
        await client.close()


if __name__ == "__main__":
    unittest.main()
