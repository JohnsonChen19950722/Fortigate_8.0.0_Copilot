"""Connect application request limits to a reusable language-model call."""

from collections.abc import Awaitable, Callable

from fortigate_8_0_0_copilot.config import Settings
from fortigate_8_0_0_copilot.llm.adapter import ModelResult, generate_reply

# Callers supply a message and request ID without needing provider settings.
ModelCall = Callable[[str, str], Awaitable[ModelResult]]


def build_model_call(settings: Settings) -> ModelCall:
    """Create a model caller that uses the supplied request limits.

    The adapter manages the model and credentials.
    Settings are read when a request is made; no model request is sent here.
    """

    async def call_model(
        message: str,
        request_id: str,
    ) -> ModelResult:
        """Return the adapter's result unchanged.

        Accept the request ID for compatibility with the ModelCall interface.
        """
        return await generate_reply(
            message,
            timeout_seconds=settings.llm_timeout_seconds,
            max_output_tokens=settings.llm_max_output_tokens,
        )

    return call_model