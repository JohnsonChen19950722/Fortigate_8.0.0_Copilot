import asyncio
from unittest.mock import create_autospec

import pytest
from pydantic import SecretStr

from fortigate_8_0_0_copilot.config import Settings
from fortigate_8_0_0_copilot.llm import bindings
from fortigate_8_0_0_copilot.llm.adapter import ModelResponseError, ModelResult


@pytest.fixture
def model_settings() -> Settings:
    return Settings(
        llm_model="openai/test-model",
        llm_api_key=SecretStr("test-key"),
        llm_timeout_seconds=12.5,
        llm_max_output_tokens=128,
    )


@pytest.mark.parametrize("finish_reason", ["stop", "length", "content_filter", None])
def test_model_call_returns_result_unchanged(
    monkeypatch: pytest.MonkeyPatch,
    model_settings: Settings,
    finish_reason: str | None,
) -> None:
    result = ModelResult(
        text="  Reply unchanged.  ",
        requested_model="openai/test-model",
        returned_model="test-model",
        input_tokens=10,
        output_tokens=5,
        total_tokens=15,
        finish_reason=finish_reason,
    )
    generate_reply = create_autospec(bindings.generate_reply, return_value=result)
    monkeypatch.setattr(bindings, "generate_reply", generate_reply)

    call_model = bindings.build_model_call(model_settings)
    generate_reply.assert_not_called()
    actual = asyncio.run(call_model("Hello", "request-123"))

    assert actual is result
    generate_reply.assert_awaited_once_with(
        "Hello",
        timeout_seconds=12.5,
        max_output_tokens=128,
    )


def test_model_call_reads_settings_when_called(
    monkeypatch: pytest.MonkeyPatch,
    model_settings: Settings,
) -> None:
    generate_reply = create_autospec(bindings.generate_reply)
    monkeypatch.setattr(bindings, "generate_reply", generate_reply)
    call_model = bindings.build_model_call(model_settings)

    asyncio.run(call_model("First", "request-1"))
    model_settings.llm_timeout_seconds = 20.0
    model_settings.llm_max_output_tokens = 256
    asyncio.run(call_model("Second", "request-2"))

    assert generate_reply.await_count == 2
    generate_reply.assert_awaited_with(
        "Second",
        timeout_seconds=20.0,
        max_output_tokens=256,
    )


@pytest.mark.parametrize(
    "error",
    [ModelResponseError("Invalid response"), RuntimeError("Provider failure")],
)
def test_model_call_propagates_original_error(
    monkeypatch: pytest.MonkeyPatch,
    model_settings: Settings,
    error: Exception,
) -> None:
    generate_reply = create_autospec(bindings.generate_reply, side_effect=error)
    monkeypatch.setattr(bindings, "generate_reply", generate_reply)
    call_model = bindings.build_model_call(model_settings)

    with pytest.raises(type(error)) as raised:
        asyncio.run(call_model("Hello", "request-123"))

    assert raised.value is error
