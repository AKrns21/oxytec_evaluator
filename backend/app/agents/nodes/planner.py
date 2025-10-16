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
    user_input = state["user_input"]

    logger.info("planner_started", session_id=session_id)

    try:
        llm_service = LLMService()

        # Create planning prompt
        planning_prompt = f"""You are an expert feasibility study planner for Oxytec, a plasma-based VOC treatment company.

Based on the extracted technical facts from customer documents, you need to create a detailed execution plan for parallel subagents.

**Extracted Facts:**
```json
{extracted_facts}
```

**User Input:**
```json
{user_input}
```

Your task is to create a plan that defines multiple subagents to run in parallel. Each subagent will investigate a specific aspect of the feasibility study.

Common subagent types you might create:
1. **VOC Analysis Agent**: Analyze VOC composition, concentrations, destruction efficiency requirements
2. **Product Selection Agent**: Identify suitable Oxytec products (NTP reactors, UV lamps, ozone generators, etc.)
3. **Process Design Agent**: Design the treatment process flow, sizing, integration
4. **Energy Analysis Agent**: Calculate energy consumption, operating costs
5. **Competitive Analysis Agent**: Compare with alternative technologies
6. **Regulatory Compliance Agent**: Check compliance with regulations and standards
7. **Economic Analysis Agent**: ROI calculation, payback period, lifecycle costs

For each subagent, define:
- **name**: Unique identifier (e.g., "voc_analysis", "product_selection")
- **objective**: Clear description of what this agent should accomplish
- **questions**: List of specific questions the agent should answer
- **input_fields**: Which fields from extracted_facts this agent needs
- **tools**: Which tools the agent can use ["product_database", "web_search", "none"]
- **priority**: "high", "medium", or "low"

Create between 3-8 subagents depending on the complexity of the inquiry.

Return a JSON object with this structure:
{{
  "subagents": [
    {{
      "name": "agent_name",
      "objective": "What this agent should accomplish",
      "questions": ["Question 1", "Question 2"],
      "input_fields": ["field1", "field2"],
      "tools": ["product_database"],
      "priority": "high"
    }}
  ],
  "reasoning": "Brief explanation of the planning strategy"
}}
"""

        # Execute planning with Claude
        plan = await llm_service.execute_structured(
            prompt=planning_prompt,
            system_prompt="You are a strategic planning expert. Create comprehensive, parallel execution plans for feasibility studies.",
            response_format="json"
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
