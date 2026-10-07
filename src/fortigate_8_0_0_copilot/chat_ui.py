import chainlit as cl


@cl.on_message
async def handle_message(message: cl.Message) -> None:
    """Let the user know their message reached the chat interface.

    The on_message decorator registers this as the handler Chainlit calls
    whenever a user sends a message. It replies with a fixed confirmation;
    it does not yet process the message or send it to the backend.
    """
    await cl.Message(
        content="The chat interface received your message.",
    ).send()