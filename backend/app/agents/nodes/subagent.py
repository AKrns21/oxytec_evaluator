"""SUBAGENT execution - dynamic parallel agent execution."""

import asyncio
import traceback
import json
from typing import Any
from app.agents.state import GraphState
from app.services.llm_service import LLMService
from app.agents.tools import get_tools_for_subagent, ToolExecutor
from app.utils.logger import get_logger
from app.agents.prompts import UNIT_FORMATTING_INSTRUCTIONS, MITIGATION_STRATEGY_EXAMPLES
from app.agents.prompts.versions import get_prompt_version
from app.config import settings
from app.models.database import AgentOutput
from app.db.session import AsyncSessionLocal

logger = get_logger(__name__)


async def execute_subagents_parallel(state: GraphState) -> dict[str, Any]:
    """
    Execute multiple subagents in parallel based on planner's plan.

    This is the core innovation - dynamically created agents executing in parallel.
    Each subagent gets:
    - Its own objective and questions
    - Relevant subset of extracted facts
    - Access to specific tools

    Uses a semaphore to limit concurrent execution to prevent resource exhaustion.

    Args:
        state: Current graph state with planner_plan

    Returns:
        Updated state with subagent_results accumulated
    """

    session_id = state["session_id"]
    plan = state["planner_plan"]
    subagent_definitions = plan.get("subagents", [])

    if not subagent_definitions:
        logger.warning(
            "no_subagents_to_execute",
            session_id=session_id,
            planner_plan_keys=list(plan.keys()) if isinstance(plan, dict) else "not_a_dict",
            planner_plan_type=type(plan).__name__
        )
        return {"subagent_results": []}

    logger.info(
        "subagents_execution_started",
        session_id=session_id,
        num_subagents=len(subagent_definitions)
    )

    # Validate subagent definitions structure
    valid_definitions = []
    for idx, subagent_def in enumerate(subagent_definitions):
        if not isinstance(subagent_def, dict):
            logger.error(
                "invalid_subagent_definition_not_dict",
                session_id=session_id,
                index=idx,
                type=type(subagent_def).__name__
            )
            continue

        if "task" not in subagent_def or "relevant_content" not in subagent_def:
            logger.error(
                "invalid_subagent_definition_missing_fields",
                session_id=session_id,
                index=idx,
                has_task="task" in subagent_def,
                has_relevant_content="relevant_content" in subagent_def,
                available_keys=list(subagent_def.keys())
            )
            continue

        valid_definitions.append(subagent_def)

    if not valid_definitions:
        logger.error(
            "no_valid_subagent_definitions",
            session_id=session_id,
            total_definitions=len(subagent_definitions)
        )
        return {
            "subagent_results": [],
            "errors": [f"All {len(subagent_definitions)} subagent definitions were invalid"]
        }

    if len(valid_definitions) < len(subagent_definitions):
        logger.warning(
            "some_subagent_definitions_invalid",
            session_id=session_id,
            valid=len(valid_definitions),
            invalid=len(subagent_definitions) - len(valid_definitions)
        )

    subagent_definitions = valid_definitions

    # Create semaphore to limit concurrent subagent execution
    # This prevents database connection pool exhaustion and API rate limit issues
    MAX_PARALLEL_SUBAGENTS = 5
    semaphore = asyncio.Semaphore(MAX_PARALLEL_SUBAGENTS)

    # Create tasks for parallel execution with semaphore
    async def limited_execute_subagent(subagent_def, state, instance_name):
        """Execute single subagent with semaphore control."""
        async with semaphore:
            return await execute_single_subagent(subagent_def, state, instance_name)

    tasks = []
    for idx, subagent_def in enumerate(subagent_definitions):
        # Extract name from task description for instance naming
        task_desc = subagent_def.get("task", "")
        agent_name = extract_agent_name(task_desc) or f"agent_{idx}"

        task = limited_execute_subagent(
            subagent_def=subagent_def,
            state=state,
            instance_name=f"subagent_{idx}_{agent_name}"
        )
        tasks.append(task)

    # Execute all subagents in parallel with semaphore limiting
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect results and errors
    successful_results = []
    errors = []

    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            # Extract agent name from subagent definition
            task_desc = subagent_definitions[idx].get("task", "")
            agent_name = extract_agent_name(task_desc) or f"agent_{idx}"

            error_msg = f"Subagent {agent_name} failed: {str(result)}"
            errors.append(error_msg)
            logger.error(
                "subagent_failed",
                session_id=session_id,
                agent_name=agent_name,
                error=str(result)
            )
        else:
            successful_results.append(result)
            logger.info(
                "subagent_completed",
                session_id=session_id,
                agent_name=result.get("agent_name", "unknown")
            )

    logger.info(
        "subagents_execution_completed",
        session_id=session_id,
        successful=len(successful_results),
        failed=len(errors)
    )

    # Save subagent execution summary with prompt version to database
    try:
        async with AsyncSessionLocal() as db:
            agent_output = AgentOutput(
                session_id=session_id,
                agent_type="subagent",
                output_type="results",
                content={
                    "subagent_results": successful_results,
                    "successful": len(successful_results),
                    "failed": len(errors),
                    "note": "Rendered prompts are stored per subagent execution in individual subagent result objects"
                },
                prompt_version=settings.subagent_prompt_version
            )
            db.add(agent_output)
            await db.commit()
            logger.info("subagent_output_saved", session_id=session_id, prompt_version=settings.subagent_prompt_version)
    except Exception as db_error:
        logger.warning("subagent_output_save_failed", session_id=session_id, error=str(db_error))

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

    New Flowise-style structure:
    - subagent_def has "task" (comprehensive description) and "relevant_content" (JSON string)
    - Task description includes objective, questions, method hints, deliverables, dependencies, and tools

    Args:
        subagent_def: Subagent definition from planner (task + relevant_content)
        state: Current graph state
        instance_name: Unique instance identifier

    Returns:
        Subagent result dictionary
    """

    # Extract task description and relevant content
    task_description = subagent_def.get("task", "")
    relevant_content = subagent_def.get("relevant_content", "{}")

    # Extract agent name from task description (first line typically has "Subagent: Name")
    agent_name = extract_agent_name(task_description) or instance_name

    logger.info("subagent_started", agent_name=agent_name, instance=instance_name)

    try:
        logger.debug("step_1_init_llm_service", agent_name=agent_name)
        llm_service = LLMService()

        # Extract tool names - try JSON field first, fall back to text parsing
        logger.debug("step_2_extract_tools", agent_name=agent_name)
        tool_names = subagent_def.get("tools", [])
        if not tool_names:
            # Fallback: Try parsing from task description
            tool_names = extract_tools_from_task(task_description)
            logger.warning("tools_not_in_json_using_fallback",
                          agent_name=agent_name,
                          parsed_tools=tool_names,
                          message="Tools field not in JSON, using text parsing fallback")
        else:
            logger.info("tools_from_json_field",
                       agent_name=agent_name,
                       tool_names=tool_names)

        # CRITICAL LOGGING: Verify tool extraction for debugging
        logger.info("tools_extracted_final",
                   agent_name=agent_name,
                   tool_names=tool_names,
                   has_tools=len(tool_names) > 0,
                   task_preview=task_description[:300])  # Log task start to verify tools

        # Build subagent prompt (now much simpler - task description has everything)
        logger.debug("step_3_build_prompt", agent_name=agent_name)
        prompt = build_subagent_prompt_v2(
            task_description=task_description,
            relevant_content=relevant_content
        )

        # Get tool definitions for this subagent
        logger.debug("step_4_get_tools", agent_name=agent_name, tool_names=tool_names)
        tools = get_tools_for_subagent(tool_names)

        # CRITICAL VALIDATION: Ensure tools were retrieved successfully
        logger.info("tools_retrieved",
                   agent_name=agent_name,
                   requested_tools=tool_names,
                   retrieved_tools=[t.get("name") for t in tools] if tools else [],
                   num_tools=len(tools) if tools else 0)

        # ALERT: Technology screening without RAG is a critical failure
        if "technology" in agent_name.lower() and "oxytec_knowledge_search" not in [t.get("name") for t in tools if t]:
            logger.error("technology_screening_missing_rag_tool",
                        agent_name=agent_name,
                        available_tools=[t.get("name") for t in tools] if tools else [],
                        message="Technology screening subagent created without oxytec_knowledge_search tool!")

        # Load versioned system prompt for subagents
        prompt_data = get_prompt_version("subagent", settings.subagent_prompt_version)
        system_prompt = prompt_data["SYSTEM_PROMPT"]

        # Execute with configured model
        # CRITICAL: Tools are in Claude/Anthropic format, so ALWAYS use Claude when tools are present
        # Use OpenAI only for tool-free analysis tasks (cost optimization)

        if tools:
            # ALWAYS use Claude for tool calling - tools are in Claude/Anthropic format
            # OpenAI tool calling uses different format and is not compatible
            logger.info("subagent_using_claude_for_tools",
                       agent_name=agent_name,
                       num_tools=len(tools),
                       tool_names=[t.get("name") for t in tools])

            result = await llm_service.execute_with_tools(
                prompt=prompt,
                tools=tools,
                max_iterations=5,
                system_prompt=system_prompt,
                temperature=settings.subagent_temperature,
                model="claude-3-haiku-20240307"  # Fast, cost-effective for tool calling
            )
        else:
            # Use OpenAI for text-only analysis (no tools needed)
            logger.info("subagent_using_openai_text_only",
                       agent_name=agent_name,
                       model=settings.subagent_model)

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
            "task": task_description[:200] + "..." if len(task_description) > 200 else task_description,  # Truncated for logging
            "result": result
        }

    except Exception as e:
        logger.error(
            "subagent_execution_error",
            agent_name=agent_name,
            error=str(e),
            traceback=traceback.format_exc()
        )
        raise


def extract_agent_name(task_description: str) -> str:
    """
    Extract agent name from task description.
    Expected format: "Subagent: Agent Name" on first line.

    Args:
        task_description: Full task description

    Returns:
        Agent name or empty string
    """
    lines = task_description.split('\n')
    if lines and lines[0].startswith("Subagent:"):
        # Extract name after "Subagent: "
        name = lines[0].replace("Subagent:", "").strip()
        # Convert to snake_case identifier
        return name.lower().replace(" ", "_").replace("&", "and")
    return ""


def extract_tools_from_task(task_description: str) -> list[str]:
    """
    Extract tool names from task description.
    Looks for "Tools needed: tool_name" or "Tools: tool_name" line.

    Supports variations:
    - "Tools needed: oxytec_knowledge_search"
    - "Tools: oxytec_knowledge_search, web_search"
    - "Tools needed: none"

    Args:
        task_description: Full task description

    Returns:
        List of tool names (e.g., ["oxytec_knowledge_search", "product_database", "web_search"])
        Empty list if "none" or no tools line found
    """
    lines = task_description.split('\n')
    for line in lines:
        line_lower = line.strip().lower()

        # Support multiple variations of the tools line
        if line_lower.startswith("tools needed:") or line_lower.startswith("tools:"):
            # Extract tool text after the colon
            tool_text = line.split(":", 1)[1].strip().lower()

            # Build list of tools (can have multiple comma-separated)
            tools = []

            # Check for each known tool (case-insensitive, flexible matching)
            if "oxytec_knowledge_search" in tool_text or "search_oxytec_knowledge" in tool_text:
                tools.append("oxytec_knowledge_search")
            if "product_database" in tool_text or "search_product_database" in tool_text:
                tools.append("product_database")
            if "web_search" in tool_text or "search_web" in tool_text:
                tools.append("web_search")

            # If we found any tools, log and return them
            if tools:
                logger.info("tools_parsed_from_task",
                           raw_line=line.strip(),
                           extracted_tools=tools)
                return tools

            # If "none" mentioned or empty, log and return empty list
            if "none" in tool_text or not tool_text:
                logger.info("no_tools_specified", raw_line=line.strip())
                return []

            # If we found the line but couldn't parse tools, warn
            logger.warning("tools_line_found_but_unparseable",
                          raw_line=line.strip(),
                          tool_text=tool_text)
            return []

    # No tools line found - log warning
    logger.warning("no_tools_line_in_task",
                  task_preview=task_description[:200])
    return []  # No tools by default


def build_subagent_prompt_v2(
    task_description: str,
    relevant_content: str
) -> str:
    """
    Build a prompt for a subagent using Flowise-style structure with versioned prompts.

    Task description already contains:
    - Objective
    - Questions to answer
    - Method hints / quality criteria
    - Deliverables
    - Dependencies
    - Tools needed

    Args:
        task_description: Comprehensive task description from planner
        relevant_content: JSON string with relevant subset of extracted facts

    Returns:
        Formatted prompt string
    """

    # Load versioned prompt template
    prompt_data = get_prompt_version("subagent", settings.subagent_prompt_version)
    prompt_template = prompt_data["PROMPT_TEMPLATE"]

    # Format with runtime data
    prompt = prompt_template.format(
        task_description=task_description,
        relevant_content=relevant_content
    )

    return prompt


# Legacy functions kept for backward compatibility (not used in new flow)

def extract_relevant_data(
    extracted_facts: dict[str, Any],
    input_fields: list[str]
) -> dict[str, Any]:
    """
    Extract only the relevant fields needed by a subagent.
    NOTE: This is legacy - new flow uses relevant_content string directly.

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
    Build a comprehensive prompt for a subagent with balanced analysis approach.
    NOTE: This is legacy - new flow uses build_subagent_prompt_v2.

    Args:
        objective: What the subagent should accomplish
        questions: Specific questions to answer
        data: Relevant extracted facts (JSON subset only)
        tools: Available tools

    Returns:
        Formatted prompt string with balanced analysis instructions
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

**BALANCED ANALYSIS MANDATE:**

Your analysis must provide realistic, evidence-based evaluation. For every technical factor you identify:
- CLASSIFY risk severity: CRITICAL (>80% failure probability), HIGH (30-80%), MEDIUM (10-30%), LOW (<10%)
- Compare parameters to industry benchmarks and typical successful projects
- Distinguish between insurmountable barriers and solvable engineering challenges
- Provide specific mitigation strategies for each identified risk
- Cite evidence from similar projects or technical literature

Your output should be a concise, fact-based report that highlights:
- Quantified risks with severity classification and mitigation strategies
- Specific technical limitations with measurable consequences
- Realistic positive factors with supporting evidence
- Clear, actionable findings and recommendations that the Coordinator can integrate

Your report will be returned to the lead agent to integrate into a final response. Remember: Oxytec's business is solving difficult industrial challenges - provide both realistic assessment AND actionable paths forward.

**Your Objective:**
{objective}

**Questions to Answer:**
{questions_text}

**Relevant Technical Data (JSON subset only):**
```json
{json.dumps(data, indent=2, ensure_ascii=False)}
```
{tools_text}

Provide your balanced analysis, addressing all questions with severity-classified risks, mitigation strategies, and realistic opportunities.
"""

    return prompt
