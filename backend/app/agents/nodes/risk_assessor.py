"""RISK ASSESSOR agent node - evaluates technical and commercial risks."""

from typing import Any
from app.agents.state import GraphState
from app.services.llm_service import LLMService
from app.utils.logger import get_logger
from app.agents.prompts import POSITIVE_FACTORS_FILTER, OXYTEC_EXPERIENCE_CHECK

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
        risk_prompt = f"""You are the Risk Assessor, a specialized risk synthesis and strategic planning agent for oxytec AG feasibility studies.

{POSITIVE_FACTORS_FILTER}

{OXYTEC_EXPERIENCE_CHECK}

Oxytec specialized in non-thermal plasma (NTP), UV/ozone and air scrubbing technologies for industrial exhaust-air purification. Your purpose is to:
1. Synthesize and prioritize risks identified by technical subagents
2. Distinguish between true project-killing factors and manageable engineering challenges
3. Consolidate mitigation strategies into actionable recommendations
4. Provide realistic probability assessments based on documented evidence

CONTEXT: You are given an analysis from domain-specific subagents that summarizes the current industrial exhaust-air situation (e.g., VOC composition, volume flows, operating schedule, existing abatement measures/technologies, constraints, safety/ATEX context) and includes their proposed mitigation strategies. Use this material as the basis for your evaluation.

MISSION: Provide balanced risk synthesis that enables informed go/no-go decisions AND provides clear paths forward for manageable challenges.

**ATEX & EXPLOSIVE ATMOSPHERE CONTEXT:** ⚠️
Oxytec has NO ATEX-certified equipment. Standard practice: Install equipment OUTSIDE ATEX-classified zones.
- Installation outside ATEX zones is the ONLY option for Oxytec equipment
- This is a standard design constraint, NOT a critical risk (it's how we always work)
- ONLY mention ATEX in risks if:
  • Client explicitly requires in-zone installation AND cannot be convinced otherwise → HIGH risk (project may not be feasible)
  • OR ductwork routing outside zone is physically impossible → HIGH risk
  • OR concentration is >25% LEL at equipment location requiring extensive safety measures → CRITICAL risk
- Typical case: ATEX is NOT a risk at all - we simply install outside the zone (mention in recommendations if applicable)

**RISK CLASSIFICATION ATEX GUIDANCE:**
- NO RISK: Equipment can be installed outside zone (typical case - don't list as risk, just mention in recommendations)
- LOW (5-10%): Minor ductwork extension needed (<€30k)
- MEDIUM (20-30%): Some in-zone sensors/controls required; explosion relief needed
- HIGH (40-60%): Client insists on in-zone installation; may require project redesign or rejection
- CRITICAL (>80%): NEVER use for ATEX unless explosion risk makes project impossible

<new_findings>

{consolidated_findings}

</new_findings>

**RISK SYNTHESIS FRAMEWORK:** Evaluate risks using evidence-based severity classification:

**CARCINOGEN SEVERITY ESCALATION (MANDATORY):**
⚠️ If ANY risk involves Group 1 carcinogens (formaldehyde, ethylene oxide, propylene oxide, benzene, etc.):
1. **Auto-escalate severity**: HIGH → CRITICAL (minimum CRITICAL severity for Group 1 carcinogens)
2. **Add carcinogen label**: Include "(Group 1 Carcinogen - IARC)" in risk description
3. **Mention health impact**: Must explicitly state "carcinogenic substance requires special handling, worker protection, and regulatory compliance beyond standard VOC treatment"
4. **Formaldehyde specific**: If formaldehyde is mentioned, MUST include: "Formaldehyde ist krebserregend (Group 1 IARC) und erfordert katalytische Nachbehandlung und strenge Emissionsüberwachung"

Example carcinogen risk (MANDATORY format):
{{
  "category": "Safety/Chemical",
  "description": "Formaldehyde formation from alcohol oxidation (Group 1 Carcinogen - IARC). Carcinogenic substance requires special handling, worker protection, and regulatory compliance beyond standard VOC treatment.",
  "severity": "CRITICAL",
  "mitigation": "Install KAT catalytic post-treatment for aldehyde destruction (€28k CAPEX, 99.5% removal efficiency). Continuous emission monitoring required per TA Luft for carcinogenic substances."
}}

**CRITICAL RISKS (Project-killing factors):**
- ANY Group 1 carcinogen (formaldehyde, ethylene oxide, propylene oxide, benzene) → ALWAYS CRITICAL
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
- **Cost/timeline estimates**:
  • **CRITICAL RESTRICTION**: Include cost estimates ONLY if subagents sourced them from product_database tool
  • If subagent mentioned cost without database source, replace with: "Cost TBD - requires product selection"
  • Format database-sourced costs as: "€X (from product database: [product_name])"
  • If no pricing data available: "Detaillierte Kostenabschätzung erfordert Produktauswahl und Angebotserstellung"
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
  "executive_risk_summary": "2-3 sentence overview balancing key risks and opportunities (min 50 chars)",
  "risk_classification": {{
    "technical_risks": [
      {{
        "category": "string (e.g., Chemical, Equipment, Process, Safety)",
        "description": "string (min 10 chars, specific description of risk)",
        "severity": "CRITICAL|HIGH|MEDIUM|LOW",
        "mitigation": "string (specific mitigation strategy, can be empty for CRITICAL risks)"
      }}
    ],
    "commercial_risks": [
      {{
        "category": "string (e.g., Economic, Timeline, Competition, Regulatory)",
        "description": "string (min 10 chars)",
        "severity": "CRITICAL|HIGH|MEDIUM|LOW",
        "mitigation": "string (specific mitigation strategy)"
      }}
    ],
    "data_quality_risks": [
      {{
        "category": "string (e.g., Missing Measurements, Uncertainty, Assumptions)",
        "description": "string (min 10 chars)",
        "severity": "CRITICAL|HIGH|MEDIUM|LOW",
        "mitigation": "string (what data to collect, what tests to perform)"
      }}
    ]
  }},
  "overall_risk_level": "CRITICAL|HIGH|MEDIUM|LOW",
  "go_no_go_recommendation": "GO|CONDITIONAL_GO|NO_GO",
  "critical_success_factors": [
    "string (specific factor required for project success, e.g., 'Obtain detailed VOC speciation within 2 weeks')"
  ],
  "mitigation_priorities": [
    "string (prioritized action, e.g., '1. CRITICAL: Install alkaline scrubber to prevent acid corrosion')"
  ]
}}

**FIELD DEFINITIONS:**

- **executive_risk_summary**: Concise synthesis of overall risk profile with balanced view of challenges and opportunities
- **risk_classification**: Categorize risks into technical, commercial, and data quality domains
  - **technical_risks**: Engineering challenges, equipment limitations, process constraints
  - **commercial_risks**: Economic viability, timeline, competition, market factors
  - **data_quality_risks**: Missing measurements, uncertainties, assumptions affecting design
- **overall_risk_level**: Single aggregate assessment (roll-up of all risk categories)
  - CRITICAL: Multiple insurmountable barriers, >80% failure probability
  - HIGH: Significant challenges requiring major mitigation, 30-80% failure probability
  - MEDIUM: Standard engineering challenges with known solutions, 10-30% probability
  - LOW: Minor concerns manageable with routine measures, <10% probability
- **go_no_go_recommendation**:
  - GO: No CRITICAL risks, ≤1 HIGH risk with clear mitigation, proceed confidently
  - CONDITIONAL_GO: No CRITICAL risks, 2-3 HIGH risks with feasible mitigation, proceed with action plan
  - NO_GO: ≥1 CRITICAL risk OR ≥4 HIGH risks without clear mitigation paths
- **critical_success_factors**: Top 3-5 factors that MUST be addressed for project success
- **mitigation_priorities**: Ordered list of 5-8 priority actions synthesized from subagent recommendations

**ALIGNMENT WITH SUBAGENT FINDINGS:**
- Extract risk severity from subagent analyses (they classify as CRITICAL/HIGH/MEDIUM/LOW)
- Synthesize mitigation strategies from subagent recommendations
- Do NOT add new risks - only consolidate and prioritize what subagents identified
- Reference specific subagent findings as evidence for each risk

**JSON SCHEMA EXAMPLE:**

{{
  "executive_risk_summary": "The project presents MEDIUM overall risk with 2 HIGH challenges (corrosive by-product formation, missing humidity data) and several manageable MEDIUM factors. Both HIGH risks have clear technical mitigation paths (alkaline scrubber, on-site measurements). No project-killing CRITICAL risks identified. Economics appear viable with standard Oxytec hybrid system approach.",
  "risk_classification": {{
    "technical_risks": [
      {{
        "category": "Chemical",
        "description": "Sulfuric acid formation from SO2 oxidation will cause severe corrosion of downstream equipment within 6-12 months of operation",
        "severity": "HIGH",
        "mitigation": "Install CWA alkaline wet scrubber upstream of NTP reactor for SO2 removal (Cost TBD - requires product selection, proven solution in chemical industry)"
      }},
      {{
        "category": "Process",
        "description": "Formaldehyde and acetaldehyde formation from partial oxidation of alcohols requires catalytic post-treatment",
        "severity": "MEDIUM",
        "mitigation": "Add KAT catalytic reactor stage for aldehyde destruction (Cost TBD - requires product selection, 99.5% removal efficiency typical)"
      }}
    ],
    "commercial_risks": [
      {{
        "category": "Economic",
        "description": "OPEX for scrubber caustic consumption not yet quantified (customer has not budgeted for recurring costs)",
        "severity": "MEDIUM",
        "mitigation": "Calculate OPEX breakdown after product selection. Present 3-year TCO comparison vs thermal oxidizer alternative in proposal."
      }}
    ],
    "data_quality_risks": [
      {{
        "category": "Missing Measurements",
        "description": "Humidity content not specified - critical for scrubber sizing and condensation risk assessment (±30% uncertainty in water consumption and heat exchanger sizing)",
        "severity": "HIGH",
        "mitigation": "Request 24-hour humidity logging at exhaust point (customer can use portable datalogger, measurement cost minimal, 1 week turnaround)"
      }}
    ]
  }},
  "overall_risk_level": "MEDIUM",
  "go_no_go_recommendation": "CONDITIONAL_GO",
  "critical_success_factors": [
    "Obtain humidity measurements within 2 weeks (reduces scrubber sizing uncertainty from ±30% to ±10%)",
    "Confirm customer acceptance of scrubber OPEX for caustic consumption (to be calculated after product selection)",
    "Site visit to verify installation space for 2-stage system (scrubber + NTP + catalyst requires 8-10m length)"
  ],
  "mitigation_priorities": [
    "1. CRITICAL: Commission 24-hour humidity and temperature logging (minimal cost, 1 week) - Required for accurate sizing",
    "2. HIGH: Schedule site visit to measure available installation space and utility connections (1 day, travel costs only)",
    "3. HIGH: Prepare detailed OPEX breakdown for scrubber caustic consumption after product selection (2 days engineering time)",
    "4. MEDIUM: Request detailed VOC speciation if available from customer's existing monitoring (no cost, 3 days)",
    "5. MEDIUM: Conduct preliminary LEL calculations to confirm installation outside ATEX zone feasible (4 hours engineering)",
    "6. LOW: Review customer's maintenance capabilities for quarterly scrubber pH checks (phone call, 1 hour)"
  ]
}}

**UNIT FORMATTING**: Use plain ASCII for all units to avoid encoding issues:
- Write "h^-1" or "h-1" instead of "h⁻¹"
- Write "m^3" or "m3" instead of "m³"
- Write "degC" or just "C" instead of "°C"
- Avoid all Unicode superscripts, subscripts, and special characters

Remember: Oxytec's business success depends on realistic assessment AND finding viable paths forward. Distinguish between insurmountable barriers (REJECT) and solvable engineering challenges (PROCEED with mitigation plan).
"""

        # Execute risk assessment with configured OpenAI model (gpt-5 by default)
        from app.config import settings
        from app.agents.validation import validate_risk_assessor_output
        from pydantic import ValidationError

        risk_assessment = await llm_service.execute_structured(
            prompt=risk_prompt,
            system_prompt="You are a strategic risk synthesis specialist for oxytec AG feasibility studies. Your job is to: (1) Distinguish between insurmountable barriers and solvable engineering challenges, (2) Consolidate mitigation strategies from technical subagents into actionable recommendations, (3) Provide realistic, evidence-based risk probabilities. Focus on enabling informed decisions with clear paths forward. Return only valid JSON.",
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
