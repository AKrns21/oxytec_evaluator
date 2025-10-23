"""LangGraph workflow definition and execution."""

import asyncio
import os
import json
from typing import Any
from langgraph.graph import StateGraph, END
try:
    from langgraph.checkpoint.postgres import PostgresSaver
except ImportError:
    from langgraph_checkpoint.postgres import PostgresSaver

from app.agents.state import GraphState
from app.agents.nodes.extractor import extractor_node
from app.agents.nodes.planner import planner_node
from app.agents.nodes.subagent import execute_subagents_parallel
from app.agents.nodes.risk_assessor import risk_assessor_node
from app.agents.nodes.writer import writer_node
from app.agents.timing import track_agent_timing
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def sanitize_unicode_for_postgres(obj: Any) -> Any:
    """
    Recursively sanitize Unicode strings to remove characters that PostgreSQL cannot store.

    PostgreSQL JSONB cannot store:
    - Null bytes (\u0000)
    - Invalid Unicode escape sequences

    Args:
        obj: Any Python object (dict, list, str, etc.)

    Returns:
        Sanitized object with PostgreSQL-safe strings
    """
    if isinstance(obj, str):
        # Remove null bytes and other problematic characters
        return obj.replace('\x00', '').replace('\u0000', '')
    elif isinstance(obj, dict):
        return {k: sanitize_unicode_for_postgres(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_unicode_for_postgres(item) for item in obj]
    else:
        return obj

# Configure LangSmith tracing for LangGraph if enabled
if settings.langchain_tracing_v2 and settings.langchain_api_key:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    if settings.langchain_endpoint:
        os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint
    logger.info("langsmith_graph_tracing_enabled",
                project=settings.langchain_project,
                endpoint=settings.langchain_endpoint or "default")


def create_agent_graph():
    """
    Creates the dynamic agent graph with checkpointing.

    The graph follows this flow:
    1. EXTRACTOR: Extract structured facts from documents
    2. PLANNER: Decide which subagents to create and what they should do
    3. SUBAGENTS (parallel): Execute multiple subagents in parallel
    4. RISK ASSESSOR: Analyze technical and commercial risks
    5. WRITER: Generate final feasibility report

    Returns:
        Compiled LangGraph application
    """

    # Initialize graph with state
    workflow = StateGraph(GraphState)

    # Add nodes with timing tracking
    workflow.add_node("extractor", track_agent_timing("extractor")(extractor_node))
    workflow.add_node("planner", track_agent_timing("planner")(planner_node))
    workflow.add_node("subagent", track_agent_timing("subagent")(execute_subagents_parallel))
    workflow.add_node("risk_assessor", track_agent_timing("risk_assessor")(risk_assessor_node))
    workflow.add_node("writer", track_agent_timing("writer")(writer_node))

    # Define edges (workflow sequence)
    workflow.set_entry_point("extractor")
    workflow.add_edge("extractor", "planner")
    workflow.add_edge("planner", "subagent")
    workflow.add_edge("subagent", "risk_assessor")
    workflow.add_edge("risk_assessor", "writer")
    workflow.add_edge("writer", END)

    # Compile without checkpointing for now
    # PostgreSQL checkpointing requires async context manager setup
    # which is complex in this workflow. Disabling for stability.
    app = workflow.compile()
    logger.info("agent_graph_compiled", checkpointing=False)

    return app


async def run_agent_graph(
    session_id: str,
    documents: list[dict[str, Any]],
    user_input: dict[str, Any]
) -> dict[str, Any]:
    """
    Execute the agent graph for a session.

    Args:
        session_id: Unique session identifier
        documents: List of document metadata and content
        user_input: User-provided metadata and requirements

    Returns:
        Final graph state with report and metadata
    """

    logger.info(
        "agent_graph_execution_started",
        session_id=session_id,
        num_documents=len(documents)
    )

    # Create graph
    graph = create_agent_graph()

    # Initial state
    initial_state: GraphState = {
        "session_id": session_id,
        "documents": documents,
        "user_input": user_input,
        "extracted_facts": {},
        "planner_plan": {},
        "subagent_results": [],
        "risk_assessment": {},
        "final_report": "",
        "errors": [],
        "warnings": [],
    }

    try:
        # Execute graph
        config = {"configurable": {"thread_id": session_id}}
        result = await graph.ainvoke(initial_state, config=config)

        # Sanitize Unicode characters that PostgreSQL cannot store
        result = sanitize_unicode_for_postgres(result)

        logger.info(
            "agent_graph_execution_completed",
            session_id=session_id,
            num_errors=len(result.get("errors", [])),
            num_warnings=len(result.get("warnings", []))
        )

        return result

    except Exception as e:
        logger.error(
            "agent_graph_execution_failed",
            session_id=session_id,
            error=str(e)
        )
        raise
