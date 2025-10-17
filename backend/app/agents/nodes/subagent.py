"""SUBAGENT execution - dynamic parallel agent execution."""

import asyncio
import traceback
import json
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
        # Extract name from task description for instance naming
        task_desc = subagent_def.get("task", "")
        agent_name = extract_agent_name(task_desc) or f"agent_{idx}"

        task = execute_single_subagent(
            subagent_def=subagent_def,
            state=state,
            instance_name=f"subagent_{idx}_{agent_name}"
        )
        tasks.append(task)

    # Execute all subagents in parallel
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

        # Extract tool names from task description
        logger.debug("step_2_extract_tools", agent_name=agent_name)
        tool_names = extract_tools_from_task(task_description)

        # Build subagent prompt (now much simpler - task description has everything)
        logger.debug("step_3_build_prompt", agent_name=agent_name)
        prompt = build_subagent_prompt_v2(
            task_description=task_description,
            relevant_content=relevant_content
        )

        # Get tool definitions for this subagent
        logger.debug("step_4_get_tools", agent_name=agent_name, tool_names=tool_names)
        tools = get_tools_for_subagent(tool_names)
        logger.debug("step_4_tools_retrieved", agent_name=agent_name, num_tools=len(tools) if tools else 0)

        # Define enhanced system prompt for subagents with critical risk focus
        system_prompt = """You are a specialist subagent contributing to a critical feasibility study for Oxytec AG (non-thermal plasma, UV/ozone, and air scrubbing technologies for industrial exhaust-air purification).

Your mission: Execute the specific analytical task assigned by the Coordinator with ruthless precision and realistic risk assessment.

ANALYTICAL STANDARDS:
• Quantitative over qualitative: Provide specific numbers, ranges, and probabilities wherever possible
• Evidence-based: Cite authoritative sources (technical databases, peer-reviewed literature, industry standards)
• Conservative assumptions: When uncertain, favor worst-case scenarios over optimistic projections
• Explicit confidence levels: Tag conclusions as HIGH/MEDIUM/LOW confidence and explain why
• Structured deliverables: Follow the exact output format specified in your task description

RISK-FOCUSED MANDATE (70/30 rule):
• 70% of analysis: Identify and quantify risks, limitations, show-stoppers, project-killing factors
• 30% of analysis: Document realistic positive factors with supporting evidence
• Flag any factor combinations that could cause cascade failures
• Provide specific probabilities (%) for failure scenarios when sufficient data exists

TECHNICAL RIGOR:
• Compare parameters against industry benchmarks and typical successful projects
• Identify measurement gaps and specify their impact on design/cost uncertainty
• For chemical/physical properties: Use authoritative databases (PubChem, NIST, ChemSpider, etc.)
• For technology performance: Reference vendor data, case studies, published literature
• State assumptions explicitly and test sensitivity to key variables

OUTPUT REQUIREMENTS:
• Address EVERY question in your task description
• Provide deliverables in the exact format requested
• Use clear, actionable language suitable for integration into final report
• Prioritize machine-readable formats (tables, structured lists) over prose when appropriate
• **CRITICAL: Do NOT use markdown headers (# ## ###). Use plain text with clear section labels, paragraph breaks, and bullet/numbered lists only.**
• Write in a professional, technical report style without decorative formatting

Remember: Oxytec's reputation depends on realistic project assessment. A conservative, evidence-based analysis that identifies deal-breakers early is vastly more valuable than an optimistic assessment that leads to costly failures."""

        # Execute with configured model
        # Note: Tools use Claude format, so use Claude for subagents with tools
        # OpenAI for subagents without tools (text-only analysis)
        from app.config import settings

        if tools:
            # Use Claude for tool calling (tools are in Claude format)
            logger.debug("step_5_execute_with_tools", agent_name=agent_name)
            result = await llm_service.execute_with_tools(
                prompt=prompt,
                tools=tools,
                max_iterations=5,
                system_prompt=system_prompt,
                temperature=settings.subagent_temperature
            )
        else:
            # Use OpenAI for text-only analysis
            logger.debug("step_5_execute_openai", agent_name=agent_name, model=settings.subagent_model)
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
    Looks for "Tools needed: tool_name" line.

    Args:
        task_description: Full task description

    Returns:
        List of tool names (e.g., ["product_database", "web_search"] or ["none"])
    """
    lines = task_description.split('\n')
    for line in lines:
        if line.strip().lower().startswith("tools needed:"):
            # Extract tool name after "Tools needed:"
            tool_text = line.split(":", 1)[1].strip().lower()

            # Check for specific tool names
            if "product_database" in tool_text:
                return ["product_database"]
            elif "web_search" in tool_text:
                return ["web_search"]
            elif "none" in tool_text or not tool_text:
                return []

    return []  # No tools by default


def build_subagent_prompt_v2(
    task_description: str,
    relevant_content: str
) -> str:
    """
    Build a prompt for a subagent using Flowise-style structure.

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

    prompt = f"""You have been assigned a specialized analytical task by the Coordinator as part of an Oxytec AG feasibility study. Read your task description carefully and execute it with precision.

═══════════════════════════════════════════════════════════════════════════════
YOUR TASK ASSIGNMENT
═══════════════════════════════════════════════════════════════════════════════

{task_description}

═══════════════════════════════════════════════════════════════════════════════
TECHNICAL DATA (JSON subset relevant to your task)
═══════════════════════════════════════════════════════════════════════════════

```json
{relevant_content}
```

═══════════════════════════════════════════════════════════════════════════════
EXECUTION REQUIREMENTS
═══════════════════════════════════════════════════════════════════════════════

1. **Answer ALL questions** specified in your task description above
2. **Provide deliverables** in the exact format requested
3. **Apply method hints** and quality criteria specified in your task
4. **Follow the 70/30 rule**: 70% critical risk analysis, 30% realistic positive factors
5. **Quantify when possible**: Provide percentages, ranges, specific values, not vague statements
6. **Cite sources**: Reference databases, literature, standards, or industry benchmarks
7. **State confidence levels**: HIGH/MEDIUM/LOW for each major conclusion with justification
8. **Flag show-stoppers**: Clearly identify any factors that would prevent project success
9. **Identify measurement gaps**: List missing data that impacts your analysis accuracy
10. **Consider dependencies**: Note what inputs from other subagents would refine your analysis

**FORMATTING RULE:**
Do NOT use markdown headers (# ## ###). Instead, use plain text with clear section labels (e.g., "SECTION 1: VOC Analysis"), paragraph breaks, bullet points, and numbered lists. This ensures your analysis can be cleanly parsed by downstream agents.

Your analysis will be integrated into the final feasibility report and used by the Risk Assessor to determine project viability. Precision and realism are critical.

Provide your complete analysis now:
"""

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
{json.dumps(data, indent=2, ensure_ascii=False)}
```
{tools_text}

Provide your analysis with CRITICAL RISK FOCUS, addressing all questions with quantified risks and probabilities. Focus 70% on risks and limitations, 30% on positive factors.
"""

    return prompt
