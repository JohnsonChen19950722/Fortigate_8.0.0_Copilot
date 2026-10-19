"""schemas: the shapes of the messages sent to and from the chat API.

This module defines what a chat message must look like when it arrives at the
`/chat` endpoint, and what the reply sent back looks like. The API uses these
to reject bad input before it reaches the copilot workflow, and the Chainlit
chat UI uses them to check the replies it gets from the API.
"""

from pydantic import BaseModel, ConfigDict, Field


# --- Incoming chat message ---------------------------------------------------
class ChatRequest(BaseModel):
    """A question a user sends to the FortiGate copilot.

    Only the `message` field is accepted. Anything extra is rejected, and spaces
    at the start or end of the text are trimmed. A message must be real text
    between 1 and 4,000 characters long, so blank or oversized questions never
    reach the language model.
    """

    # Reject unknown fields and trim surrounding spaces from all text fields
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    # The user's question: must be a real string, 1 to 4,000 characters
    message: str = Field(
        strict=True,
        min_length=1,
        max_length=4_000,
        examples=["Hello"],
    )


# --- Outgoing chat reply -----------------------------------------------------
class ChatResponse(BaseModel):
    """The copilot's reply to a chat message.

    Carries the answer text with the ID of the request it belongs to. The same
    ID is also returned in the `X-Request-ID` response header, so a reply can be
    traced back to its request in the API's records.
    """

    # Unique ID the API gave this request
    request_id: str
    # The copilot's answer to the user's question
    answer: str
