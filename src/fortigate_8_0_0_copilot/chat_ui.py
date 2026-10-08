import logging

import chainlit as cl
import httpx
from pydantic import ValidationError

from fortigate_8_0_0_copilot.config import Settings
from fortigate_8_0_0_copilot.logging_config import configure_logging
from fortigate_8_0_0_copilot.schemas import ChatResponse, ErrorResponse

configure_logging()
logger = logging.getLogger(__name__)
settings = Settings()


def format_backend_error(response: httpx.Response) -> str:
    """Build a readable chat message from an unsuccessful backend response.

    Check that the response body matches the expected error format. For an
    HTTP 422 response, show the backend's validation message so the user knows
    why their input was rejected. For other valid error responses, show a
    general retry message instead of exposing the backend's error details.
    If the body cannot be read as an error response, log the validation problem
    and show a message that includes the HTTP status code.

    Log the failed request and append its request ID when available, so the
    user can provide it when reporting a problem. Use the ID from a valid error
    body, or fall back to the X-Request-ID header if the body is invalid.

    Args:
        response: The unsuccessful HTTP response received from the backend.

    Returns:
        Text ready to display in the chat, with a request ID when available.
    """
    request_id = response.headers.get("X-Request-ID")
    text = "The backend could not complete your request. Please try again."

    try:
        error = ErrorResponse.model_validate_json(
            response.content,
            strict=True,
        )
    except ValidationError as exc:
        text = (
            "The backend returned an unexpected error response "
            f"(HTTP {response.status_code})."
        )
        logger.error(
            "Invalid backend error response: status=%s errors=%s",
            response.status_code,
            exc.errors(include_input=False),
        )
    else:
        request_id = error.request_id

        if response.status_code == 422:
            text = error.error.message

    logger.warning(
        "Backend request failed: status=%s request_id=%s",
        response.status_code,
        request_id,
    )

    if request_id:
        text += f"\n\nRequest ID: `{request_id}`"

    return text


@cl.on_message
async def handle_message(message: cl.Message) -> None:
    """Forward a chat message to the backend and update the waiting reply.

    The @cl.on_message decorator registers this function with Chainlit, which
    calls it whenever a user sends a message. First, show a waiting message in
    the chat. Then use an asynchronous HTTP client to send the user's text as
    JSON to the backend's /chat endpoint, using the configured address and
    timeout.

    Check the HTTP status and validate the response body before displaying
    the backend's answer. Handle timeouts, connection failures, other request
    errors, and invalid response data with readable error messages and logs.
    Delegate unsuccessful HTTP responses to format_backend_error so their
    messages and request IDs are handled consistently.

    Replace the waiting message with the answer or error rather than sending
    a separate reply. This function updates the chat; it does not return the
    answer to its caller.

    Args:
        message: The incoming Chainlit message whose content is sent to the
            backend.
    """
    reply = cl.Message(content="Waiting for the backend...")
    await reply.send()

    request_id = None

    try:
        async with httpx.AsyncClient(
            base_url=settings.backend_base_url,
            timeout=settings.backend_timeout_seconds,
        ) as client:
            response = await client.post(
                "/chat",
                json={"message": message.content},
            )

        request_id = response.headers.get("X-Request-ID")
        response.raise_for_status()

        result = ChatResponse.model_validate_json(
            response.content,
            strict=True,
        )

    except httpx.TimeoutException:
        logger.warning("Backend request timed out")
        text = "The backend request timed out. Please try again."

    except httpx.ConnectError:
        logger.warning("Could not connect to the backend")
        text = "Could not reach the backend. Please check that it is running."

    except httpx.HTTPStatusError as exc:
        text = format_backend_error(exc.response)

    except httpx.RequestError:
        logger.exception("Communication with the backend failed")
        text = "Communication with the backend failed. Please try again."

    except ValidationError as exc:
        logger.error(
            "Invalid backend success response: request_id=%s errors=%s",
            request_id,
            exc.errors(include_input=False),
        )
        text = "The backend returned a response that could not be processed."

        if request_id:
            text += f"\n\nRequest ID: `{request_id}`"

    else:
        logger.info(
            "Backend reply received: request_id=%s",
            result.request_id,
        )
        text = result.answer

    reply.content = text
    await reply.update()