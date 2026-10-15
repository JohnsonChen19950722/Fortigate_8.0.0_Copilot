from uuid import uuid4

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import RequestResponseEndpoint

from fortigate_8_0_0_copilot.schemas import ChatRequest, ChatResponse
from fortigate_8_0_0_copilot.workflow import WorkflowState, graph

app = FastAPI(debug=False)


@app.middleware("http")
async def add_request_context(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    """Assign a request ID and include it in the returned response header."""
    request_id = str(uuid4())
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    return response


@app.get("/health")
async def health() -> dict[str, str]:
    """Provide a simple way to check that the API is responding.

    Registered as GET /health, this returns {"status": "ok"} without running
    the chat workflow or checking any external services.
    """
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
) -> ChatResponse:
    """Send a validated user message through the chat workflow.

    Pass the message and request ID to the workflow and return its answer
    together with the same ID.
    """
    request_id = request.state.request_id

    initial_state: WorkflowState = {
        "message": payload.message,
        "request_id": request_id,
    }

    result = await graph.ainvoke(initial_state)

    return ChatResponse(
        request_id=request_id,
        answer=result["answer"],
    )
