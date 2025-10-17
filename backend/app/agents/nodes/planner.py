"""PLANNER agent node - dynamically creates subagent execution plan."""

import json
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

        # Serialize extracted_facts to JSON string
        extracted_facts_json = json.dumps(extracted_facts, indent=2, ensure_ascii=False)

        # Create planning prompt - ONLY sees output of previous agent (EXTRACTOR)
        planning_prompt = f"""You are the Coordinator for feasibility studies conducted by oxytec AG. Oxytec specialized in non-thermal plasma (NTP), UV/ozone and air scrubbing technologies for industrial exhaust-air purification. The purpose of each study is to decide whether oxytec should proceed with deeper engagement with a prospective customer (e.g., pilot, PoC, proposal) and whether NTP, UV/ozone, exhaust air scrubbers, or a combination of these technologies can augment the customer's current abatement setup or fully replace it.

**Context:** You are given a JSON file compiled from documents the prospective customer provided to oxytec. It summarizes its current industrial exhaust-air situation (e.g., VOC composition, volume flows, operating schedule, existing abatement measures/technologies, constraints, safety/ATEX context) and may reference attached materials. Use this material as the basis for planning.

**Extracted Facts:**
```json
{extracted_facts_json}
```

**Your job:** Decompose the overall study into well-scoped subtasks and dispatch domain-specific subagents to perform the analysis. For each subagent, you must create a comprehensive task description and provide the exact JSON subset they need.

**CRITICAL: For each subagent, you must provide TWO fields:**

1. **task** (string): A comprehensive multi-paragraph task description that includes ALL of the following:
   - Subagent name/role (e.g., "Subagent: VOC Analysis Expert")
   - **Objective (narrow)**: Clear, focused objective emphasizing critical risk assessment
   - **Questions to answer (explicit)**: List specific, detailed questions the subagent must answer. Be prescriptive and thorough.
   - **Method hints / quality criteria**: Provide specific guidance on HOW to perform the analysis (e.g., "Use authoritative property databases like PubChem", "Provide conservative assessments", "Compare against industry benchmarks")
   - **Deliverables (concise outputs, machine-usable)**: Specify exact format of outputs (e.g., "Table of compounds with properties", "Ranked shortlist with justification")
   - **Dependencies / sequencing**: Note what can run in parallel vs what needs other results
   - **Tools needed** (if any): Specify which tools this subagent should use: "product_database" for searching Oxytec catalog, "web_search" for external research, or "none"

2. **relevant_content** (JSON string): Extract ONLY the specific JSON fields this subagent needs from the extracted_facts above. Pass them as a JSON string (not a list of field names). Do not alter values or structure.

**Examples of good task descriptions (showing variety):**

**Example 1: Chemical Analysis Agent (uses web_search tool)**
```
Subagent: VOC Composition & Reactivity Analyst

Objective (narrow): Analyze the VOC composition to identify challenging compounds, expected reactivity with NTP/UV/ozone systems, potential by-products, and measurement gaps. Classify challenges by severity and propose mitigation strategies for each.

Questions to answer (explicit):
- What are the representative compounds/groups from the TVOC list with relevant physico-chemical properties (boiling point, vapor pressure, water solubility, Henry's law constant, molecular weight)?
- Which compounds will react rapidly with ozone vs requiring OH radicals (from NTP)? Provide rate constants or relative reactivity rankings.
- What hazardous by-products are likely (formaldehyde, organic acids, secondary aerosols) and at what estimated concentrations?
- Are there CRITICAL challenges (>80% failure probability) that could prevent use of specific technologies (NTP/UV/ozone/scrubbers)? Or are challenges HIGH/MEDIUM/LOW severity?
- What critical measurements are missing (water vapor content, detailed speciation, particulate load) and how much uncertainty do they introduce?
- For each identified challenge, what specific mitigation strategies exist? (additional scrubbing, multi-stage treatment, material selection, etc.)

Method hints / quality criteria:
- Use authoritative databases (PubChem, NIST, ChemSpider) and cite sources per compound
- Group similar compounds and justify representative molecule selection with chemical reasoning
- Provide realistic by-product yield estimates (qualitative or semi-quantitative) based on industry benchmarks
- Classify each risk as CRITICAL (>80%), HIGH (30-80%), MEDIUM (10-30%), or LOW (<10%) with explicit justification
- Compare against literature on similar VOC mixtures (surfactant production, alcohol oxidation, etc.)
- Quantify uncertainties: "±20% due to unknown moisture" rather than "uncertain"
- For each challenge, propose specific mitigation approach with estimated feasibility

Deliverables (concise outputs, machine-usable):
- Structured table of representative compounds/groups with: CAS#, MW, BP, vapor pressure, water solubility, functional group, ozone rate constant, NTP reactivity (fast/medium/slow), expected by-products
- Risk classification table: Challenge description, Severity (CRITICAL/HIGH/MEDIUM/LOW), Probability (%), Mitigation strategy, Feasibility (Easy/Moderate/Difficult/Impossible)
- Prioritized list of measurement gaps ranked by impact on design uncertainty (CRITICAL/HIGH/MEDIUM/LOW)
- Recommended immediate actions: specific tests/measurements to reduce uncertainty

Dependencies / sequencing: Independent — can run immediately in parallel. No dependencies on other subagents. Results will inform technology selection and safety analysis.

Tools needed: web_search (for technical literature, property databases, and similar case studies)
```

**Example 2: Quantitative Engineering Agent (uses product_database tool)**
```
Subagent: Flow & Mass Balance Specialist

Objective (narrow): Convert provided mass flow (kg/h) envelope into standard volumetric flow (Nm3/h) with uncertainty bounds, calculate VOC removal loads (g/h and kg/h) for inlet scenarios and compliance target, and estimate gas hourly space velocity (GHSV) for reactor sizing.

Questions to answer (explicit):
- What are the Nm3/h flow rates for minimum, optimal, and maximum mass flows (kg/h)? Provide at least two calculation approaches (dry air density vs molar mass) and state which standard conditions you use (0°C or 20°C, 1.013 bar).
- For TVOC concentrations 2.9-1800 mg/Nm3, what are the mass removal loads in g/h and kg/h for each flow scenario?
- What is the required abatement capacity (g/h and kg/h) to achieve <20 mg/Nm3 target from maximum inlet concentration?
- What are the sensitivity bounds on these calculations (±X%) given missing data (moisture content, exact composition)?
- For a placeholder reactor volume of 1-2 m3, what are the estimated GHSV values (h^-1) and are they within typical ranges for NTP/UV reactors (cite literature values)?

Method hints / quality criteria:
- Use standard conditions explicitly (state which: 0°C/1.013 bar or 20°C/1.013 bar) and show calculations step-by-step
- For air density, use 1.204 kg/Nm3 at 20°C or 1.293 kg/Nm3 at 0°C; for molar mass use 28.97 g/mol
- Provide uncertainty bounds for each value (e.g., "±10-30% depending on moisture and exact composition")
- Compare calculated GHSV against literature values for similar applications (cite sources)
- Explicitly state what missing measurements (water vapor fraction, detailed speciation) would most affect accuracy and by how much

Deliverables (concise outputs, machine-usable):
- Table of Nm3/h estimates for min/opt/max mass flows with: assumptions stated, calculation method, uncertainty bounds
- Table of VOC removal loads (g/h and kg/h) for: min TVOC, typical TVOC, max TVOC at each flow rate, plus required removal to reach 20 mg/Nm3 target
- GHSV estimates with placeholder reactor volumes, comparison to literature benchmarks
- Short list of missing site data ranked by impact on calculation accuracy

Dependencies / sequencing: Independent — can run in parallel with chemical analysis and technology screening. Results feed into technology sizing and economic analysis tasks.

Tools needed: product_database (to check typical Oxytec reactor volumes for GHSV estimation)
```

**Key differences to note:**
- Example 1: Chemical/analytical focus, uses web_search for literature
- Example 2: Quantitative/engineering focus, uses product_database for equipment data
- Both: Highly specific questions, quantitative method hints, structured deliverables, explicit confidence/uncertainty
- Both: Clear dependencies and tools needed statement
- Both: **Require risk severity classification (CRITICAL/HIGH/MEDIUM/LOW) and mitigation strategies for each challenge**
- Both: **Balance technical rigor - assess both challenges AND opportunities, not just risks**

**Important rules:**
- Create 3-8 subagents depending on case complexity
- Maximize parallelism - mark tasks as independent when possible
- Extract ONLY relevant JSON sections for each subagent (don't pass entire extracted_facts)
- Be extremely prescriptive in task descriptions - subagents need detailed guidance
- Focus on **balanced technical evaluation**: identify both challenges AND opportunities with equal rigor
- **Require mitigation strategies**: Instruct subagents to propose specific solutions for each identified challenge
- **Require risk severity classification**: Subagents must classify risks as CRITICAL/HIGH/MEDIUM/LOW (not assume all risks are project-killing)
- Include specific quality criteria and deliverable formats

Common subagent types (adapt as needed):
1. VOC Analysis: Composition, concentrations, challenging compounds, destruction efficiency
2. Product Selection: Identify suitable Oxytec equipment (NTP, UV, ozone, scrubbers)
3. Flow/Mass Balance: Convert mass flows to volumetric flows, calculate removal loads
4. Technology Screening: Compare NTP/UV/ozone/scrubbers/thermal, flag incompatibilities
5. Safety/ATEX: Flammability risk, corrosion, materials of construction, safety controls
6. Process Integration: Sizing, utilities, footprint, site requirements
7. Economic Analysis: CAPEX/OPEX estimates, ROI, payback vs alternatives
8. Regulatory Compliance: Emissions limits, permits, ATEX zones

Return a JSON object with this EXACT structure:
{{
  "subagents": [
    {{
      "task": "Subagent: [Name]\\n\\nObjective (narrow): ...\\n\\nQuestions to answer:\\n- ...\\n\\nMethod hints:\\n- ...\\n\\nDeliverables:\\n- ...\\n\\nDependencies: ...\\n\\nTools needed: [tool name or 'none']",
      "relevant_content": "{{\\"field1\\": \\"value\\", \\"field2\\": ...}}"
    }}
  ],
  "reasoning": "Brief explanation of planning strategy emphasizing risk identification and parallel execution"
}}

Remember: The quality of subagent outputs depends entirely on the quality and detail of your task descriptions. Be thorough and prescriptive.
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
