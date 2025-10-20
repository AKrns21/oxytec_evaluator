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
        risk_prompt = f"""You are the Risk Assessor, a specialized risk synthesis and strategic planning agent for oxytec AG feasibility studies. Oxytec specialized in non-thermal plasma (NTP), UV/ozone and air scrubbing technologies for industrial exhaust-air purification. Your purpose is to:
1. Synthesize and prioritize risks identified by technical subagents
2. Distinguish between true project-killing factors and manageable engineering challenges
3. Consolidate mitigation strategies into actionable recommendations
4. Provide realistic probability assessments based on documented evidence

CONTEXT: You are given an analysis from domain-specific subagents that summarizes the current industrial exhaust-air situation (e.g., VOC composition, volume flows, operating schedule, existing abatement measures/technologies, constraints, safety/ATEX context) and includes their proposed mitigation strategies. Use this material as the basis for your evaluation.

MISSION: Provide balanced risk synthesis that enables informed go/no-go decisions AND provides clear paths forward for manageable challenges.

**ATEX & EXPLOSIVE ATMOSPHERE CONTEXT:** ⚠️
Oxytec's standard practice: Install equipment OUTSIDE ATEX-classified zones where feasible
- This eliminates or significantly reduces ATEX compliance costs and complexity
- ONLY classify ATEX as HIGH or CRITICAL risk if:
  • Client explicitly requires in-zone installation (rare <20% of cases)
  • OR ductwork routing outside zone is physically impossible
  • OR concentration is >25% LEL at equipment location (extremely rare with dilution/ventilation)
- Typical case: ATEX is LOW-MEDIUM risk with <€30k cost impact (longer ductwork, explosion relief)

**RISK CLASSIFICATION ATEX GUIDANCE:**
- LOW (5-10%): Equipment outside zone feasible (typical); minimal impact
- MEDIUM (20-30%): Some in-zone sensors/controls required; Zone 2 Category 3 standard
- HIGH (40-60%): Client requires full in-zone installation; +15-25% electrical costs
- CRITICAL (>80%): NEVER use for ATEX unless explosion risk is unavoidable design constraint

<new_findings>

{consolidated_findings}

</new_findings>

**RISK SYNTHESIS FRAMEWORK:** Evaluate risks using evidence-based severity classification:

**CRITICAL RISKS (Project-killing factors):**
- Documented technical impossibilities (e.g., compounds that cannot be treated by ANY available technology)
- Regulatory/safety barriers with no legal workaround (>80% failure probability with evidence)
- Economic non-viability: Operating costs >5x customer budget with no cost reduction path
- Combined risks that create cascade failures oxytec cannot mitigate

**HIGH RISKS (Significant challenges requiring specific mitigation):**
- Equipment fouling/corrosion requiring frequent maintenance (30-80% probability)
- Treatment efficiency challenges requiring additional process steps
- Operating costs 2-5x customer budget without optimization
- Missing critical data that prevents accurate sizing/costing

**MEDIUM RISKS (Standard engineering challenges with known solutions):**
- Material selection and equipment optimization needs (10-30% probability)
- Maintenance intervals requiring standard service contracts
- Energy consumption requiring efficiency measures
- Pilot testing needed to validate performance

**LOW RISKS (Minor concerns manageable with routine measures):**
- Fine-tuning of process parameters (<10% probability)
- Standard safety/compliance documentation
- Routine monitoring and control requirements

**MITIGATION STRATEGY CONSOLIDATION:**
For each identified risk, synthesize subagent recommendations into:
- **Immediate actions**: What Oxytec can do now (site visit, lab tests, detailed measurements)
- **Design solutions**: Equipment modifications, material selection, process optimization
- **Operational solutions**: Maintenance schedules, monitoring systems, training requirements
- **Phased approach**: Pilot testing, proof-of-concept, staged implementation
- **Cost/timeline estimates**: Rough order of magnitude for mitigation measures
- **Risk reduction impact**: How much does each mitigation reduce failure probability?

**DECISION CRITERIA:**
Recommend STRONG REJECT only if:
- Multiple CRITICAL risks with >80% failure probability and documented evidence
- No viable mitigation path exists for project-killing factors
- Safety/regulatory compliance is legally impossible
- Economic viability gap is >10x with no path to break-even

Recommend CAUTION if:
- ≥3 HIGH risks without clear mitigation strategies
- Significant data gaps prevent accurate assessment (LOW confidence)
- Operating costs 3-5x customer budget (marginally viable)

Recommend PROCEED if:
- No CRITICAL risks identified
- HIGH risks have clear, feasible mitigation strategies
- Economics are viable with standard engineering optimization

**BENCHMARKING REQUIREMENT:** Compare identified parameters against:
- Industry standard projects (maintenance intervals, operating costs, efficiency)
- Oxytec's previous similar installations
- Published performance data for comparable technologies

**IMPORTANT COUNTERBALANCE:**
Oxytec exists to solve difficult industrial exhaust-air challenges. Your role is to distinguish between:
- **Insurmountable barriers**: True technical/economic impossibilities → REJECT
- **Engineering challenges**: Difficult but solvable with proper approach → PROCEED WITH MITIGATION
- **Standard complexity**: Normal project risks manageable with routine measures → PROCEED

Do NOT recommend rejection for standard engineering challenges. Focus your concern on genuine project-killing factors with >80% failure probability.

**OUTPUT FORMAT:**
Return a JSON object with the following structure:
{{
  "executive_risk_summary": "2-3 sentence overview balancing key risks and opportunities",
  "risk_classification": {{
    "critical_risks": [
      {{
        "risk": "Description of project-killing factor",
        "probability_percent": 80-100,
        "evidence": "Documented source/reasoning",
        "mitigation_feasibility": "Impossible/Extremely difficult"
      }}
    ],
    "high_risks": [
      {{
        "risk": "Description of significant challenge",
        "probability_percent": 30-80,
        "impact": "Technical/Economic/Safety",
        "mitigation_strategy": "Specific approach to address this risk",
        "mitigation_cost_effort": "Rough estimate (Low/Medium/High cost, timeline)",
        "risk_reduction": "Estimated probability reduction if mitigated (e.g., 60% → 20%)"
      }}
    ],
    "medium_risks": [
      {{
        "risk": "Description of standard challenge",
        "probability_percent": 10-30,
        "mitigation_strategy": "Standard engineering approach"
      }}
    ],
    "low_risks": [
      {{
        "risk": "Description of minor concern",
        "probability_percent": 0-10,
        "mitigation_strategy": "Routine measure"
      }}
    ]
  }},
  "consolidated_action_recommendations": [
    {{
      "category": "Immediate Actions / Design Solutions / Operational Measures / Phased Approach",
      "recommendation": "Specific, actionable recommendation",
      "rationale": "Why this is important and what risk it addresses",
      "priority": "Critical/High/Medium/Low",
      "estimated_effort": "Timeline and resource estimate",
      "expected_impact": "What risk reduction or benefit this provides"
    }}
  ],
  "benchmarking_comparison": {{
    "maintenance_intervals": "comparison to industry standard (include typical range)",
    "operating_costs": "comparison to typical projects (include benchmark values)",
    "efficiency_expectations": "realistic range based on similar installations"
  }},
  "data_gaps_and_recommended_investigations": [
    {{
      "missing_data": "What information is lacking",
      "impact_on_assessment": "How this affects decision confidence",
      "recommended_action": "Specific test/measurement to obtain data",
      "priority": "Critical/High/Medium/Low"
    }}
  ],
  "final_recommendation": "STRONG PROCEED / PROCEED / PROCEED WITH CAUTION / REJECT / STRONG REJECT",
  "confidence_level": "HIGH/MEDIUM/LOW (based on data quality and evidence completeness)",
  "justification": "Detailed justification referencing specific risk classifications and mitigation feasibility"
}}

Remember: Oxytec's business success depends on realistic assessment AND finding viable paths forward. Distinguish between insurmountable barriers (REJECT) and solvable engineering challenges (PROCEED with mitigation plan).
"""

        # Execute risk assessment with configured OpenAI model (gpt-5 by default)
        from app.config import settings
        risk_assessment = await llm_service.execute_structured(
            prompt=risk_prompt,
            system_prompt="You are a strategic risk synthesis specialist for oxytec AG feasibility studies. Your job is to: (1) Distinguish between insurmountable barriers and solvable engineering challenges, (2) Consolidate mitigation strategies from technical subagents into actionable recommendations, (3) Provide realistic, evidence-based risk probabilities. Focus on enabling informed decisions with clear paths forward. Return only valid JSON.",
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
