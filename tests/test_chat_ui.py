import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, create_autospec

import httpx
import pytest
from pydantic import ValidationError

from fortigate_8_0_0_copilot import api, chat_ui


@pytest.fixture
def reply(monkeypatch: pytest.MonkeyPatch) -> Mock:
    reply = Mock(send=AsyncMock(), update=AsyncMock())
    monkeypatch.setattr(chat_ui.cl, "Message", Mock(return_value=reply))
    return reply


@pytest.fixture
def backend_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    client = create_autospec(httpx.AsyncClient, instance=True)
    client.__aenter__.return_value = client
    monkeypatch.setattr(chat_ui.httpx, "AsyncClient", Mock(return_value=client))
    return client


def test_message_displays_validated_answer(
    reply: Mock,
    backend_client: MagicMock,
) -> None:
    backend_client.post.return_value = httpx.Response(
        200,
        json={"request_id": "request-123", "answer": "  Reply unchanged.  "},
        request=httpx.Request("POST", "http://backend/chat"),
    )

    asyncio.run(chat_ui.handle_message(Mock(content="Hello")))

    backend_client.post.assert_awaited_once_with("/chat", json={"message": "Hello"})
    reply.send.assert_awaited_once_with()
    assert reply.content == "  Reply unchanged.  "
    reply.update.assert_awaited_once_with()
    backend_client.__aexit__.assert_awaited_once()


@pytest.mark.parametrize("message", ["  Hello  ", "x" * 4_000])
def test_message_round_trip_through_api(
    monkeypatch: pytest.MonkeyPatch,
    reply: Mock,
    message: str,
) -> None:
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app),
        base_url="http://backend",
    )
    monkeypatch.setattr(chat_ui.httpx, "AsyncClient", Mock(return_value=client))

    asyncio.run(chat_ui.handle_message(Mock(content=message)))

    reply.send.assert_awaited_once_with()
    assert reply.content == "Your message reached the backend."
    reply.update.assert_awaited_once_with()
    assert client.is_closed


@pytest.mark.parametrize("message", ["   ", "x" * 4_001])
def test_api_validation_failure_propagates_through_ui(
    monkeypatch: pytest.MonkeyPatch,
    reply: Mock,
    message: str,
) -> None:
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app),
        base_url="http://backend",
    )
    monkeypatch.setattr(chat_ui.httpx, "AsyncClient", Mock(return_value=client))

    with pytest.raises(httpx.HTTPStatusError) as raised:
        asyncio.run(chat_ui.handle_message(Mock(content=message)))

    assert raised.value.response.status_code == 422
    assert "X-Request-ID" in raised.value.response.headers
    reply.update.assert_not_awaited()
    assert client.is_closed


@pytest.mark.parametrize(
    "error_type",
    [httpx.TimeoutException, httpx.ConnectError, httpx.RequestError],
)
def test_request_failure_propagates(
    reply: Mock,
    backend_client: MagicMock,
    error_type: type[httpx.RequestError],
) -> None:
    error = error_type("Request failed")
    backend_client.post.side_effect = error

    with pytest.raises(error_type) as raised:
        asyncio.run(chat_ui.handle_message(Mock(content="Hello")))

    assert raised.value is error
    reply.update.assert_not_awaited()
    backend_client.__aexit__.assert_awaited_once()


@pytest.mark.parametrize("status_code", [422, 500])
def test_http_failure_propagates(
    reply: Mock,
    backend_client: MagicMock,
    status_code: int,
) -> None:
    response = httpx.Response(
        status_code,
        text="Backend failure",
        request=httpx.Request("POST", "http://backend/chat"),
    )
    backend_client.post.return_value = response

    with pytest.raises(httpx.HTTPStatusError) as raised:
        asyncio.run(chat_ui.handle_message(Mock(content="Hello")))

    assert raised.value.response is response
    reply.update.assert_not_awaited()


@pytest.mark.parametrize(
    "content",
    [
        "not JSON",
        '{"request_id": "request-123"}',
        '{"request_id": "request-123", "answer": 123}',
    ],
)
def test_invalid_response_propagates_validation_error(
    reply: Mock,
    backend_client: MagicMock,
    content: str,
) -> None:
    backend_client.post.return_value = httpx.Response(
        200,
        text=content,
        request=httpx.Request("POST", "http://backend/chat"),
    )

    with pytest.raises(ValidationError):
        asyncio.run(chat_ui.handle_message(Mock(content="Hello")))

    reply.update.assert_not_awaited()
