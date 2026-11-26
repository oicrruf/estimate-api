"""Contrato SDK simulado: objeto HTTP tipado, sin cuerpo crudo ni red."""

import asyncio
import json
import sys
from types import SimpleNamespace
from typing import Any

import pytest

from demo.private_model import DEFAULT_MODEL, OpenAIJsonExtractor, configured_model


def test_default_luna_request_and_typed_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class FakeRaw:
        status_code = 200

        def parse(self) -> SimpleNamespace:
            captured["parseCalls"] = captured.get("parseCalls", 0) + 1
            return SimpleNamespace(
                status="completed",
                output_text=json.dumps({"requested_quantity": 2}),
                usage=SimpleNamespace(input_tokens=31, output_tokens=14),
            )

        def json(self) -> None:
            raise AssertionError("No usar raw.json()")

    class FakeRawResponses:
        async def create(self, **kwargs: object) -> FakeRaw:
            captured["request"] = kwargs
            return FakeRaw()

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            captured["client"] = kwargs
            self.responses = SimpleNamespace(with_raw_response=FakeRawResponses())

        async def close(self) -> None:
            captured["closed"] = True

    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-only")
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=FakeClient))
    extractor = OpenAIJsonExtractor(
        prompt="Extrae cámara", schema={"type": "object"}, name="test_camera"
    )
    body, metrics = asyncio.run(extractor.extract("Dos cámaras ficticias"))
    assert DEFAULT_MODEL == "gpt-6-luna"
    assert body == {"requested_quantity": 2}
    assert metrics == {"httpStatus": 200, "inputTokens": 31, "outputTokens": 14}
    assert captured["client"] == {"timeout": 15.0, "max_retries": 0}
    assert captured["request"]["model"] == "gpt-6-luna"
    assert captured["request"]["reasoning"] == {"effort": "none"}
    assert captured["request"]["store"] is False
    assert captured["request"]["tools"] == []
    assert captured["request"]["max_output_tokens"] == 500
    assert captured["request"]["text"]["format"]["strict"] is True
    assert captured["parseCalls"] == 1
    assert captured["closed"] is True


def test_explicit_model_has_no_fallback() -> None:
    assert configured_model("gpt-6-luna") == "gpt-6-luna"
    assert configured_model("gpt-6-sol") == "gpt-6-sol"
    with pytest.raises(ValueError, match="ID de modelo inválido"):
        configured_model("../../other")


@pytest.mark.parametrize(
    ("http_status", "response_status", "body", "input_tokens", "output_tokens"),
    [
        (503, "completed", '{"requested_quantity":2}', 30, 20),
        (200, "incomplete", '{"requested_quantity":2}', 30, 20),
        (200, "completed", "not-json", 30, 20),
        (200, "completed", '{"requested_quantity":2}', 4001, 20),
        (200, "completed", '{"requested_quantity":2}', 30, 501),
    ],
)
def test_sdk_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    http_status: int,
    response_status: str,
    body: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    closed = []

    class FakeRaw:
        status_code = http_status

        def parse(self) -> SimpleNamespace:
            return SimpleNamespace(
                status=response_status,
                output_text=body,
                usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
            )

        def json(self) -> None:
            raise AssertionError("No usar raw.json()")

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            self.responses = SimpleNamespace(with_raw_response=SimpleNamespace(create=self.create))

        async def create(self, **kwargs: object) -> FakeRaw:
            assert kwargs["model"] == "gpt-6-luna"
            return FakeRaw()

        async def close(self) -> None:
            closed.append(True)

    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-only")
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=FakeClient))
    extractor = OpenAIJsonExtractor(prompt="Ficticio", schema={"type": "object"}, name="test")
    with pytest.raises((ValueError, json.JSONDecodeError)):
        asyncio.run(extractor.extract("Dos cámaras ficticias"))
    assert closed == [True]


def test_missing_key_blocks_request_before_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    extractor = OpenAIJsonExtractor(prompt="Ficticio", schema={"type": "object"}, name="test")
    with pytest.raises(ValueError, match="OPENAI_API_KEY ausente"):
        asyncio.run(extractor.extract("Dos cámaras ficticias"))


def test_pinned_sdk_parses_mock_http_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx2
    import openai

    original_client = openai.AsyncOpenAI
    requests: list[dict[str, Any]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(json.loads(request.content))
        return httpx2.Response(
            200,
            json={
                "id": "resp_synthetic",
                "object": "response",
                "created_at": 0,
                "model": "gpt-6-luna",
                "status": "completed",
                "output": [
                    {
                        "id": "msg_synthetic",
                        "type": "message",
                        "status": "completed",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": '{"requested_quantity":2}',
                                "annotations": [],
                            }
                        ],
                    }
                ],
                "usage": {"input_tokens": 31, "output_tokens": 14, "total_tokens": 45},
                "tools": [],
                "tool_choice": "auto",
                "parallel_tool_calls": False,
            },
        )

    def local_client(*, timeout: float, max_retries: int) -> openai.AsyncOpenAI:
        return original_client(
            api_key="x",
            http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)),
            timeout=timeout,
            max_retries=max_retries,
        )

    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-only")
    monkeypatch.setattr(openai, "AsyncOpenAI", local_client)
    extractor = OpenAIJsonExtractor(prompt="Ficticio", schema={"type": "object"}, name="test")
    body, metrics = asyncio.run(extractor.extract("Dos cámaras ficticias"))
    assert body == {"requested_quantity": 2}
    assert metrics == {"httpStatus": 200, "inputTokens": 31, "outputTokens": 14}
    assert len(requests) == 1
    assert requests[0]["model"] == "gpt-6-luna"
    assert requests[0]["reasoning"] == {"effort": "none"}
    assert requests[0]["store"] is False
