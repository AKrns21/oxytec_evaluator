"""PLANNER agent node - dynamically creates subagent execution plan."""

import json
from typing import Any
from app.agents.state import GraphState
from app.services.llm_service import LLMService
from app.utils.logger import get_logger
from app.agents.prompts.versions import get_prompt_version
from app.config import settings
from app.models.database import AgentOutput
from app.db.session import AsyncSessionLocal

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

        # Serialize extracted_facts to JSON string
        extracted_facts_json = json.dumps(extracted_facts, indent=2, ensure_ascii=False)

        # Load versioned prompt
        prompt_data = get_prompt_version("planner", settings.planner_prompt_version)
        prompt_template = prompt_data["PROMPT_TEMPLATE"]
        system_prompt = prompt_data["SYSTEM_PROMPT"]

        # Create planning prompt from template
        planning_prompt = prompt_template.format(
            extracted_facts_json=extracted_facts_json
        )

        # Execute planning with configured OpenAI model (gpt-mini by default)
        from app.agents.validation import validate_planner_output
        from pydantic import ValidationError

        plan = await llm_service.execute_structured(
            prompt=planning_prompt,
            system_prompt=system_prompt,  # Use versioned system prompt
            response_format="json",
            temperature=settings.planner_temperature,
            use_openai=True,
            openai_model=settings.planner_model
        )

        # Validate plan structure with Pydantic
        try:
            validated_plan = validate_planner_output(plan)
            plan = validated_plan.model_dump()  # Convert back to dict

            num_subagents = len(plan.get("subagents", []))

            logger.info(
                "planner_completed_validated",
                session_id=session_id,
                num_subagents=num_subagents
            )

        except ValidationError as e:
            logger.error(
                "planner_validation_failed",
                session_id=session_id,
                validation_errors=str(e),
                raw_plan_preview=str(plan)[:500]  # Log first 500 chars for debugging
            )

            # Check if plan has subagents despite validation error
            if isinstance(plan, dict) and "subagents" in plan and len(plan["subagents"]) > 0:
                logger.warning(
                    "planner_validation_failed_but_has_subagents",
                    session_id=session_id,
                    num_subagents=len(plan["subagents"]),
                    message="Proceeding with unvalidated plan to avoid blocking execution"
                )
                # Continue with unvalidated plan rather than blocking
                return {
                    "planner_plan": plan,
                    "warnings": [f"Planner output validation failed but proceeding: {str(e)}"]
                }
            else:
                # No subagents found - this is a critical failure
                logger.error(
                    "planner_validation_failed_no_subagents",
                    session_id=session_id
                )
                return {
                    "planner_plan": {"subagents": []},
                    "errors": [f"Planner output validation failed: {str(e)}"]
                }

        # Save agent output with prompt version to database
        try:
            async with AsyncSessionLocal() as db:
                agent_output = AgentOutput(
                    session_id=session_id,
                    agent_type="planner",
                    output_type="plan",
                    content={
                        "planner_plan": plan,
                        "rendered_prompt": planning_prompt,
                        "system_prompt": system_prompt
                    },
                    prompt_version=settings.planner_prompt_version
                )
                db.add(agent_output)
                await db.commit()
                logger.info("planner_output_saved", session_id=session_id, prompt_version=settings.planner_prompt_version)
        except Exception as db_error:
            logger.warning("planner_output_save_failed", session_id=session_id, error=str(db_error))

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
