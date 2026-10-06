from pprint import pprint
from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph


class WorkflowState(TypedDict):
    message: str
    request_id: str
    answer: NotRequired[str]


def fixed_reply(state: WorkflowState) -> dict[str, str]:
    """Return the fixed answer as an update to the workflow state."""
    return {"answer": "Your message reached the backend."}


builder = StateGraph(WorkflowState)

builder.add_node("fixed_reply", fixed_reply)
builder.add_edge(START, "fixed_reply")
builder.add_edge("fixed_reply", END)

graph = builder.compile()


if __name__ == "__main__":
    initial_state: WorkflowState = {
        "message": "Hello",
        "request_id": "demo-request-001",
    }

    result = graph.invoke(initial_state)

    pprint(result)
