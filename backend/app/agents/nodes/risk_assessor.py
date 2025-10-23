"""RISK ASSESSOR agent node - evaluates technical and commercial risks."""

from typing import Any
from app.agents.state import GraphState
from app.services.llm_service import LLMService
from app.utils.logger import get_logger
from app.agents.prompts import POSITIVE_FACTORS_FILTER, OXYTEC_EXPERIENCE_CHECK
from app.agents.prompts.versions import get_prompt_version
from app.config import settings
from app.models.database import AgentOutput
from app.db.session import AsyncSessionLocal

logger = get_logger(__name__)


async def risk_assessor_node(state: GraphState) -> dict[str, Any]:
    """
    RISK ASSESSOR node: Analyze technical and commercial risks.

    This agent synthesizes all subagent findings and identifies:
    - Technical risks and challenges
    - Commercial risks
    - Mitigation strategies
    - Confidence levels

    Args:
        state: Current graph state with subagent results

    Returns:
        Updated state with risk_assessment
    """

    session_id = state["session_id"]
    subagent_results = state["subagent_results"]
    extracted_facts = state.get("extracted_facts", {})

    logger.info("risk_assessor_started", session_id=session_id)

    try:
        llm_service = LLMService()

        # Import json for serialization
        import json

        # Check if customer questions exist
        customer_questions = extracted_facts.get("customer_specific_questions", [])
        has_customer_questions = len(customer_questions) > 0

        # Create customer questions context string if applicable
        customer_questions_context = ""
        if has_customer_questions:
            questions_list = "\n".join([
                f"{i+1}. {q.get('question_text', 'N/A')}"
                for i, q in enumerate(customer_questions)
            ])
            customer_questions_context = f"""

**CUSTOMER-SPECIFIC QUESTIONS DETECTED:**

The customer asked the following explicit questions in their inquiry documents:

{questions_list}

These questions MUST be addressed in your risk synthesis:
- Include in critical_success_factors: "Provide direct answers to customer's specific questions about [main topic from questions above]"
- In mitigation_priorities: Reference how recommended actions address the customer's questions
- Look for subagent findings from "Customer Question Response Specialist" if present
"""

        # Consolidate all subagent findings into one continuous analysis (Flowise pattern)
        # Just concatenate the actual findings with section breaks, no agent names/metadata
        consolidated_findings = "\n\n".join(
            result['result'] for result in subagent_results
        )

        # Load versioned prompt
        prompt_data = get_prompt_version("risk_assessor", settings.risk_assessor_prompt_version)
        prompt_template = prompt_data["PROMPT_TEMPLATE"]
        system_prompt = prompt_data["SYSTEM_PROMPT"]

        # Create risk assessment prompt from template
        risk_prompt = prompt_template.format(
            customer_questions_context=customer_questions_context,
            POSITIVE_FACTORS_FILTER=POSITIVE_FACTORS_FILTER,
            OXYTEC_EXPERIENCE_CHECK=OXYTEC_EXPERIENCE_CHECK,
            consolidated_findings=consolidated_findings
        )

        # Execute risk assessment with configured OpenAI model (gpt-5 by default)
        from app.agents.validation import validate_risk_assessor_output
        from pydantic import ValidationError

        risk_assessment = await llm_service.execute_structured(
            prompt=risk_prompt,
            system_prompt=system_prompt,  # Use versioned system prompt
            response_format="json",
            temperature=settings.risk_assessor_temperature,
            use_openai=True,
            openai_model=settings.risk_assessor_model
        )

        # Validate risk assessment output
        try:
            validated_assessment = validate_risk_assessor_output(risk_assessment)
            risk_assessment = validated_assessment.model_dump()

            logger.info(
                "risk_assessor_completed_validated",
                session_id=session_id,
                risk_level=risk_assessment.get("overall_risk_level"),
                recommendation=risk_assessment.get("go_no_go_recommendation")
            )
        except ValidationError as e:
            logger.error(
                "risk_assessment_validation_failed",
                session_id=session_id,
                errors=str(e),
                raw_assessment_preview=str(risk_assessment)[:500]
            )
            # Return error structure matching validation model
            return {
                "risk_assessment": {
                    "executive_risk_summary": f"Validation failed: {str(e)}",
                    "risk_classification": {
                        "technical_risks": [],
                        "commercial_risks": [],
                        "data_quality_risks": []
                    },
                    "overall_risk_level": "HIGH",
                    "go_no_go_recommendation": "NO_GO",
                    "critical_success_factors": ["Fix risk assessment validation errors"],
                    "mitigation_priorities": []
                },
                "errors": [f"Risk assessment validation failed: {str(e)}"]
            }

        # Save agent output with prompt version to database
        try:
            async with AsyncSessionLocal() as db:
                agent_output = AgentOutput(
                    session_id=session_id,
                    agent_type="risk_assessor",
                    output_type="assessment",
                    content={
                        "risk_assessment": risk_assessment,
                        "rendered_prompt": risk_prompt,
                        "system_prompt": system_prompt
                    },
                    prompt_version=settings.risk_assessor_prompt_version
                )
                db.add(agent_output)
                await db.commit()
                logger.info("risk_assessor_output_saved", session_id=session_id, prompt_version=settings.risk_assessor_prompt_version)
        except Exception as db_error:
            logger.warning("risk_assessor_output_save_failed", session_id=session_id, error=str(db_error))

        return {
            "risk_assessment": risk_assessment
        }

    except Exception as e:
        logger.error(
            "risk_assessor_failed",
            session_id=session_id,
            error=str(e)
        )
        return {
            "risk_assessment": {
                "error": str(e),
                "overall_risk_level": "UNKNOWN"
            },
            "errors": [f"Risk assessment failed: {str(e)}"]
        }
