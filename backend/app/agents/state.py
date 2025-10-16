"""LangGraph state definition for the agent workflow."""

from typing import TypedDict, Annotated, Any
from operator import add


class GraphState(TypedDict):
    """
    State shared across all agents in the workflow.

    This state is passed through the entire agent graph and updated
    by each node. Uses reducers for accumulating lists.
    """

    # Input data
    session_id: str
    documents: list[dict[str, Any]]
    user_input: dict[str, Any]

    # Extracted facts from documents
    extracted_facts: dict[str, Any]

    # Planner output - defines which subagents to create
    planner_plan: dict[str, Any]  # Contains subagent definitions

    # Subagent results (accumulated with add reducer)
    # Each subagent appends its result to this list
    subagent_results: Annotated[list[dict[str, Any]], add]

    # Risk assessment output
    risk_assessment: dict[str, Any]

    # Final report
    final_report: str

    # Metadata and error tracking
    errors: Annotated[list[str], add]
    warnings: Annotated[list[str], add]
