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
    extracted_facts = state.get("extracted_facts", {})

    logger.info("writer_started", session_id=session_id)

    try:
        llm_service = LLMService()

        # Import json for serialization
        import json

        # Create report writing prompt - sees RISK ASSESSOR output + EXTRACTED FACTS for Ausgangslage
        writer_prompt = f"""You are the Writer Agent responsible for producing the final feasibility report in German for oxytec AG. Oxytec specialized in non-thermal plasma (NTP), UV/ozone and air scrubbing technologies for industrial exhaust-air purification. The purpose of the feasibility study is to determine whether it is worthwhile for oxytec to proceed with deeper engagement with a prospective customer and whether NTP, UV/ozone, exhaust air scrubbers, or a combination of these technologies can augment or replace the customer's current abatement setup.

Your role is to compile and synthesize the risk assessment into a structured, management-ready document that provides both realistic evaluation AND actionable recommendations. **Do not add your own analysis, do not invent information, and rely strictly on the provided data.**

**Extracted Facts (for Ausgangslage context only):**
```json
{json.dumps(extracted_facts, indent=2, ensure_ascii=False)}
```

**Risk Assessment Report:**
```json
{json.dumps(risk_assessment, indent=2, ensure_ascii=False)}
```

**DATA USAGE INSTRUCTIONS:**
- **Extracted Facts**: Use ONLY for the "Ausgangslage" subsection to summarize the customer's current situation (industry, VOC composition, flow rates, existing measures, requirements)
- **Risk Assessment**: Use for ALL other sections (Bewertung, VOC-Zusammensetzung, Positive Faktoren, Kritische Herausforderungen, Handlungsempfehlungen)

**RISK ASSESSMENT INTEGRATION:**
You MUST incorporate the Risk Assessment findings into your feasibility report by:
- Writing "Ausgangslage" based on extracted_facts (2-3 sentences about customer situation)
- Integrating risk classifications (CRITICAL/HIGH/MEDIUM/LOW) and probabilities
- Synthesizing top 4-6 action recommendations into brief Handlungsempfehlungen bullet list
- Adjusting feasibility classification based on risk severity and mitigation feasibility
- Adding specific risk quantifications to your "Kritische Herausforderungen" section

**REPORTING STRUCTURE (must be followed exactly):**

**IMPORTANT: Do NOT include a main document title (# Machbarkeitsstudie). Start directly with the first section.**

## Zusammenfassung

### Ausgangslage

Provide a concise 2-3 sentence summary in German of the customer's current situation based on the uploaded documents. Write as continuous paragraph text (NOT bullet points). Mention: industry sector, key VOC compounds/concentrations, flow rates, current abatement measures (if any), and main challenges/requirements.

### Bewertung

Provide a concise 2-3 sentence assessment of overall feasibility in German as continuous paragraph text. Balance risk assessment with mitigation potential. End with a final line containing ONLY one of the following evaluations with its icon: **🟢 GUT GEEIGNET** | **🟡 MACHBAR** | **🔴 SCHWIERIG**

- 🟢 GUT GEEIGNET: No CRITICAL risks, ≤1 HIGH risk with clear mitigation, favorable economics
- 🟡 MACHBAR: No CRITICAL risks, 2-3 HIGH risks with feasible mitigation strategies, viable economics
- 🔴 SCHWIERIG: ≥1 CRITICAL risk with no viable mitigation, OR ≥4 HIGH risks without clear solutions, OR Risk Assessor recommendation is STRONG REJECT/REJECT

## VOC-Zusammensetzung und Eignung

Present a technical evaluation in German of which oxytec technology (NTP, UV/ozone, exhaust air scrubbers, or combinations) is most suitable. Base this strictly on risk assessment findings.

**CRITICAL - TECHNOLOGY-AGNOSTIC POSITIONING:**
- Oxytec is technology-agnostic: We offer NTP, UV/ozone, scrubbers, and hybrid systems
- State explicitly which technology is MOST suitable based on pollutant characteristics
- If UV/ozone or scrubbers are better than NTP: **Clearly communicate this** (do not default to NTP)
- Justify technology selection with specific technical reasoning (reactivity, water solubility, LEL concerns, etc.)
- Mention if hybrid systems offer advantages (e.g., scrubber pre-treatment + NTP polishing)
- **INCLUDE SPECIFIC OXYTEC PRODUCT NAMES** when mentioned in risk assessment (e.g., CEA, CFA, CWA, CSA, KAT product families)

Write as 2-3 continuous paragraphs (NO separators between paragraphs):
- First paragraph: Which oxytec technology (NTP, UV/ozone, scrubber, or combination) is MOST suitable and why. Be explicit and technology-specific. **Include specific Oxytec product family names (CEA, CFA, CWA, CSA, KAT) if available in the risk assessment.**
- Second paragraph: Key chemical/physical considerations, expected treatment efficiency ranges, and any technology-specific advantages

## Positive Faktoren

**MUST be formatted as bullet list with "-" markers:**

- [Bullet point 1 - one sentence in German]
- [Bullet point 2 - one sentence in German]
- [Bullet point 3 - one sentence in German]
- [Bullet point 4 - one sentence in German, if applicable]
- [Bullet point 5 - one sentence in German, if applicable]

Synthesize 3-5 favorable aspects from risk assessment. Include technical advantages, suitable parameters, existing infrastructure. Be realistic - do not overstate positives.

## Kritische Herausforderungen

**MUST be formatted as bullet list with "-" markers:**

- [Challenge 1 with severity classification] (e.g., "Korrosionsrisiko durch Schwefelsäurebildung (HIGH, 60% Wahrscheinlichkeit)")
- [Challenge 2 with severity classification]
- [Challenge 3 with severity classification]
- [Challenge 4 with severity classification, if applicable]
- [Challenge 5 with severity classification, if applicable]

Synthesize 3-5 CRITICAL and HIGH risks from risk assessment. Include severity classification and probabilities in parentheses. Focus on challenges that require active mitigation.

## Handlungsempfehlungen

**MUST be formatted as bullet list with "-" markers (NO subsections):**

Synthesize the most important 4-6 action recommendations from Risk Assessment into concise bullet points:

- [Recommendation 1 - specific, actionable, e.g., "Vor-Ort-Besichtigung zur Klärung der Platzverhältnisse und Installation"]
- [Recommendation 2 - specific, actionable]
- [Recommendation 3 - specific, actionable]
- [Recommendation 4 - specific, actionable]
- [Recommendation 5 - specific, actionable, if applicable]
- [Recommendation 6 - specific, actionable, if applicable]

Include only Critical and High priority actions. Be specific and actionable. Focus on immediate next steps and key technical solutions.

**Important:**
- Write in German, using formal, technical, and precise language
- Use short, fact-based sentences
- Follow the structure exactly - include all sections with proper Markdown formatting
- **DO NOT include main title** - start directly with ## Zusammenfassung
- Use ## for section headers (bold and larger), ### for subsections
- **DO NOT use horizontal rules (---) between sections** - just leave blank lines for spacing
- Use bullet points (-) for lists in Positive Faktoren, Kritische Herausforderungen, and Handlungsempfehlungen
- Use **bold** for emphasis and ALWAYS include the appropriate icon emoji for feasibility ratings (🟢 GUT GEEIGNET / 🟡 MACHBAR / 🔴 SCHWIERIG)
- Write paragraph sections (Ausgangslage, Bewertung, VOC-Zusammensetzung) as continuous text WITHOUT blank lines between paragraphs
- Keep Handlungsempfehlungen brief (4-6 bullets total, no subsections)
- Balance realism (identify challenges) with solution-focus (provide paths forward)

**FORMATTING EXAMPLE:**
```markdown
## Zusammenfassung

### Ausgangslage

Der Kunde aus der chemischen Industrie verarbeitet VOCs mit Konzentrationen von 500-1800 mg/Nm³ bei Volumenströmen von 3000 Nm³/h. Aktuell keine Abgasbehandlung vorhanden. Ziel ist Einhaltung der TA-Luft-Grenzwerte (<20 mg/Nm³).

### Bewertung

Die VOC-Behandlung ist mit NTP-Technologie technisch machbar, erfordert jedoch eine mehrstufige Lösung zur Handhabung der Schwefelsäurebildung. Die wirtschaftlichen Parameter sind akzeptabel bei moderaten CAPEX- und OPEX-Werten.

**🟡 MACHBAR**

## VOC-Zusammensetzung und Eignung

NTP-Technologie ist für die vorliegenden VOCs grundsätzlich geeignet. Die Mischung aus Alkoholen und Aromaten lässt sich mit 90-95% Wirkungsgrad behandeln.
Die kritische Herausforderung liegt in der Schwefelsäurebildung durch SO₂-Oxidation. Ein alkalischer Vorwäscher ist technisch zwingend erforderlich. Die erwartete Gesamteffizienz des Hybridsystems liegt bei ≥99% TVOC-Abscheidung.

## Positive Faktoren

- Hohe VOC-Konzentrationen günstig für NTP-Behandlung ohne zusätzliche Energiekosten
- Kontinuierlicher Betrieb ermöglicht stabile Prozessführung und optimale Auslastung
- Keine halogenierten VOCs vorhanden, was Korrosionsrisiko reduziert
- Volumenstrom liegt im Standardbereich für industrielle NTP-Anlagen

## Kritische Herausforderungen

- Schwefelsäurebildung aus SO₂/SO₃ erfordert alkalischen Vorwäscher zur Korrosionsvermeidung (CRITICAL, 90% Wahrscheinlichkeit)
- Formaldehyd- und Acetaldehydbildung bei partieller Oxidation erfordert katalytische Nachbehandlung (HIGH, 60% Wahrscheinlichkeit)
- Fehlende Feuchtedaten erschweren exakte Auslegung des Wäschersystems (MEDIUM, 40% Unsicherheit)

## Handlungsempfehlungen

- Vor-Ort-Besichtigung zur Klärung der Platzverhältnisse und Installationsbedingungen durchführen
- Detaillierte VOC-Analyse inklusive Feuchtemessung zur Absicherung der Wäscherauslegung beauftragen
- Zweistufiges Hybridsystem (alkalischer Vorwäscher + NTP-Reaktor) als technische Lösung implementieren
- Pilotversuch zur Validierung der Aldehydbildung und Katalysator-Wirksamkeit durchführen
- Wartungsvertrag mit vierteljährlicher Elektrodeninspektion und pH-Überwachung etablieren
```

Generate the complete German feasibility report now following this exact structure and formatting.
"""

        # Execute report generation with configured Claude model (sonnet 4-5 by default)
        from app.config import settings
        final_report = await llm_service.execute_long_form(
            prompt=writer_prompt,
            system_prompt="You are a German technical writer for oxytec AG feasibility studies. Synthesize Risk Assessment findings into structured German reports with actionable recommendations. Never invent data. Balance realistic risk evaluation with solution-oriented approach. Use formal, precise language. Include comprehensive Handlungsempfehlungen section. Follow the exact report structure provided.",
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
