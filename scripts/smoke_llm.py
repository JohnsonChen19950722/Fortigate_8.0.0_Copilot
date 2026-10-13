import asyncio

from fortigate_8_0_0_copilot.config import Settings
from fortigate_8_0_0_copilot.llm.adapter import generate_reply


async def main() -> None:
    settings = Settings()

    print("Sending one model request...")

    result = await generate_reply(
        "Explain what an API is in one sentence.",
        timeout_seconds=settings.llm_timeout_seconds,
        max_output_tokens=settings.llm_max_output_tokens,
    )

    print("Requested model:", result.requested_model)
    print("Returned model:", result.returned_model)
    print("Finish reason:", result.finish_reason)
    print("Input tokens:", result.input_tokens)
    print("Output tokens:", result.output_tokens)
    print("Total tokens:", result.total_tokens)

    # For this simple smoke test, require a normal stopping condition.
    if result.finish_reason != "stop":
        raise RuntimeError(
            "The smoke test did not finish normally: "
            f"{result.finish_reason!r}"
        )

    print("Reply:", result.text)


if __name__ == "__main__":
    asyncio.run(main())