import logging
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from fortigate_8_0_0_copilot.schemas import (
    ChatRequest,
    ChatResponse,
    ErrorDetail,
    ErrorResponse,
)

app = FastAPI(debug=False)
logger = logging.getLogger(__name__)



"""This middleware assigns a request ID to each incoming HTTP request."""

@app.middleware("http")
async def add_request_id(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request.state.request_id = str(uuid4())
    return await call_next(request)



@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}





"""It accepts a JSON request, validates that JSON using ChatRequest, has access to the current HTTP Request, and returns a ChatResponse. 
"""

@app.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        422: {
            "model": ErrorResponse,
            "description": "Invalid request data",
        },
        500: {
            "model": ErrorResponse,
            "description": "Unexpected application failure",
        },
    },
)
async def chat(
    payload: ChatRequest,
    request: Request,
) -> ChatResponse:
    return ChatResponse(
        request_id=request.state.request_id,
        answer="Your message reached the backend.",
    )




"""When request validation fails, FastAPI raises RequestValidationError. Registering a handler for that exception lets you replace FastAPI’s default validation response with your chosen format.
This handler:
- Reads the first validation problem.
- Chooses an understandable message.
- Builds an ErrorResponse.
- Sends it with HTTP status 422.
"""




@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    messages = {
        "missing": "The request must include a message.",
        "string_type": "The message must be text.",
        "string_too_short": "Please enter a nonempty message.",
        "string_too_long": "Please limit your message to 4,000 characters.",
        "extra_forbidden": "Send only the message field.",
        "json_invalid": "The request body must contain valid JSON.",
    }

    first_error = exc.errors()[0]
    message = messages.get(
        first_error["type"],
        "Send a JSON object containing a message field.",
    )

    body = ErrorResponse(
        request_id=request.state.request_id,
        error=ErrorDetail(
            code="INVALID_INPUT",
            message=message,
        ),
    )

    return JSONResponse(
        status_code=422,
        content=body.model_dump(mode="json"),
    )





@app.exception_handler(Exception)
async def unexpected_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.error(
        "Unexpected request failure: request_id=%s",
        request.state.request_id,
        exc_info=exc,
    )

    body = ErrorResponse(
        request_id=request.state.request_id,
        error=ErrorDetail(
            code="INTERNAL_ERROR",
            message="Something went wrong. Please try again.",
        ),
    )

    return JSONResponse(
        status_code=500,
        content=body.model_dump(mode="json"),
    )


