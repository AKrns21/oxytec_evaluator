"""SUBAGENT execution - dynamic parallel agent execution."""

import asyncio
from typing import Any
from app.agents.state import GraphState
from app.services.llm_service import LLMService
from app.agents.tools import get_tools_for_subagent, ToolExecutor
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def execute_subagents_parallel(state: GraphState) -> dict[str, Any]:
    """
    Execute multiple subagents in parallel based on planner's plan.

    This is the core innovation - dynamically created agents executing in parallel.
    Each subagent gets:
    - Its own objective and questions
    - Relevant subset of extracted facts
    - Access to specific tools

    Args:
        state: Current graph state with planner_plan

    Returns:
        Updated state with subagent_results accumulated
    """

    session_id = state["session_id"]
    plan = state["planner_plan"]
    subagent_definitions = plan.get("subagents", [])

    if not subagent_definitions:
        logger.warning("no_subagents_to_execute", session_id=session_id)
        return {"subagent_results": []}

    logger.info(
        "subagents_execution_started",
        session_id=session_id,
        num_subagents=len(subagent_definitions)
    )

    # Create tasks for parallel execution
    tasks = []
    for idx, subagent_def in enumerate(subagent_definitions):
        task = execute_single_subagent(
            subagent_def=subagent_def,
            state=state,
            instance_name=f"subagent_{idx}_{subagent_def['name']}"
        )
        tasks.append(task)

    # Execute all subagents in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect results and errors
    successful_results = []
    errors = []

    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            error_msg = f"Subagent {subagent_definitions[idx]['name']} failed: {str(result)}"
            errors.append(error_msg)
            logger.error(
                "subagent_failed",
                session_id=session_id,
                agent_name=subagent_definitions[idx]['name'],
                error=str(result)
            )
        else:
            successful_results.append(result)
            logger.info(
                "subagent_completed",
                session_id=session_id,
                agent_name=result["agent_name"]
            )

    logger.info(
        "subagents_execution_completed",
        session_id=session_id,
        successful=len(successful_results),
        failed=len(errors)
    )

    return {
        "subagent_results": successful_results,
        "errors": errors
    }


async def execute_single_subagent(
    subagent_def: dict[str, Any],
    state: GraphState,
    instance_name: str
) -> dict[str, Any]:
    """
    Execute a single subagent with its specific instructions.

    Args:
        subagent_def: Subagent definition from planner
        state: Current graph state
        instance_name: Unique instance identifier

    Returns:
        Subagent result dictionary
    """

    agent_name = subagent_def["name"]
    logger.info("subagent_started", agent_name=agent_name, instance=instance_name)

    try:
        llm_service = LLMService()

        # Extract relevant data for this subagent
        relevant_data = extract_relevant_data(
            state["extracted_facts"],
            subagent_def.get("input_fields", [])
        )

        # Build subagent prompt
        prompt = build_subagent_prompt(
            objective=subagent_def["objective"],
            questions=subagent_def.get("questions", []),
            data=relevant_data,
            tools=subagent_def.get("tools", [])
        )

        # Get tools for this subagent
        tools = get_tools_for_subagent(subagent_def.get("tools", []))

        # Execute with tools
        if tools:
            result = await llm_service.execute_with_tools(
                prompt=prompt,
                tools=tools,
                max_iterations=5
            )
        else:
            result = await llm_service.execute_structured(
                prompt=prompt,
                response_format="text"
            )

        return {
            "agent_name": agent_name,
            "instance": instance_name,
            "objective": subagent_def["objective"],
            "result": result,
            "priority": subagent_def.get("priority", "medium")
        }

    except Exception as e:
        logger.error(
            "subagent_execution_error",
            agent_name=agent_name,
            error=str(e)
        )
        raise


def extract_relevant_data(
    extracted_facts: dict[str, Any],
    input_fields: list[str]
) -> dict[str, Any]:
    """
    Extract only the relevant fields needed by a subagent.

    Args:
        extracted_facts: All extracted facts
        input_fields: List of field names needed

    Returns:
        Filtered dictionary with only requested fields
    """

    if not input_fields:
        return extracted_facts

    relevant = {}
    for field in input_fields:
        if field in extracted_facts:
            relevant[field] = extracted_facts[field]

    return relevant


def build_subagent_prompt(
    objective: str,
    questions: list[str],
    data: dict[str, Any],
    tools: list[str]
) -> str:
    """
    Build a comprehensive prompt for a subagent.

    Args:
        objective: What the subagent should accomplish
        questions: Specific questions to answer
        data: Relevant extracted facts
        tools: Available tools

    Returns:
        Formatted prompt string
    """

    questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

    tools_text = ""
    if tools:
        tool_descriptions = {
            "product_database": "Search the Oxytec product database for relevant equipment and specifications",
            "web_search": "Search oxytec.com and the web for technical information",
        }
        tools_text = "\n**Available Tools:**\n" + "\n".join(
            f"- {tool}: {tool_descriptions.get(tool, '')}"
            for tool in tools if tool != "none"
        )

    prompt = f"""You are a specialized technical analyst working on an Oxytec feasibility study.

**Your Objective:**
{objective}

**Questions to Answer:**
{questions_text}

**Relevant Technical Data:**
```json
{data}
```
{tools_text}

Provide a comprehensive analysis addressing all questions. Be specific, technical, and cite sources when using tools.
Format your response clearly with sections for each question.
"""

    return prompt
