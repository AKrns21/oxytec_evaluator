"""WRITER agent node - generates final feasibility report."""

from typing import Any
from app.agents.state import GraphState
from app.services.llm_service import LLMService
from app.utils.logger import get_logger
from app.agents.prompts import UNIT_FORMATTING_INSTRUCTIONS, POSITIVE_FACTORS_FILTER
from app.agents.prompts.versions import get_prompt_version
from app.config import settings
from app.models.database import AgentOutput
from app.db.session import AsyncSessionLocal

logger = get_logger(__name__)


async def writer_node(state: GraphState) -> dict[str, Any]:
    """
    WRITER node: Generate comprehensive feasibility study report.

    This is the final agent that synthesizes all findings into a
    professional, well-structured feasibility report.

    Args:
        state: Current graph state with all previous results

    Returns:
        Updated state with final_report
    """

    session_id = state["session_id"]
    risk_assessment = state["risk_assessment"]
    extracted_facts = state.get("extracted_facts", {})

    logger.info("writer_started", session_id=session_id)

    try:
        llm_service = LLMService()

        # Import json for serialization
        import json

        # Check if customer questions exist
        customer_questions = extracted_facts.get("customer_specific_questions", [])
        has_customer_questions = len(customer_questions) > 0

        # Check if positive factors exist (look for LOW risk level factors in risk assessment)
        # We'll instruct the LLM to skip the section if no genuine advantages exist
        has_positive_factors = False
        if risk_assessment:
            technical_risks = risk_assessment.get("technical_risks", [])
            # Check if there are any LOW severity risks that could be positive factors
            # Note: This is a heuristic - the LLM will make the final decision
            has_positive_factors = any(
                risk.get("severity", "").upper() == "LOW"
                for risk in technical_risks
            )

        # Create conditional section instructions
        customer_questions_section_instructions = ""
        if has_customer_questions:
            questions_list = "\n".join([
                f"{i+1}. {q.get('question_text', 'N/A')}"
                for i, q in enumerate(customer_questions)
            ])
            customer_questions_section_instructions = f"""

**MANDATORY SECTION: Beantwortung Ihrer spezifischen Fragen**

The customer asked the following explicit questions:

{questions_list}

You MUST include a dedicated section titled "## Beantwortung Ihrer spezifischen Fragen" IMMEDIATELY AFTER "## VOC-Zusammensetzung und Eignung" and BEFORE "## Positive Faktoren".

**Section Requirements:**
1. Brief intro (1-2 sentences) acknowledging customer's test experience/context
2. For EACH question above, create a subsection:
   **Frage [N]: [Original question text verbatim]**

   [Direct answer starting with clear position: "Ja, ...", "Nein, ...", "Teilweise, ...", "Es hängt davon ab, ..."]

   [Technical reasoning with 2-3 paragraphs]

3. Extract answers from risk_assessment findings (look for "Customer Question Response Specialist" in subagent findings or relevant technical_risks)
4. Connect each answer to broader recommendations in Handlungsempfehlungen section
5. Use professional but direct tone - customer wants clear answers

**Example Format:**
```markdown
## Beantwortung Ihrer spezifischen Fragen

Sie haben in Ihren Tests mit Ozonröhren (anstelle von UV-Lampen) Aktivkohle-Ablagerungen, Benzaldehydbildung sowie Geruchs- und Rauchentwicklung beobachtet. Hierzu ergeben sich folgende Antworten:

**Frage 1: Liegt es an den zusätzlichen Stoffen neben Styrol oder daran, dass Ozonröhren eingesetzt wurden?**

Die Ursache liegt höchstwahrscheinlich an **beiden Faktoren**, wobei die Ozonröhren der Hauptfaktor sind. Ozon oxidiert Styrol zu Benzaldehyd (nachgewiesen in Ihrer Messung bei 0,8 mg/Nm³), was den charakteristischen Geruch erklärt. Die "zusätzlichen Stoffe" verstärken die Nebenproduktbildung...

[Continue with detailed technical explanation referencing risk_assessment findings]

**Frage 2: Wäre es sinnvoll, einen Wäscher nach der UV-Anlage zu schalten?**

Ja, ein alkalischer Wäscher nach der Oxidationsstufe ist **dringend empfohlen**. Er würde:
1. Benzaldehyd zu ~70-85% abscheiden (wasserlöslich bei pH >8)
2. Organische Säuren neutralisieren

[Continue with technical justification]

**Frage 3: Ist NTP für die anderen Stoffe notwendig?**

NTP ist für die nicht-Styrol-VOCs **nicht zwingend notwendig**, aber **vorteilhaft**...

[Continue with technical comparison]
```

**VALIDATION CHECKLIST FOR THIS SECTION:**
- [ ] Section appears AFTER "## VOC-Zusammensetzung und Eignung"
- [ ] Section appears BEFORE "## Positive Faktoren"
- [ ] Each customer question is quoted verbatim with **Frage [N]:** header
- [ ] Each answer starts with clear position (Ja/Nein/Teilweise/Es hängt davon ab)
- [ ] Answers reference specific findings from risk_assessment
- [ ] Technical depth is appropriate (2-3 paragraphs per question)
- [ ] Answers connect to Handlungsempfehlungen section
```
"""

        # Load versioned prompt
        prompt_data = get_prompt_version("writer", settings.writer_prompt_version)
        prompt_template = prompt_data["PROMPT_TEMPLATE"]
        system_prompt = prompt_data["SYSTEM_PROMPT"]

        # Create report writing prompt from template
        writer_prompt = prompt_template.format(
            customer_questions_section_instructions=customer_questions_section_instructions,
            extracted_facts_json=json.dumps(extracted_facts, indent=2, ensure_ascii=False),
            risk_assessment_json=json.dumps(risk_assessment, indent=2, ensure_ascii=False),
            POSITIVE_FACTORS_FILTER=POSITIVE_FACTORS_FILTER,
            UNIT_FORMATTING_INSTRUCTIONS=UNIT_FORMATTING_INSTRUCTIONS
        )

        # Execute report generation with configured Claude model (sonnet 4-5 by default)
        final_report = await llm_service.execute_long_form(
            prompt=writer_prompt,
            system_prompt=system_prompt,  # Use versioned system prompt
            temperature=settings.writer_temperature,
            model=settings.writer_model
        )

        logger.info(
            "writer_completed",
            session_id=session_id,
            report_length=len(final_report)
        )

        # Save agent output with prompt version to database
        try:
            async with AsyncSessionLocal() as db:
                agent_output = AgentOutput(
                    session_id=session_id,
                    agent_type="writer",
                    output_type="report",
                    content={
                        "final_report": final_report,
                        "report_length": len(final_report),
                        "rendered_prompt": writer_prompt,
                        "system_prompt": system_prompt
                    },
                    prompt_version=settings.writer_prompt_version
                )
                db.add(agent_output)
                await db.commit()
                logger.info("writer_output_saved", session_id=session_id, prompt_version=settings.writer_prompt_version)
        except Exception as db_error:
            logger.warning("writer_output_save_failed", session_id=session_id, error=str(db_error))

        return {
            "final_report": final_report
        }

    except Exception as e:
        logger.error(
            "writer_failed",
            session_id=session_id,
            error=str(e)
        )
        return {
            "final_report": f"# Report Generation Failed\n\nError: {str(e)}",
            "errors": [f"Report generation failed: {str(e)}"]
        }
