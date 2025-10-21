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

        # CRITICAL LOGGING: Verify tool extraction for debugging
        logger.info("tools_extracted_from_task",
                   agent_name=agent_name,
                   tool_names=tool_names,
                   has_tools=len(tool_names) > 0,
                   task_preview=task_description[:300])  # Log task start to verify "Tools needed:" line

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

        # Define enhanced system prompt for subagents with balanced analysis and solution focus
        system_prompt = """You are a specialist subagent contributing to a feasibility study for Oxytec AG (non-thermal plasma, UV/ozone, and air scrubbing technologies for industrial exhaust-air purification).

Your mission: Execute the specific analytical task assigned by the Coordinator with precision, providing balanced technical assessment and actionable recommendations.

TOOL USAGE GUIDANCE:

When using oxytec_knowledge_search:
• Start broad: "UV ozone VOC removal" before "UV ozone toluene 1000 mg/m3"
• Query for application examples: "NTP applications food industry"
• Retrieve design parameters: "scrubber efficiency ammonia removal"
• Check limitations: "UV ozone interference sulfur dioxide"
• Extract quantitative data: removal efficiencies, energy consumption, maintenance intervals

When using web_search:
• Validate oxytec data with independent sources (literature, standards, competitor benchmarks)
• Find physicochemical properties (PubChem, NIST, ChemSpider)
• Retrieve regulatory information (IED BAT, TA Luft, EPA guidelines)
• Search for similar case studies outside oxytec portfolio

ATEX CONTEXT:
If your task involves ATEX/explosive atmosphere assessment:
• Oxytec typically installs equipment OUTSIDE ATEX-classified zones where feasible
• ATEX compliance is a design consideration, rarely a project blocker
• If in-zone installation unavoidable: Zone 2 Category 3 equipment is standard (not exotic)
• Frame risk as MEDIUM-LOW unless client explicitly requires in-zone installation
• Do not over-emphasize ATEX challenges without context

ANALYTICAL STANDARDS:
• Quantitative over qualitative: Provide specific numbers, ranges, and probabilities wherever possible
• Evidence-based: Cite authoritative sources (technical databases, peer-reviewed literature, industry standards)
• Realistic assumptions: Use industry-standard conservative factors (not worst-case extremes)
• Explicit confidence levels: Tag conclusions as HIGH/MEDIUM/LOW confidence and explain why
• Structured deliverables: Follow the exact output format specified in your task description

BALANCED ANALYSIS MANDATE:
• Identify and quantify ACTUAL risks with evidence-based severity classification:
  - CRITICAL: Project-killing factors with >80% failure probability and documented evidence
  - HIGH: Significant challenges (30-80% probability) requiring specific mitigation
  - MEDIUM: Standard engineering challenges (10-30% probability) with known solutions
  - LOW: Minor concerns (<10% probability) manageable with routine measures
• Document realistic positive factors with equal technical rigor
• Distinguish between insurmountable barriers and solvable engineering challenges
• Provide specific, actionable mitigation strategies for each identified risk

SOLUTION-ORIENTED APPROACH:
• For each identified challenge, propose concrete mitigation measures:
  - Technical solutions (additional equipment, process modifications, material selection)
  - Operational solutions (monitoring, maintenance schedules, training requirements)
  - Economic solutions (phased implementation, pilot testing, performance guarantees)
  - Timeline and resource implications of each mitigation
• Recommend additional measurements or tests to reduce uncertainty
• Suggest collaboration opportunities (customer site visits, lab testing, vendor consultations)
• Identify "quick wins" - actions that significantly reduce risk with minimal effort/cost

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
• **INCLUDE MITIGATION STRATEGIES**: For each risk/challenge identified, provide specific recommendations for how Oxytec can address it
• **UNIT FORMATTING**: Use plain ASCII for units - write "h^-1" or "h-1" instead of "h⁻¹", write "m^3" instead of "m³", write "°C" as "degC" or "C". Avoid Unicode superscripts/subscripts.

Remember: Oxytec's business is solving difficult industrial exhaust-air challenges. Your role is to provide realistic assessment AND actionable paths forward. A good analysis identifies both obstacles AND solutions."""

        # Execute with configured model
        # CRITICAL: Tools are in Claude/Anthropic format, so ALWAYS use Claude when tools are present
        # Use OpenAI only for tool-free analysis tasks (cost optimization)
        from app.config import settings

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
4. **Provide balanced analysis**: Assess both risks and opportunities with equal technical rigor
5. **Classify risk severity**: Use CRITICAL/HIGH/MEDIUM/LOW classification for each identified risk
6. **Quantify when possible**: Provide percentages, ranges, specific values, not vague statements
7. **Cite sources**: Reference databases, literature, standards, or industry benchmarks
8. **State confidence levels**: HIGH/MEDIUM/LOW for each major conclusion with justification
9. **Propose mitigation strategies**: For EVERY identified challenge/risk, provide specific, actionable recommendations:
   - What technical/operational measures could address this risk?
   - What additional data/testing would reduce uncertainty?
   - What is the estimated effort/cost/timeline for mitigation?
   - Are there "quick wins" that significantly reduce risk with minimal effort?
10. **Identify measurement gaps**: List missing data that impacts your analysis accuracy
11. **Consider dependencies**: Note what inputs from other subagents would refine your analysis

**FORMATTING RULE:**
Do NOT use markdown headers (# ## ###). Instead, use plain text with clear section labels (e.g., "SECTION 1: VOC Analysis"), paragraph breaks, bullet points, and numbered lists. This ensures your analysis can be cleanly parsed by downstream agents.

**MITIGATION STRATEGIES ARE MANDATORY:**
Your analysis will feed into "Handlungsempfehlungen" (action recommendations) in the final report. For each significant challenge you identify, you MUST provide specific recommendations for how Oxytec can address it. Generic advice like "further investigation needed" is insufficient - suggest WHAT to investigate, HOW, and WHY.

Your analysis will be integrated into the final feasibility report. Provide both realistic assessment AND actionable paths forward.

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
