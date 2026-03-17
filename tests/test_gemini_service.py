import asyncio
from types import SimpleNamespace

from app.core.settings import Settings
from app.models.chat import ChatMessage
from app.services import gemini_service as gemini_service_module
from app.services.gemini_service import GeminiService


class _FakeModels:
    def __init__(self, sink: dict):
        self._sink = sink

    def generate_content(self, **kwargs):
        self._sink["kwargs"] = kwargs
        return SimpleNamespace(
            text="model-answer",
            usage_metadata=SimpleNamespace(total_token_count=123),
        )


class _FakeClient:
    def __init__(self, sink: dict):
        self.models = _FakeModels(sink)


def test_generate_chat_response_passes_default_system_instruction(monkeypatch):
    sink: dict = {}

    def _fake_client_factory(*args, **kwargs):
        return _FakeClient(sink)

    monkeypatch.setattr(gemini_service_module.genai, "Client", _fake_client_factory)

    service = GeminiService(
        settings=Settings(
            gemini_api_key="test-key",
            gemini_model="test-model",
        )
    )

    text, generation_time, used_tokens = asyncio.run(
        service.generate_chat_response(
            message="hello",
            history=[ChatMessage(role="user", parts=["previous message"])],
        )
    )

    assert text == "model-answer"
    assert generation_time >= 0
    assert used_tokens == 123

    config = sink["kwargs"]["config"]
    assert (
        "\n\n----------------\n" in config.system_instruction
        or "\\n\\n----------------\\n" in config.system_instruction
    )


def test_generate_chat_response_uses_custom_system_instruction(monkeypatch):
    sink: dict = {}

    def _fake_client_factory(*args, **kwargs):
        return _FakeClient(sink)

    monkeypatch.setattr(gemini_service_module.genai, "Client", _fake_client_factory)

    service = GeminiService(
        settings=Settings(
            gemini_api_key="test-key",
            gemini_model="test-model",
            GEMINI_CHAT_SYSTEM_PROMPT="custom-system-prompt",
        )
    )

    asyncio.run(
        service.generate_chat_response(
            message="hello",
            history=[],
        )
    )

    config = sink["kwargs"]["config"]
    assert config.system_instruction == "custom-system-prompt"
