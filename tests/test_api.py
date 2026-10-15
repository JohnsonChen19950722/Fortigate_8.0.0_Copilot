from unittest.mock import create_autospec
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from fortigate_8_0_0_copilot import api


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert UUID(response.headers["X-Request-ID"]).version == 4


@pytest.mark.parametrize("message", ["Hello", "x" * 4_000])
def test_chat_preserves_response_contract(client: TestClient, message: str) -> None:
    response = client.post("/chat", json={"message": message})

    assert response.status_code == 200
    request_id = response.headers["X-Request-ID"]
    assert UUID(request_id).version == 4
    assert response.json() == {
        "request_id": request_id,
        "answer": "Your message reached the backend.",
    }


def test_chat_passes_validated_message_and_request_id_to_workflow(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invoke = create_autospec(api.graph.ainvoke, return_value={"answer": "Reply"})
    monkeypatch.setattr(api.graph, "ainvoke", invoke)

    response = client.post("/chat", json={"message": "  Hello  "})

    assert response.status_code == 200
    request_id = response.headers["X-Request-ID"]
    invoke.assert_awaited_once_with({"message": "Hello", "request_id": request_id})
    assert response.json() == {"request_id": request_id, "answer": "Reply"}


@pytest.mark.parametrize(
    ("payload", "error_type"),
    [
        ({}, "missing"),
        ({"message": 123}, "string_type"),
        ({"message": ""}, "string_too_short"),
        ({"message": "   "}, "string_too_short"),
        ({"message": "x" * 4_001}, "string_too_long"),
        ({"message": "Hello", "extra": True}, "extra_forbidden"),
    ],
)
def test_invalid_input_uses_framework_validation_response(
    client: TestClient,
    payload: dict[str, object],
    error_type: str,
) -> None:
    response = client.post("/chat", json=payload)

    assert response.status_code == 422
    assert set(response.json()) == {"detail"}
    assert response.json()["detail"][0]["type"] == error_type
    assert UUID(response.headers["X-Request-ID"]).version == 4


def test_invalid_json_uses_framework_validation_response(client: TestClient) -> None:
    response = client.post(
        "/chat",
        content="{",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "json_invalid"


def test_workflow_exception_propagates(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("Workflow failure")
    invoke = create_autospec(api.graph.ainvoke, side_effect=error)
    monkeypatch.setattr(api.graph, "ainvoke", invoke)

    with pytest.raises(RuntimeError) as raised:
        client.post("/chat", json={"message": "Hello"})

    assert raised.value is error


def test_workflow_failure_uses_framework_server_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invoke = create_autospec(
        api.graph.ainvoke,
        side_effect=RuntimeError("Workflow failure"),
    )
    monkeypatch.setattr(api.graph, "ainvoke", invoke)

    with TestClient(api.app, raise_server_exceptions=False) as client:
        response = client.post("/chat", json={"message": "Hello"})

    assert response.status_code == 500
    assert response.text == "Internal Server Error"
    assert "X-Request-ID" not in response.headers


def test_openapi_uses_framework_error_schema(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    responses = schema["paths"]["/chat"]["post"]["responses"]

    assert responses["422"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/HTTPValidationError",
    }
    assert "500" not in responses
    assert "ErrorDetail" not in schema["components"]["schemas"]
    assert "ErrorResponse" not in schema["components"]["schemas"]
