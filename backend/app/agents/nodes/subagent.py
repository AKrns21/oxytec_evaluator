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

        # Define system prompt for subagents with critical risk focus
        system_prompt = "You are a critical risk evaluation specialist for Oxytec feasibility studies. Your primary responsibility is to identify and quantify project-killing risks. Prioritize realistic risk assessment (70% of analysis) over optimistic possibilities (30% of analysis). Provide specific probabilities, cost impacts, and failure scenarios based on evidence and industry benchmarks. Remember: oxytec's reputation depends on realistic project assessment to avoid costly failures."

        # Execute with configured model (gpt-nano by default)
        from app.config import settings

        if tools:
            result = await llm_service.execute_with_tools(
                prompt=prompt,
                tools=tools,
                max_iterations=5,
                system_prompt=system_prompt,
                temperature=settings.subagent_temperature,
                use_openai=True,
                openai_model=settings.subagent_model
            )
        else:
            result = await llm_service.execute_structured(
                prompt=prompt,
                response_format="text",
                system_prompt=system_prompt,
                temperature=settings.subagent_temperature,
                use_openai=True,
                openai_model=settings.subagent_model
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
    Build a comprehensive prompt for a subagent with CRITICAL RISK ASSESSMENT MANDATE.

    Args:
        objective: What the subagent should accomplish
        questions: Specific questions to answer
        data: Relevant extracted facts (JSON subset only)
        tools: Available tools

    Returns:
        Formatted prompt string with risk-focused instructions
    """

    questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

    tools_text = ""
    if tools:
        tool_descriptions = {
            "product_database": "Search the Oxytec product database for relevant equipment and specifications",
            "web_search": "Search oxytec.com and the web for technical information. Consult <www.oxytec.com/en> for Oxytec's technical focus and limitations",
        }
        tools_text = "\n\n**Available Tools:**\n" + "\n".join(
            f"- {tool}: {tool_descriptions.get(tool, '')}"
            for tool in tools if tool != "none"
        )

    prompt = f"""You are a subagent contributing to a feasibility study for Oxytec AG, a company specialized in non-thermal plasma (NTP), UV/ozone and air scrubbing technologies for industrial exhaust-air purification. The study's purpose is to determine whether it is worthwhile for Oxytec to proceed with deeper engagement with a prospective customer and whether NTP, UV/ozone, exhaust air scrubbers, or a combination of these technologies can augment the customer's current abatement setup or fully replace it.

You have been assigned a specific task by the Coordinator. Your job is to complete this task efficiently by:
- analyzing the relevant JSON subset provided to you (do not assume access to the full file)
- optionally using the web search tool to consult <www.oxytec.com/en> for Oxytec's technical focus and limitations

**CRITICAL RISK ASSESSMENT MANDATE:**

Your analysis must prioritize realistic risk evaluation over optimistic possibilities. For every technical factor you identify:
- QUANTIFY risks with specific probabilities, cost impacts, and failure timeframes
- Compare parameters to industry benchmarks and typical successful projects
- Identify potential project-killing combinations of factors
- Assess whether identified challenges could realistically cause project failure
- Provide specific evidence from similar projects or technical literature

Your output should be a concise, fact-based report that highlights:
- QUANTIFIED critical risks that could cause project failure (primary focus - 70% of analysis)
- Specific technical limitations with measurable consequences
- Realistic positive factors with supporting evidence (secondary focus - 30% of analysis)
- Clear, actionable findings with risk probabilities that the Coordinator can integrate

Your report will be returned to the lead agent to integrate into a final response. Remember: oxytec's reputation depends on realistic project assessment to avoid costly failures.

**Your Objective:**
{objective}

**Questions to Answer:**
{questions_text}

**Relevant Technical Data (JSON subset only):**
```json
{data}
```
{tools_text}

Provide your analysis with CRITICAL RISK FOCUS, addressing all questions with quantified risks and probabilities. Focus 70% on risks and limitations, 30% on positive factors.
"""

    return prompt
