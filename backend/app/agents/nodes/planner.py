"""PLANNER agent node - dynamically creates subagent execution plan."""

from typing import Any
from app.agents.state import GraphState
from app.services.llm_service import LLMService
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def planner_node(state: GraphState) -> dict[str, Any]:
    """
    PLANNER node: Dynamically decide which subagents to create and what they should analyze.

    This is the key innovation - the planner autonomously decides:
    - How many subagents are needed
    - What each subagent should investigate
    - Which tools each subagent should use
    - What data each subagent needs

    The planner creates a structured plan that will be executed in parallel.

    Args:
        state: Current graph state with extracted facts

    Returns:
        Updated state with planner_plan containing subagent definitions
    """

    session_id = state["session_id"]
    extracted_facts = state["extracted_facts"]

    logger.info("planner_started", session_id=session_id)

    try:
        llm_service = LLMService()

        # Create planning prompt - ONLY sees output of previous agent (EXTRACTOR)
        planning_prompt = f"""You are the Coordinator for feasibility studies conducted by oxytec AG. Oxytec specialized in non-thermal plasma (NTP), UV/ozone and air scrubbing technologies for industrial exhaust-air purification. The purpose of each study is to decide whether oxytec should proceed with deeper engagement with a prospective customer (e.g., pilot, PoC, proposal) and whether NTP, UV/ozone, exhaust air scrubbers, or a combination of these technologies can augment the customer's current abatement setup or fully replace it.

**Context:** You are given a JSON file compiled from documents the prospective customer provided to oxytec. It summarizes its current industrial exhaust-air situation (e.g., VOC composition, volume flows, operating schedule, existing abatement measures/technologies, constraints, safety/ATEX context) and may reference attached materials. Use this material as the basis for planning.

**Extracted Facts:**
```json
{extracted_facts}
```

**Your job:** Decompose the overall study into well-scoped subtasks and dispatch domain-specific subagents to perform the analysis. For each subagent, provide:
- a clear objective and narrowly scoped questions,
- exact inputs (JSON paths/fields and any referenced attachments),
- method hints/quality criteria as needed,
- deliverables (concise outputs the Writer can integrate),
- dependencies and sequencing, while maximizing parallelism and minimizing overlap.

**Important rule:** When delegating tasks, you must not forward the entire JSON file. Instead, extract only the section(s) directly relevant to the subagent's assignment and pass them on unchanged. Do not alter field names, values, or structure in any way. Each subagent should only see the JSON subset that corresponds to its task.

**You do not perform analyses and do not produce the final report.** Your sole responsibility is to produce an efficient, well-reasoned plan and launch the minimum sufficient set of subagents with unambiguous instructions optimized for accuracy, critical assessment, and realistic risk evaluation.

Common subagent types you might create (3-8 total depending on complexity):
1. **VOC Analysis Agent**: Analyze VOC composition, concentrations, challenging compounds, destruction efficiency requirements
2. **Product Selection Agent**: Identify suitable Oxytec products (NTP reactors, UV systems, ozone generators, air scrubbers)
3. **Process Design Agent**: Design treatment process flow, sizing, integration with existing systems
4. **Energy Analysis Agent**: Calculate energy consumption, operating costs
5. **Competitive Analysis Agent**: Compare NTP/UV/scrubbers vs. alternative technologies (thermal oxidizers, adsorption, etc.)
6. **Regulatory Compliance Agent**: Check compliance with emissions regulations, ATEX requirements, permits
7. **Economic Analysis Agent**: ROI calculation, payback period, lifecycle costs vs. current solution
8. **Technical Risk Agent**: Identify technical challenges, material compatibility, fouling risks

For each subagent, define:
- **name**: Unique identifier (e.g., "voc_analysis", "product_selection")
- **objective**: Clear description focused on critical risk assessment
- **questions**: List of specific questions emphasizing risks and limitations
- **input_fields**: Which fields from extracted_facts this agent needs (provide JSON subset only)
- **tools**: Which tools the agent can use ["product_database", "web_search", "none"]
- **priority**: "high", "medium", or "low"

Return a JSON object with this structure:
{{
  "subagents": [
    {{
      "name": "agent_name",
      "objective": "What this agent should critically assess",
      "questions": ["Risk-focused question 1", "Question 2"],
      "input_fields": ["specific_field_from_extracted_facts"],
      "tools": ["product_database"],
      "priority": "high"
    }}
  ],
  "reasoning": "Brief explanation of planning strategy with emphasis on risk identification"
}}

Remember: Focus subagent instructions on realistic risk evaluation rather than optimistic possibilities. Each subagent should prioritize identifying project-killing factors.
"""

        # Execute planning with configured OpenAI model (gpt-mini by default)
        from app.config import settings
        plan = await llm_service.execute_structured(
            prompt=planning_prompt,
            system_prompt="You are a strategic planning coordinator for critical feasibility assessments. Create comprehensive, risk-focused parallel execution plans. Return only valid JSON.",
            response_format="json",
            temperature=settings.planner_temperature,
            use_openai=True,
            openai_model=settings.planner_model
        )

        num_subagents = len(plan.get("subagents", []))

        logger.info(
            "planner_completed",
            session_id=session_id,
            num_subagents=num_subagents
        )

        # Validate plan
        if num_subagents == 0:
            logger.warning("planner_no_subagents", session_id=session_id)
            return {
                "planner_plan": plan,
                "warnings": ["Planner created 0 subagents"]
            }

        if num_subagents > 10:
            logger.warning(
                "planner_too_many_subagents",
                session_id=session_id,
                count=num_subagents
            )
            # Truncate to first 10
            plan["subagents"] = plan["subagents"][:10]

        return {
            "planner_plan": plan
        }

    except Exception as e:
        logger.error(
            "planner_failed",
            session_id=session_id,
            error=str(e)
        )
        return {
            "planner_plan": {"subagents": []},
            "errors": [f"Planning failed: {str(e)}"]
        }
