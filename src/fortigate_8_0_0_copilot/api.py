
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint



from fortigate_8_0_0_copilot.schemas import (
    ChatRequest,
    ChatResponse,
    ErrorDetail,
    ErrorResponse,
)

from fortigate_8_0_0_copilot.workflow import WorkflowState, graph


import logging
from fortigate_8_0_0_copilot.logging_config import configure_logging
from time import perf_counter
from uuid import uuid4




app = FastAPI(debug=False)

configure_logging()
logger = logging.getLogger(__name__)
logger.info("Backend started")




@app.middleware("http")
async def add_request_context(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    """Make each HTTP request traceable in logs and in the returned response.

    The middleware registration runs this around every HTTP request. It gives
    the request a unique ID and start time that other handlers can use, then
    passes it on for processing. When a response comes back, it adds the ID
    to the X-Request-ID header and logs the status and elapsed time.
    """
    request_id = str(uuid4())

    request.state.request_id = request_id
    request.state.started_at = perf_counter()

    logger.info(
        "event=request_received request_id=%s method=%s path=%s",
        request_id,
        request.method,
        request.url.path,
    )

    response = await call_next(request)

    duration_ms = (
        perf_counter() - request.state.started_at
    ) * 1_000

    response.headers["X-Request-ID"] = request_id

    logger.info(
        "event=request_finished request_id=%s "
        "status_code=%s duration_ms=%.2f",
        request_id,
        response.status_code,
        duration_ms,
    )

    return response


@app.get("/health")
async def health() -> dict[str, str]:
    """Provide a simple way to check that the API is responding.

    Registered as GET /health, this returns {"status": "ok"} without running
    the chat workflow or checking any external services.
    """
    return {"status": "ok"}


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
    """Send a validated user message through the chat workflow.

    Registered as POST /chat, this passes the message and request ID to the
    workflow, logs when it starts and how long it takes, and returns its
    answer together with the same ID so the caller can match it to the logs.
    The route registration defines the successful response format and
    documents the error formats for invalid input and unexpected failures.
    """
    request_id = request.state.request_id

    initial_state: WorkflowState = {
        "message": payload.message,
        "request_id": request_id,
    }

    logger.info(
        "event=workflow_started request_id=%s",
        request_id,
    )

    workflow_started_at = perf_counter()

    result = await graph.ainvoke(initial_state)

    workflow_duration_ms = (
        perf_counter() - workflow_started_at
    ) * 1_000

    logger.info(
        "event=workflow_completed request_id=%s duration_ms=%.2f",
        request_id,
        workflow_duration_ms,
    )

    return ChatResponse(
        request_id=request_id,
        answer=result["answer"],
    )






@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Help callers understand why their request was rejected.

    Registered for request validation failures, this turns the first problem
    into a plain-language message, logs the rejection, and returns a 422
    response with the INVALID_INPUT code and request ID. Unrecognized
    validation problems receive general guidance about the expected input.
    """
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
    
    logger.warning(
    "event=request_rejected request_id=%s status_code=422",
    request.state.request_id,
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
    """Report an unexpected failure without exposing internal error details.

    Registered as the fallback handler for unhandled exceptions, this logs
    the error and elapsed request time for troubleshooting. It returns a
    generic 500 response with the INTERNAL_ERROR code, including the request
    ID in both the body and X-Request-ID header to help locate the failure
    in the logs.
    """
    request_id = request.state.request_id

    duration_ms = (
        perf_counter() - request.state.started_at
    ) * 1_000

    logger.error(
        "event=request_failed request_id=%s "
        "status_code=500 duration_ms=%.2f",
        request_id,
        duration_ms,
        exc_info=exc,
    )

    body = ErrorResponse(
        request_id=request_id,
        error=ErrorDetail(
            code="INTERNAL_ERROR",
            message="Something went wrong. Please try again.",
        ),
    )

    return JSONResponse(
        status_code=500,
        content=body.model_dump(mode="json"),
        headers={"X-Request-ID": request_id},
    )