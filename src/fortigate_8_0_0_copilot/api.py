from collections.abc import AsyncGenerator
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import RequestResponseEndpoint

from fortigate_8_0_0_copilot.schemas import ChatRequest, ChatResponse
from fortigate_8_0_0_copilot.workflow import WorkflowState, graph
from contextlib import asynccontextmanager

from fortigate_8_0_0_copilot.config import Settings
from fortigate_8_0_0_copilot.workflow import build_graph
from fortigate_8_0_0_copilot.llm.bindings import ModelCall, build_model_call





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


# Create and configure the API application and its supporting workflow.
def create_app(model_call: ModelCall | None = None) -> FastAPI:
    """Create a FastAPI application connected to a language-model workflow.

    Accept an existing model caller when one is provided, or create one
    using the application's settings.

    Prepare the workflow when the application starts and make it available
    to API endpoints that need to process user messages.

    Return the configured FastAPI application.
    """

    # Manage the application's startup and shutdown lifecycle.
    # The decorator lets FastAPI use this function for lifecycle management.
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        """Prepare the language-model workflow before serving requests.

        Use the supplied model caller if one exists. Otherwise, load the
        application settings and create a model caller.

        Build the workflow and store it in the application so that incoming
        chat requests can reuse it.

        Keep the prepared workflow available throughout the application's
        running lifetime.
        """

        # Use the model caller provided when the application was created.
        active_model_call = model_call

        # Create a configured model caller if none was provided.
        if active_model_call is None:
            settings = Settings()
            active_model_call = build_model_call(settings)

        # Build the workflow and make it accessible to API endpoints.
        app.state.chat_graph = build_graph(active_model_call)

        # Allow the application to serve requests after startup completes.
        yield

    # Create the FastAPI application with its lifecycle manager.
    app = FastAPI(lifespan=lifespan)

    # Register an HTTP POST endpoint for processing chat requests.
    # The decorator connects requests to /chat with the chat function.
    @app.post("/chat", response_model=ChatResponse)
    async def chat(body: ChatRequest, request: Request) -> ChatResponse:
        """Process a user's chat message and return the generated answer.

        Receive the user's message from the HTTP request and pass it to
        the language-model workflow prepared during application startup.

        Wait for the workflow to finish processing the message, then
        return its answer using the application's response format.
        """

        # Run the user's message through the prepared workflow.
        result = await request.app.state.chat_graph.ainvoke(
            {"message": body.message}
        )

        # Return the workflow's answer to the client.
        return ChatResponse(answer=result["answer"])

    # Return the configured application to its caller.
    return app


# Create the application instance that the ASGI server will run.
app = create_app()
