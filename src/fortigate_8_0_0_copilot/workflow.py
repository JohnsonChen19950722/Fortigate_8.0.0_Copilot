"""Workflow: the path a user's question takes to become the copilot's answer.

This module is named ``workflow`` because it lays out the steps the FortiGate
copilot follows for every request: take in the user's message, ask the
language model for a reply, and hand that reply back as the answer. It also
defines the record that travels through those steps, so every step sees the
same request and can add its result to it.

Right now the workflow has a single step that asks the model for a reply.
Which model is used, and how it is called, is decided by the application and
passed in when the workflow is built.
"""

# Standard-library helpers, the model-caller contract, and LangGraph tools
# for building the step-by-step workflow.
from pprint import pprint
from typing import NotRequired, TypedDict
from fortigate_8_0_0_copilot.llm.bindings import ModelCall
from langgraph.graph import END, START, StateGraph, CompiledStateGraph


# The record shared by every step: what the user asked, which request it
# belongs to, and (once ready) the copilot's answer.
class WorkflowState(TypedDict):
    """The information carried through the workflow for a single request.

    Think of it as a ticket that follows one question from start to finish.
    It begins with the user's message and a request ID so the question can be
    tracked, and the answer is filled in once the model has replied.
    """

    message: str
    request_id: str
    # The answer is missing when a request first arrives and is added later.
    answer: NotRequired[str]


# Assemble the workflow: plug in the model caller, define the steps, and
# connect them in order.
def build_graph(model_call: ModelCall) -> CompiledStateGraph:
    """Put together the copilot's workflow so it is ready to answer questions.

    The application supplies the function that talks to the language model,
    and this builds a workflow around it: a request comes in, the model is
    asked for a reply, and the reply is saved as the answer. Building the
    workflow only prepares it; no question is sent to the model until the
    application actually runs it with a request.
    """

    # The single working step: ask the model and record its reply.
    async def answer_node(state: WorkflowState) -> dict[str, str]:
        """Ask the language model to reply to the user's message.

        It sends the user's message to the model and returns only the reply
        text, which becomes the request's answer. If the model call fails,
        the problem is passed back to whoever ran the workflow instead of
        being hidden behind a made-up answer.
        """
        # Send the user's message to the model supplied by the application.
        result = await model_call(state["message"])

        # Keep only the reply text; extra details from the model are dropped.
        return {"answer": result.text}

    # Lay out the route: start -> answer step -> finish.
    builder = StateGraph(WorkflowState)

    builder.add_node("answer", answer_node)
    builder.add_edge(START, "answer")
    builder.add_edge("answer", END)

    # Turn the layout into a runnable workflow (nothing is run yet).
    return builder.compile()
