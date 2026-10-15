import chainlit as cl
import httpx

from fortigate_8_0_0_copilot.config import Settings
from fortigate_8_0_0_copilot.schemas import ChatResponse

settings = Settings()


@cl.on_message
async def handle_message(message: cl.Message) -> None:
    """Forward a chat message to the backend and update the waiting reply.

    The @cl.on_message decorator registers this function with Chainlit, which
    calls it whenever a user sends a message. First, show a waiting message in
    the chat. Then use an asynchronous HTTP client to send the user's text as
    JSON to the backend's /chat endpoint, using the configured address and
    timeout.

    Check the HTTP status and validate the response body before replacing
    the waiting message with the answer. Failures propagate to Chainlit.

    Args:
        message: The incoming Chainlit message whose content is sent to the
            backend.
    """
    reply = cl.Message(content="Waiting for the backend...")
    await reply.send()

    async with httpx.AsyncClient(
        base_url=settings.backend_base_url,
        timeout=settings.backend_timeout_seconds,
    ) as client:
        response = await client.post(
            "/chat",
            json={"message": message.content},
        )

    response.raise_for_status()
    result = ChatResponse.model_validate_json(
        response.content,
        strict=True,
    )

    reply.content = result.answer
    await reply.update()
