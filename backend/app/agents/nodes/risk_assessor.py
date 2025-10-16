"""RISK ASSESSOR agent node - evaluates technical and commercial risks."""

from typing import Any
from app.agents.state import GraphState
from app.services.llm_service import LLMService
from app.utils.logger import get_logger

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
    extracted_facts = state["extracted_facts"]
    subagent_results = state["subagent_results"]

    logger.info("risk_assessor_started", session_id=session_id)

    try:
        llm_service = LLMService()

        # Format subagent results
        results_summary = "\n\n".join(
            f"**{result['agent_name']}** (Priority: {result.get('priority', 'N/A')})\n"
            f"Objective: {result['objective']}\n"
            f"Findings: {result['result']}"
            for result in subagent_results
        )

        # Create risk assessment prompt
        risk_prompt = f"""You are an expert risk analyst for technical feasibility studies in VOC treatment systems.

Based on the technical analysis from multiple specialist agents, perform a comprehensive risk assessment.

**Original Technical Data:**
```json
{extracted_facts}
```

**Analysis Results from Specialist Agents:**
{results_summary}

Perform a structured risk assessment covering:

1. **Technical Risks:**
   - VOC composition challenges (e.g., difficult compounds, high concentrations)
   - Process integration complexity
   - Equipment sizing and selection uncertainties
   - Performance guarantees and validation
   - Technology limitations
   - Scale-up risks

2. **Commercial Risks:**
   - Cost estimation uncertainty
   - Competition from alternative technologies
   - Market acceptance
   - Timeline and delivery risks
   - Customer-specific requirements

3. **Regulatory & Compliance Risks:**
   - Emission standards compliance
   - Permitting challenges
   - Future regulatory changes

4. **Risk Mitigation Strategies:**
   - For each major risk, propose mitigation approaches
   - Recommend pilot tests or demonstrations if needed
   - Suggest warranty/guarantee structures

5. **Overall Risk Assessment:**
   - Risk level: LOW / MEDIUM / HIGH
   - Confidence level in success: LOW / MEDIUM / HIGH
   - Key success factors
   - Deal-breaker issues (if any)

Return a comprehensive, structured risk assessment in JSON format with clear sections.
"""

        # Execute risk assessment
        risk_assessment = await llm_service.execute_structured(
            prompt=risk_prompt,
            system_prompt="You are a thorough risk analyst. Identify all potential issues while remaining balanced and constructive.",
            response_format="json"
        )

        logger.info(
            "risk_assessor_completed",
            session_id=session_id,
            risk_level=risk_assessment.get("overall_risk_level", "unknown")
        )

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
