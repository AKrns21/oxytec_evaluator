"""LangGraph workflow definition and execution."""

import asyncio
from typing import Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

from app.agents.state import GraphState
from app.agents.nodes.extractor import extractor_node
from app.agents.nodes.planner import planner_node
from app.agents.nodes.subagent import execute_subagents_parallel
from app.agents.nodes.risk_assessor import risk_assessor_node
from app.agents.nodes.writer import writer_node
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


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

    # Add nodes
    workflow.add_node("extractor", extractor_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("execute_subagents", execute_subagents_parallel)
    workflow.add_node("risk_assessor", risk_assessor_node)
    workflow.add_node("writer", writer_node)

    # Define edges (workflow sequence)
    workflow.set_entry_point("extractor")
    workflow.add_edge("extractor", "planner")
    workflow.add_edge("planner", "execute_subagents")
    workflow.add_edge("execute_subagents", "risk_assessor")
    workflow.add_edge("risk_assessor", "writer")
    workflow.add_edge("writer", END)

    # Compile with PostgreSQL checkpointing for debugging
    # This allows us to inspect the state at each step
    try:
        checkpointer = PostgresSaver.from_conn_string(settings.database_url)
        app = workflow.compile(checkpointer=checkpointer)
        logger.info("agent_graph_compiled", checkpointing=True)
    except Exception as e:
        logger.warning(
            "checkpointing_disabled",
            reason=str(e),
            message="Compiling without checkpointing"
        )
        app = workflow.compile()

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
