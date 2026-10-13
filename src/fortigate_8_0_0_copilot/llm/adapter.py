"""Request replies from OpenAI's GPT-6.1-sol through LiteLLM.

Send a user's message to GPT-6.1-sol, reject responses without usable
text, and return the reply with model details and token usage in a consistent
format. Keep LiteLLM response handling separate from the rest of the application.
"""

from dataclasses import dataclass

import litellm

from fortigate_8_0_0_copilot.config import settings


@dataclass(frozen=True)
class ModelResult:
    """Keep a model's reply and its metadata in one read-only record.

    Store the reply text, the requested and reported model names, token
    counts, and the reason generation stopped. Optional details can be
    left unset when unavailable. Fields cannot be reassigned after creation.
    """

    text: str
    requested_model: str
    returned_model: str | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    finish_reason: str | None


class ModelResponseError(RuntimeError):
    """Signal that a model response cannot provide a usable text reply.

    Cover an unexpected response type, missing response choices, or a first
    choice whose content is not text or contains only whitespace.
    """


async def generate_reply(
    message: str,
    *,
    timeout_seconds: float,
    max_output_tokens: int,
) -> ModelResult:
    """Ask OpenAI's GPT-6.1-sol to answer a user's message clearly and concisely.

    Use LLM_API_KEY from application settings, loaded from the root .env file
    or environment. Keep the key masked in settings and unwrap it only when
    passing it to LiteLLM to authenticate the request.

    Wait for a complete reply using the supplied timeout and output-token
    limit. Failed requests are not retried.

    Return the first choice's text unchanged, together with model details,
    available token counts, and the reason generation stopped. Missing token
    counts are left unset.

    Raise ModelResponseError if the response has an unexpected type, has no
    choices, or its first choice has no non-blank text. Errors from the model
    service are passed through to the caller.
    """

    # Give the model a consistent response style while keeping the user's
    # message separate from the application's instructions.
    messages = [
        {
            "role": "system",
            "content": "Answer clearly and concisely.",
        },
        {
            "role": "user",
            "content": message,
        },
    ]

    # Request a complete reply within the configured time and output limits.
    # Disable automatic retries so a failed request is reported to the caller.
    model = "openai/gpt-6.1-sol"
    response = await litellm.acompletion(
        model=model,
        api_key=settings.llm_api_key.get_secret_value(),
        messages=messages,
        timeout=timeout_seconds,
        max_completion_tokens=max_output_tokens,
        stream=False,
        num_retries=0,
        max_retries=0,
    )

    # Require the expected response format before reading its reply details.
    if not isinstance(response, litellm.ModelResponse):
        raise ModelResponseError("Unexpected model response type.")

    # Treat a response with no reply candidates as a failure, not an empty answer.
    if not response.choices:
        raise ModelResponseError("The model returned no choices.")

    # Use the first candidate as the answer, even if the model returned several.
    choice = response.choices[0]
    text = choice.message.content

    # Reject unusable text without trimming or otherwise changing a valid reply.
    if not isinstance(text, str) or not text.strip():
        raise ModelResponseError("The model returned no usable text.")

    # Token usage is optional; keep missing counts unset rather than assuming zero.
    usage = getattr(response, "usage", None)

    # Give callers a consistent result independent of LiteLLM's response format.
    # Keep both model names so the requested and reported models can be compared.
    return ModelResult(
        text=text,
        requested_model=model,
        returned_model=response.model,
        input_tokens=getattr(usage, "prompt_tokens", None),
        output_tokens=getattr(usage, "completion_tokens", None),
        total_tokens=getattr(usage, "total_tokens", None),
        finish_reason=choice.finish_reason,
    )