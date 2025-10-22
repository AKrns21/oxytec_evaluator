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
        planning_prompt = f"""You are the Coordinator for oxytec AG feasibility studies. Oxytec specializes in NTP, UV/ozone, and air scrubbers for industrial exhaust-air purification.

**Extracted Facts:**
```json
{extracted_facts_json}
```

**Your job:** Create 3-8 specialized subagent tasks to analyze this inquiry.

**Subagent Structure (3 fields required):**

1. **task** (string): Multi-paragraph description with sections:
   - Subagent: [Name & Role]
   - Objective: Narrow scope
   - Questions to answer: 3-6 explicit questions
   - Method hints: Quality criteria, calculation methods, sources to cite
   - Deliverables: Structured outputs (tables, lists, classifications)
   - Dependencies: INDEPENDENT (default) or specify dependencies
   - Tools needed: List tool names or state "none"

2. **relevant_content** (JSON string): Subset of extracted_facts this subagent needs (e.g., "{{\\"pollutant_characterization\\": {{...}}, \\"process_parameters\\": {{...}}}}")

3. **tools** (array): ["oxytec_knowledge_search"], ["product_database"], ["web_search"], ["oxytec_knowledge_search", "web_search"], or []

**Task Description Template:**
```
Subagent: [Name]

Objective: [Narrow focus - what this agent investigates]

Questions to answer:
- [Question 1 with specifics: units, methods, confidence levels]
- [Question 2 with deliverable format: table, classification, range]
- [Question 3 with risk/uncertainty requirements]

Method hints:
- [Calculation methods with standard values to use]
- [Databases/sources to cite: PubChem, NIST, ISO standards]
- [Risk classification: CRITICAL (>80%), HIGH (30-80%), MEDIUM (10-30%), LOW (<10%)]
- [Uncertainty quantification: ±X% with justification]
- [Mitigation requirement: propose solutions for each challenge]

Deliverables:
- [Table/list format with columns specified]
- [Risk classification table: Challenge, Severity, Probability, Mitigation]
- [Prioritized recommendations with cost/time estimates]

Dependencies: INDEPENDENT

Tools needed: [list tools or "none"]
```

**CRITICAL MANDATES:**

**A. CUSTOMER-SPECIFIC QUESTIONS (CONDITIONAL - HIGH PRIORITY)**
IF extracted_facts contains "customer_specific_questions" array with ≥1 question:
- **MANDATORY**: Create a "Customer Question Response Specialist" subagent FIRST in the list
- This subagent MUST:
  • Quote each customer question verbatim in the task description
  • Provide direct, numbered answers to each question
  • Reference customer's existing test/operational experience
  • Cross-reference findings from other subagents (VOC analysis, technology screening)
  • Use tools: ["oxytec_knowledge_search", "web_search"] for research
  • Deliverable format: Numbered responses (1-2 paragraphs each) with YES/NO/PARTIALLY stance
- Task structure:
  ```
  Subagent: Customer-Specific Question Response Specialist

  Objective: Provide direct, evidence-based answers to the customer's explicit questions about their system and testing experience.

  Customer Questions (verbatim):
  1. "[Question 1 text from customer_specific_questions[0].question_text]"
  2. "[Question 2 text from customer_specific_questions[1].question_text]"
  [... etc for all questions]

  Context: [Summarize context from customer_specific_questions[].context]

  Questions to answer:
  - For Question 1: [Specific analysis required - root cause, comparison, recommendation]
  - For Question 2: [Specific analysis required]
  [... etc]

  Method hints:
  - Use oxytec_knowledge_search for technology performance comparisons
  - Use web_search for chemical mechanism literature (e.g., ozone oxidation by-products)
  - Reference VOC Analysis subagent findings for compound-specific behavior
  - Reference Technology Screening subagent for technology pros/cons
  - Provide clear YES/NO/PARTIALLY answers with technical justification
  - Quantify recommendations with cost ranges and feasibility ratings

  Deliverables:
  - Numbered response to each customer question (1-2 paragraphs each)
  - For root_cause questions: Root cause analysis table with Factor | Likelihood (%) | Evidence | Mitigation
  - For recommendation_request questions: Recommendation table with Option | Pros | Cons | Cost Range | Feasibility
  - For technical_comparison questions: Comparison table with Technology | Performance | Cost | Complexity | Recommendation

  Dependencies: INDEPENDENT (but findings will be referenced by RISK ASSESSOR)

  Tools needed: oxytec_knowledge_search, web_search
  ```

**B. TECHNOLOGY SCREENING (REQUIRED)**
ALWAYS create a "Technology Screening" subagent that MUST:
- Use **oxytec_knowledge_search** to query technology knowledge base
- Compare NTP, UV/ozone, scrubbers, and hybrids quantitatively
- Provide ranked shortlist with efficiency, energy, CAPEX, footprint comparisons
- Task MUST include: "Tools needed: oxytec_knowledge_search" or "Tools needed: oxytec_knowledge_search, web_search"

**C. RISK CLASSIFICATION**
All subagents MUST classify risks as:
- CRITICAL (>80%): Project-killing factors (carcinogens, technical impossibilities)
- HIGH (30-80%): Significant challenges requiring mitigation
- MEDIUM (10-30%): Standard engineering challenges with known solutions
- LOW (<10%): Minor concerns manageable with routine measures

**C. MITIGATION STRATEGIES**
For each identified challenge, subagents MUST propose:
- Specific solution (equipment, process change, testing)
- Cost estimate (€X k/M) and timeline (days/weeks)
- Risk reduction impact (X% → Y%)

**D. ATEX CONTEXT** ⚠️
If creating Safety/ATEX subagent:
- Oxytec installs equipment OUTSIDE ATEX zones (standard practice)
- LEL calculations determine zone classification
- ATEX is a DESIGN CONSTRAINT, not usually a project blocker
- Risk classification: Usually MEDIUM or LOW unless client requires in-zone installation

**Tool Selection:**
- `oxytec_knowledge_search` - Oxytec technology knowledge (**REQUIRED for technology screening**)
- `product_database` - Oxytec product catalog/equipment sizing
- `web_search` - External research (literature, standards, benchmarks)
- `[]` - No tools (pure analytical tasks)

**Common Subagent Types:**
1. Pollutant Analysis (reactivity, by-products, challenges) - tools: ["web_search"]
2. Technology Screening (NTP/UV/scrubbers comparison) - tools: ["oxytec_knowledge_search", "web_search"] **REQUIRED**
3. Flow/Mass Balance (Nm3/h conversion, removal loads, GHSV) - tools: ["product_database"] or []
4. Safety/ATEX (LEL, zone classification) - tools: ["web_search"] or []
5. Economic Analysis (CAPEX/OPEX estimates) - tools: ["product_database"] **CRITICAL: Costs ONLY from product_database tool with actual pricing. NEVER estimate/generate costs.**
6. Regulatory Compliance (TA Luft, IED BAT) - tools: ["web_search"]

**Planning Strategy:**
- Maximize parallelism - default to INDEPENDENT dependencies
- Pass ONLY relevant JSON sections to each subagent (not entire extracted_facts)
- Be extremely prescriptive - specify units, methods, deliverable formats
- Balance technical rigor - assess BOTH challenges AND opportunities
- Focus on quantified uncertainty and mitigation feasibility

**CRITICAL COST ESTIMATION RULE:**
Subagents MUST NOT generate, estimate, or hallucinate cost values (CAPEX/OPEX/€ amounts).
Cost information ONLY permitted when:
1. Retrieved from product_database tool with actual product pricing
2. Explicitly marked as "from product database: [product_name] - €X"
If no database pricing available: Use "Cost TBD - requires product selection and quotation"

**OUTPUT JSON (no markdown blocks):**

{{
  "subagents": [
    {{
      "task": "Subagent: [Name]\\n\\nObjective: ...\\n\\nQuestions to answer:\\n- ...\\n\\nMethod hints:\\n- ...\\n\\nDeliverables:\\n- ...\\n\\nDependencies: INDEPENDENT\\n\\nTools needed: ...",
      "relevant_content": "{{\\"field\\": \\"value\\", ...}}",
      "tools": ["tool_name"]
    }}
  ],
  "reasoning": "Brief planning strategy (min 50 chars)"
}}

**Validation:**
- 3-10 subagents (min: 3, max: 10)
- Each "task": 10-12000 characters
- Each "relevant_content": Non-empty JSON string
- Return ONLY valid JSON, no markdown formatting
"""

        # Execute planning with configured OpenAI model (gpt-mini by default)
        from app.config import settings
        from app.agents.validation import validate_planner_output
        from pydantic import ValidationError

        plan = await llm_service.execute_structured(
            prompt=planning_prompt,
            system_prompt="You are a strategic planning coordinator for critical feasibility assessments. Create comprehensive, risk-focused parallel execution plans. Return only valid JSON.",
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
