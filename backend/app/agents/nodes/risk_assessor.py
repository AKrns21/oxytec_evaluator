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
    subagent_results = state["subagent_results"]

    logger.info("risk_assessor_started", session_id=session_id)

    try:
        llm_service = LLMService()

        # Consolidate all subagent findings into one continuous analysis (Flowise pattern)
        # Just concatenate the actual findings with section breaks, no agent names/metadata
        consolidated_findings = "\n\n".join(
            result['result'] for result in subagent_results
        )

        # Create risk assessment prompt - ONLY sees all subagent outputs (exception to chain rule)
        # Matches Flowise pattern: consolidated findings in <new_findings> tags
        risk_prompt = f"""You are the Risk Assessor, a specialized critical risk evaluation agent for oxytec AG feasibility studies. Oxytec specialized in non-thermal plasma (NTP), UV/ozone and air scrubbing technologies for industrial exhaust-air purification. Your sole purpose is to identify scenarios, factor combinations, and risk patterns that could cause complete project failure, significant cost overruns, or reputational damage.

CONTEXT: You are given an analysis from domain-specific subagents that summarizes the current industrial exhaust-air situation (e.g., VOC composition, volume flows, operating schedule, existing abatement measures/technologies, constraints, safety/ATEX context) and may reference attached materials. Use this material as the basis for your evaluation.

MISSION: Determine if the implementation as proposed by the subagents has high-probability failure modes that should prevent oxytec from proceeding.

<new_findings>

{consolidated_findings}

</new_findings>

**CRITICAL EVALUATION FRAMEWORK:** You must evaluate and quantify the following failure scenarios:

**TECHNICAL FAILURE SCENARIOS:**
- Equipment fouling/degradation rates that make operation uneconomical
- Corrosion/material compatibility issues leading to premature failure
- Safety/ATEX compliance failures that halt operations
- Treatment efficiency below customer requirements

**ECONOMIC FAILURE SCENARIOS:**
- Operating costs exceeding customer budget by >50%
- Maintenance intervals creating unacceptable downtime
- Energy consumption exceeding economic viability thresholds
- Total project costs >2.5x initial estimates

**COMBINED RISK AMPLIFICATION:**
- Identify how multiple moderate risks combine to create severe problems
- Assess "cascade failure" scenarios where one problem triggers others
- Evaluate whether simultaneous challenges exceed oxytec's technical capabilities

**QUANTIFIED OUTPUT REQUIREMENTS:** For each identified failure scenario, provide:
- Probability of occurrence (%)
- Timeline to failure (days/weeks/months)
- Financial impact (% of project value)
- Mitigation complexity (Low/Medium/High/Impossible)

**DECISION CRITERIA:**
Issue PROJECT FAILURE WARNING if:
- Any single failure scenario >70% probability
- Combined failure risk >50% probability
- Required maintenance intervals <21 days
- Predicted operating costs >3x customer's current solution
- Safety/regulatory compliance cannot be assured

**BENCHMARKING REQUIREMENT:** Compare identified parameters against:
- Industry standard projects (maintenance intervals, operating costs, efficiency)
- Oxytec's previous similar installations
- Published failure rates for comparable technologies

Your assessment has VETO POWER over optimistic technical evaluations. If you identify high-probability failure scenarios, these must be reflected in the final feasibility rating regardless of other agents' findings.

**OUTPUT FORMAT:**
Return a JSON object with the following structure:
{{
  "executive_risk_summary": "2-3 sentence overview of critical risks",
  "critical_failure_scenarios": [
    {{
      "scenario": "Description of failure mode",
      "probability_percent": 0-100,
      "timeline_to_failure": "days/weeks/months",
      "financial_impact_percent": 0-100,
      "mitigation_complexity": "Low/Medium/High/Impossible"
    }}
  ],
  "quantified_risk_matrix": {{
    "technical_risks": [
      {{"risk": "description", "probability": 0-100, "impact": "High/Medium/Low", "mitigation": "approach"}}
    ],
    "economic_risks": [
      {{"risk": "description", "probability": 0-100, "impact": "High/Medium/Low", "mitigation": "approach"}}
    ],
    "combined_amplification_risks": [
      {{"combination": "risk1 + risk2", "amplified_probability": 0-100, "cascade_effect": "description"}}
    ]
  }},
  "benchmarking_comparison": {{
    "maintenance_intervals": "comparison to industry standard",
    "operating_costs": "comparison to typical projects",
    "efficiency_expectations": "realistic vs optimistic"
  }},
  "final_recommendation": "PROCEED / PROCEED WITH CAUTION / DO NOT PROCEED",
  "justification": "Detailed justification based on failure probability analysis",
  "veto_flag": true/false,
  "veto_reason": "If veto_flag is true, explain why optimistic evaluations should be overridden"
}}

Remember: oxytec's business success depends on realistic project assessment. It is better to reject a potentially profitable project than to accept a project that will fail and damage oxytec's reputation.
"""

        # Execute risk assessment with configured OpenAI model (gpt-5 by default)
        from app.config import settings
        risk_assessment = await llm_service.execute_structured(
            prompt=risk_prompt,
            system_prompt="You are a critical risk evaluator with VETO POWER. Your job is to identify project-killing scenarios and prevent oxytec from pursuing doomed projects. Be ruthlessly realistic about failure probabilities. Return only valid JSON.",
            response_format="json",
            temperature=settings.risk_assessor_temperature,
            use_openai=True,
            openai_model=settings.risk_assessor_model
        )

        logger.info(
            "risk_assessor_completed",
            session_id=session_id,
            risk_level=risk_assessment.get("final_recommendation", "unknown")
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
