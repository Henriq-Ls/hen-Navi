import json
import unittest
from unittest.mock import patch

import _SERVICOS_.ai_service as ai_service
from _SERVICOS_.ai_service import (
    HttpTransport,
    HttpResult,
    ProviderClient,
    ProviderRequestError,
    truncate_page_text,
    validate_base_url,
)


class FakeTransport:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def request(self, method, url, *, headers=None, body=None):
        self.requests.append((method, url, headers or {}, body))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def cancel(self):
        pass


def result(status=200, body=None, headers=None):
    encoded = body if isinstance(body, bytes) else json.dumps(body or {}).encode()
    return HttpResult(status, headers or {}, encoded)


class AiServiceTests(unittest.TestCase):
    def test_private_http_urls_are_allowed(self):
        self.assertEqual(
            validate_base_url("http://localhost:11434/"),
            "http://localhost:11434",
        )
        self.assertEqual(
            validate_base_url("http://192.168.1.20:8080/v1/"),
            "http://192.168.1.20:8080/v1",
        )
        self.assertEqual(
            validate_base_url("http://[::1]:11434/"),
            "http://[::1]:11434",
        )

    def test_http_public_and_credentials_in_url_are_rejected(self):
        for url in (
            "http://example.com/api",
            "http://8.8.8.8:8080/v1",
            "http://169.254.1.1:11434",
            "http://0.0.0.0:11434",
            "http://localhost:0",
            "https://user:secret@example.com/v1",
            "https://example.com/v1?token=secret",
        ):
            with self.subTest(url=url), self.assertRaises(ProviderRequestError):
                validate_base_url(url)

    def test_https_remote_url_is_allowed(self):
        self.assertEqual(
            validate_base_url("https://api.example.com/v1/"),
            "https://api.example.com/v1",
        )

    def test_page_text_is_truncated_and_flagged(self):
        self.assertEqual(truncate_page_text("abc", 3), ("abc", False))
        self.assertEqual(truncate_page_text("abcdef", 4), ("abcd", True))

    def test_ollama_model_list_uses_native_endpoint(self):
        transport = FakeTransport(
            result(body={"models": [{"name": "llama3:8b"}, {"name": "qwen2"}]})
        )
        client = ProviderClient(
            {"kind": "ollama", "base_url": "http://localhost:11434"},
            transport=transport,
        )
        self.assertEqual(client.list_models(), ["llama3:8b", "qwen2"])
        self.assertEqual(transport.requests[0][1], "http://localhost:11434/api/tags")

    def test_openai_compatible_models_and_answer(self):
        transport = FakeTransport(
            result(body={"data": [{"id": "dynamic-model"}]}),
            result(body={"choices": [{"message": {"content": "Resposta"}}]}),
        )
        client = ProviderClient(
            {
                "kind": "openai_compatible",
                "base_url": "https://provider.example/v1",
                "model": "dynamic-model",
            },
            "unit-test-secret",
            transport=transport,
        )
        self.assertEqual(client.list_models(), ["dynamic-model"])
        answer, truncated = client.ask("conteúdo", "pergunta")
        self.assertEqual((answer, truncated), ("Resposta", False))
        method, url, headers, body = transport.requests[1]
        self.assertEqual((method, url), ("POST", "https://provider.example/v1/chat/completions"))
        self.assertEqual(headers["Authorization"], "Bearer unit-test-secret")
        payload = json.loads(body)
        self.assertIn('"conteúdo"', payload["messages"][-1]["content"])
        self.assertEqual(payload["messages"][-1]["role"], "user")

    def test_http_trace_records_status_without_logging_secret_or_page_text(self):
        transport = FakeTransport(
            result(body={"choices": [{"message": {"content": "Resposta segura"}}]})
        )
        client = ProviderClient(
            {
                "kind": "openai_compatible",
                "base_url": "https://provider.example/v1",
                "model": "dynamic-model",
            },
            "sensitive-test-token",
            transport=transport,
        )

        with patch.object(ai_service.log, "info") as info_log:
            answer, _ = client.ask(
                "conteúdo privado da página",
                "pergunta privada do usuário",
            )

        messages = "\n".join(str(call.args[-1]) for call in info_log.call_args_list)
        self.assertEqual(answer, "Resposta segura")
        self.assertIn("HTTP iniciado", messages)
        self.assertIn("status=200", messages)
        self.assertNotIn("sensitive-test-token", messages)
        self.assertNotIn("conteúdo privado", messages)
        self.assertNotIn("pergunta privada", messages)

    def test_ollama_chat_uses_native_non_streaming_protocol(self):
        transport = FakeTransport(
            result(body={"message": {"content": "Resumo"}})
        )
        client = ProviderClient(
            {
                "kind": "ollama",
                "base_url": "http://localhost:11434",
                "model": "llama3",
            },
            transport=transport,
        )
        answer, _ = client.ask("texto", "", summarize=True)
        self.assertEqual(answer, "Resumo")
        method, url, headers, body = transport.requests[0]
        self.assertEqual((method, url), ("POST", "http://localhost:11434/api/chat"))
        self.assertNotIn("Authorization", headers)
        self.assertFalse(json.loads(body)["stream"])

    def test_models_empty_list_and_invalid_shape(self):
        client = ProviderClient(
            {"kind": "openai_compatible", "base_url": "https://api.example/v1"},
            transport=FakeTransport(result(body={"data": []})),
        )
        self.assertEqual(client.list_models(), [])

        client = ProviderClient(
            {"kind": "ollama", "base_url": "http://localhost:11434"},
            transport=FakeTransport(result(body={"wrong": []})),
        )
        with self.assertRaisesRegex(ProviderRequestError, "lista de modelos"):
            client.list_models()

    def test_http_error_mapping_includes_retry_after(self):
        cases = (
            (401, {}, "Chave inválida"),
            (404, {}, "Endpoint ou modelo"),
            (429, {"retry-after": "12"}, "12 segundo"),
            (500, {}, "HTTP 500"),
        )
        for status, headers, expected in cases:
            with self.subTest(status=status):
                client = ProviderClient(
                    {"kind": "ollama", "base_url": "http://localhost:11434"},
                    transport=FakeTransport(result(status=status, headers=headers)),
                )
                with self.assertRaises(ProviderRequestError) as error:
                    client.list_models()
                self.assertIn(expected, str(error.exception))

    def test_redirect_is_not_followed(self):
        class RedirectResponse:
            status = 302

            def read(self, _limit):
                return b""

            def getheaders(self):
                return [("Location", "http://public.example/steal")]

        class RedirectConnection:
            requested = []

            def __init__(self, *_args, **_kwargs):
                pass

            def request(self, method, target, *, body=None, headers=None):
                self.requested.append((method, target, headers))

            def getresponse(self):
                return RedirectResponse()

            def close(self):
                pass

        with patch.object(ai_service.http.client, "HTTPConnection", RedirectConnection):
            transport = HttpTransport()
            with self.assertRaisesRegex(ProviderRequestError, "redirecionamentos"):
                transport.request(
                    "GET",
                    "http://localhost:11434/api/tags",
                    headers={"Authorization": "Bearer secret"},
                )
        self.assertEqual(len(RedirectConnection.requested), 1)
        self.assertEqual(
            RedirectConnection.requested[0][1],
            "/api/tags",
        )

    def test_ollama_unavailable_has_specific_message(self):
        client = ProviderClient(
            {"kind": "ollama", "base_url": "http://localhost:11434"},
            transport=FakeTransport(
                ProviderRequestError("Não foi possível conectar ao provedor.")
            ),
        )
        with self.assertRaisesRegex(ProviderRequestError, "Ollama indisponível"):
            client.list_models()

    def test_empty_answer_fails_clearly(self):
        client = ProviderClient(
            {
                "kind": "openai_compatible",
                "base_url": "https://api.example/v1",
                "model": "m",
            },
            transport=FakeTransport(result(body={"choices": [{"message": {"content": " "}}]})),
        )
        with self.assertRaisesRegex(ProviderRequestError, "resposta vazia"):
            client.ask("texto", "pergunta")


if __name__ == "__main__":
    unittest.main()
