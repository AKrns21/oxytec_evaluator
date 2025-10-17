"""WRITER agent node - generates final feasibility report."""

from typing import Any
from app.agents.state import GraphState
from app.services.llm_service import LLMService
from app.utils.logger import get_logger

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

    logger.info("writer_started", session_id=session_id)

    try:
        llm_service = LLMService()

        # Create report writing prompt - ONLY sees output of previous agent (RISK ASSESSOR)
        writer_prompt = f"""You are the Writer Agent responsible for producing the final feasibility report in German for oxytec AG. Oxytec specialized in non-thermal plasma (NTP), UV/ozone and air scrubbing technologies for industrial exhaust-air purification. The purpose of the feasibility study is to determine whether it is worthwhile for oxytec to proceed with deeper engagement with a prospective customer and whether NTP, UV/ozone, exhaust air scrubbers, or a combination of these technologies can augment or replace the customer's current abatement setup.

Your role is to compile and synthesize the risk assessment into a structured, management-ready document. **Do not add your own analysis, do not invent information, and rely strictly on the risk assessment findings.**

**Risk Assessment Report:**
```json
{risk_assessment}
```

**RISK ASSESSMENT INTEGRATION:**
If a Risk Assessment report is available (as shown above), you MUST incorporate its findings into your feasibility report by:
- Integrating the assessor's quantified risk findings and failure probabilities
- Adjusting your feasibility classification if the assessor's evidence warrants a more conservative evaluation
- Adding specific risk quantifications to your "Kritische Herausforderungen" section
- Modifying your "Zusammenfassung" to reflect critical risk assessments
- Maintaining the report structure while ensuring the final assessment reflects documented project-killing risks
- **RESPECTING VETO POWER**: If the Risk Assessor's veto_flag is true, you MUST classify the project as SCHWIERIG regardless of other positive findings

**REPORTING STRUCTURE (must be followed exactly):**

## Zusammenfassung
- Provide a concise 2-3 sentence summary of overall feasibility in German
- Integrate quantified risk findings from the Risk Assessment
- End with a final line containing ONLY one of the following evaluations: **GUT GEEIGNET** | **MACHBAR** | **SCHWIERIG**
  - GUT GEEIGNET: Low risk (<30% failure probability), standard maintenance, economics favorable
  - MACHBAR: Moderate risk (30-50% failure probability), manageable challenges
  - SCHWIERIG: High risk (>50% failure probability), project-killing factors identified, or Risk Assessor VETO

## VOC-Zusammensetzung und Eignung
Present a technical evaluation in German of whether NTP, UV/ozone, exhaust air scrubbers, or a combination is suitable. Base this strictly on subagent findings.

## Positive Faktoren
- 3-4 bullet points, each max. one sentence in German
- Only synthesize what subagents identified as favorable
- Be realistic - do not overstate positives

## Kritische Herausforderungen
- 3-4 bullet points, each max. one sentence in German
- Only synthesize what subagents identified as risks or gaps
- **Include quantified risks from Risk Assessment** (probabilities, timelines, cost impacts)
- Highlight project-killing factors if identified

**Important:**
- Write in German, using formal, technical, and precise language
- Use short, fact-based sentences
- Do not invent or assume data - integrate only what subagents explicitly reported
- Follow the structure exactly - no additional sections
- Let critical risks drive the final evaluation (SCHWIERIG if high-probability failure scenarios exist)
- If Risk Assessor recommends "DO NOT PROCEED" or has veto_flag=true, classification must be SCHWIERIG

Generate the complete German feasibility report now following this exact structure.
"""

        # Execute report generation with configured Claude model (sonnet 4-5 by default)
        from app.config import settings
        final_report = await llm_service.execute_long_form(
            prompt=writer_prompt,
            system_prompt="You are a German technical writer for oxytec AG feasibility studies. Synthesize subagent findings into structured German reports. Never invent data. Respect Risk Assessor veto power. Use formal, precise language. Follow the exact report structure provided.",
            temperature=settings.writer_temperature,
            model=settings.writer_model
        )

        logger.info(
            "writer_completed",
            session_id=session_id,
            report_length=len(final_report)
        )

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
