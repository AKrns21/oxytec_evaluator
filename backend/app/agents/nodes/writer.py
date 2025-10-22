"""WRITER agent node - generates final feasibility report."""

from typing import Any
from app.agents.state import GraphState
from app.services.llm_service import LLMService
from app.utils.logger import get_logger
from app.agents.prompts import UNIT_FORMATTING_INSTRUCTIONS, POSITIVE_FACTORS_FILTER

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

        # Create report writing prompt - sees RISK ASSESSOR output + EXTRACTED FACTS for Ausgangslage
        writer_prompt = f"""You are the Writer Agent responsible for producing the final feasibility report in German for oxytec AG. Oxytec specialized in non-thermal plasma (NTP), UV/ozone and air scrubbing technologies for industrial exhaust-air purification. The purpose of the feasibility study is to determine whether it is worthwhile for oxytec to proceed with deeper engagement with a prospective customer and whether NTP, UV/ozone, exhaust air scrubbers, or a combination of these technologies can augment or replace the customer's current abatement setup.
{customer_questions_section_instructions}

Your role is to compile and synthesize the risk assessment into a structured, management-ready document that provides both realistic evaluation AND actionable recommendations. **Do not add your own analysis, do not invent information, and rely strictly on the provided data.**

**Extracted Facts (for Ausgangslage context only):**
```json
{json.dumps(extracted_facts, indent=2, ensure_ascii=False)}
```

**Risk Assessment Report:**
```json
{json.dumps(risk_assessment, indent=2, ensure_ascii=False)}
```

**DATA USAGE INSTRUCTIONS (CRITICAL - PREVENTS SCOPE CREEP):**

You are a SYNTHESIS and FORMATTING agent, NOT an analytical agent. Your role is to compile information from upstream agents into a structured German report. You MUST NOT:
- ❌ Perform new technical analysis or calculations
- ❌ Add information not present in the provided data
- ❌ Make assumptions about missing data
- ❌ Conduct literature research or reference external knowledge
- ❌ Invent specific values, concentrations, or performance data

**INPUT DATA SOURCES AND USAGE:**

1. **Extracted Facts** (`extracted_facts`):
   - **Purpose:** Describes the customer's current situation as documented in uploaded files
   - **Use for:** "Ausgangslage" subsection ONLY
   - **Include:** Industry sector, VOC compounds/concentrations, flow rates, current abatement measures, constraints
   - **Write as:** 2-3 sentence summary in continuous paragraph format (German)
   - **Do NOT use for:** Technology assessment, risk analysis, or recommendations (that's from risk assessment)

2. **Risk Assessment** (`risk_assessment`):
   - **Purpose:** Contains all analytical findings from subagents: technology selection, efficiency estimates, risks, mitigations, recommendations
   - **Use for:** ALL other sections:
     - "Bewertung" → Extract overall_risk_level and go_no_go_recommendation
     - "VOC-Zusammensetzung und Eignung" → Extract technology selection reasoning from technical_risks and mitigation strategies
     - "Positive Faktoren" → Extract favorable findings (look for LOW risks, successful mitigations, suitable parameters)
     - "Kritische Herausforderungen" → Extract CRITICAL and HIGH risks with severity
     - "Handlungsempfehlungen" → Extract critical_success_factors and mitigation_priorities (top 4-6 only)
   - **Synthesis rule:** Translate technical findings into professional German report language
   - **Do NOT:** Add your own risk assessments or expand on risks not mentioned
   - **COST REPORTING RESTRICTION:**
     • Include CAPEX/OPEX estimates ONLY if risk_assessment contains database-sourced costs (pattern: "€X (from product database: [product])")
     • If costs mention "Cost TBD" or "requires product selection", DO NOT convert to specific amounts
     • When no database-sourced costs found, add disclaimer: "Eine detaillierte Kostenabschätzung (CAPEX/OPEX) erfordert die Auswahl konkreter Produktkomponenten aus dem Oxytec-Katalog und eine detaillierte Angebotserstellung."

**VALIDATION CHECKLIST:**
Before submitting your report, verify:
- [ ] Ausgangslage contains ONLY facts from extracted_facts (no analysis)
- [ ] Bewertung directly maps from risk_assessment.go_no_go_recommendation (no new judgment)
- [ ] All technical claims in VOC-Zusammensetzung can be traced to risk_assessment content
- [ ] IF customer_specific_questions exists: "Beantwortung Ihrer spezifischen Fragen" section MUST be present after VOC section
- [ ] IF customer_specific_questions exists: Each question MUST have a direct answer with verbatim question text
- [ ] "Positive Faktoren" section ONLY included if genuine advantages with quantified benefits (€X or Y%) exist
- [ ] IF no genuine positive factors: Section completely omitted (no heading, no placeholder text)
- [ ] Kritische Herausforderungen are direct translations of risk items
- [ ] Handlungsempfehlungen are TOP 4-6 items from mitigation_priorities (not expanded or added to)
- [ ] No calculations, assumptions, or external knowledge added
- [ ] No cost estimates (CAPEX/OPEX/€X) included unless sourced from product database with attribution
- [ ] Cost disclaimer added if no database-sourced pricing available

**REPORTING STRUCTURE (must be followed exactly):**

**IMPORTANT: Do NOT include a main document title (# Machbarkeitsstudie). Start directly with the first section.**

## Zusammenfassung

### Ausgangslage

Provide a concise 2-3 sentence summary in German of the customer's current situation based on the uploaded documents. Write as continuous paragraph text (NOT bullet points). Mention: industry sector, key VOC compounds/concentrations, flow rates, current abatement measures (if any), and main challenges/requirements.

### Bewertung

Provide a concise 2-3 sentence assessment of overall feasibility in German as continuous paragraph text. Balance risk assessment with mitigation potential. End with a final line containing ONLY one of the following evaluations with its icon: **🟢 GUT GEEIGNET** | **🟡 MACHBAR** | **🔴 SCHWIERIG**

**CLASSIFICATION LOGIC (use risk_assessment fields):**

IF risk_assessment.go_no_go_recommendation == "GO":
  → **🟢 GUT GEEIGNET**
  (Translation: No critical risks, clear technical path, favorable economics)

IF risk_assessment.go_no_go_recommendation == "CONDITIONAL_GO":
  → **🟡 MACHBAR**
  (Translation: Manageable challenges with clear mitigation strategies, viable with action plan)

IF risk_assessment.go_no_go_recommendation == "NO_GO":
  → **🔴 SCHWIERIG**
  (Translation: Critical technical/economic barriers OR multiple high risks without solutions)

**ALTERNATIVE (if go_no_go_recommendation not available, use overall_risk_level):**

IF risk_assessment.overall_risk_level == "LOW":
  → **🟢 GUT GEEIGNET**

IF risk_assessment.overall_risk_level == "MEDIUM":
  → **🟡 MACHBAR**

IF risk_assessment.overall_risk_level in ["HIGH", "CRITICAL"]:
  → **🔴 SCHWIERIG**

**EXAMPLE OUTPUT:**
"Die VOC-Behandlung ist mit Oxytec-Technologie grundsätzlich machbar, erfordert jedoch ein zweistufiges Hybridsystem (alkalischer Vorwäscher + NTP-Reaktor) zur Handhabung der Schwefelsäurebildung. Die wirtschaftlichen Parameter sind bei moderaten CAPEX- und OPEX-Werten akzeptabel, jedoch sollten vor Angebotsabgabe die fehlenden Feuchtedaten erhoben werden.

**🟡 MACHBAR**"

## VOC-Zusammensetzung und Eignung

Present a technical evaluation in German of which oxytec technology (NTP, UV/ozone, exhaust air scrubbers, or combinations) is most suitable. Base this strictly on risk assessment findings.

**CRITICAL - TECHNOLOGY-AGNOSTIC POSITIONING:**
- Oxytec is technology-agnostic: We offer NTP, UV/ozone, scrubbers, and hybrid systems
- State explicitly which technology is MOST suitable based on pollutant characteristics
- If UV/ozone or scrubbers are better than NTP: **Clearly communicate this** (do not default to NTP)
- Justify technology selection with specific technical reasoning (reactivity, water solubility, LEL concerns, etc.)
- Mention if hybrid systems offer advantages (e.g., scrubber pre-treatment + NTP polishing)
- **INCLUDE SPECIFIC OXYTEC PRODUCT NAMES** when mentioned in risk assessment (e.g., CEA, CFA, CWA, CSA, KAT product families)
- **DO NOT include cost estimates (CAPEX/OPEX)** in this section unless sourced from product database

Write as 2-3 continuous paragraphs (NO separators between paragraphs):
- First paragraph: Which oxytec technology (NTP, UV/ozone, scrubber, or combination) is MOST suitable and why. Be explicit and technology-specific. **Include specific Oxytec product family names (CEA, CFA, CWA, CSA, KAT) if available in the risk assessment.**
- Second paragraph: Key chemical/physical considerations, expected treatment efficiency ranges, and any technology-specific advantages
- Third paragraph (if no database-sourced costs found): Add cost disclaimer: "Eine detaillierte Kostenabschätzung (CAPEX/OPEX) erfordert die Auswahl konkreter Produktkomponenten aus dem Oxytec-Katalog und eine detaillierte Angebotserstellung. Grobe Richtwerte können nach Produktspezifikation bereitgestellt werden."

---

**[CONDITIONAL SECTION - ONLY IF customer_specific_questions exists]**

## Beantwortung Ihrer spezifischen Fragen

**This section is MANDATORY if customer_specific_questions array contains ≥1 question.**

See detailed instructions in "MANDATORY SECTION: Beantwortung Ihrer spezifischen Fragen" above for format and requirements.

**Position:** IMMEDIATELY AFTER "## VOC-Zusammensetzung und Eignung" and BEFORE "## Positive Faktoren"

---

**[CONDITIONAL SECTION - ONLY IF genuine positive factors exist]**

## Positive Faktoren

**CRITICAL: This section should ONLY be included if you identify genuine, exceptional advantages with quantified benefits (€X savings or Y% measurable advantage).**

**MANDATORY PRE-CHECK:** Before including this section, verify that you have AT LEAST ONE advantage that meets BOTH criteria:
1. "Would an expert say 'ja sonst würden wir das ja auch nicht machen'?" → If YES, DO NOT INCLUDE THIS SECTION
2. "Does this include a quantified cost/performance benefit (€X, Y%, Z advantage)?" → If NO, DO NOT INCLUDE THIS SECTION

**IF NO GENUINE ADVANTAGES EXIST:** Skip this entire section (do not write "## Positive Faktoren" heading at all). Move directly from "## VOC-Zusammensetzung und Eignung" (or "## Beantwortung Ihrer spezifischen Fragen" if present) to "## Kritische Herausforderungen".

**IF 1-2 GENUINE ADVANTAGES EXIST:** Include the section with the advantages listed as bullet points with specific cost/benefit quantification.

{POSITIVE_FACTORS_FILTER}

**CRITICAL FILTERING INSTRUCTIONS FOR THIS SECTION:**

This section is the MOST COMMON SOURCE OF EXPERT CRITICISM. You MUST apply EXTREME filtering to avoid listing basic requirements.

**MANDATORY PRE-CHECK:** Before writing ANY positive factor, ask BOTH questions:
1. "Would an expert say 'ja sonst würden wir das ja auch nicht machen'?" → If YES, DELETE IT
2. "Does this include a quantified cost/performance benefit (€X, Y%, Z advantage)?" → If NO, DELETE IT

**FORBIDDEN PHRASES (these will trigger expert criticism - NEVER use):**
- ❌ "Kontinuierlicher Betrieb" / "Continuous operation" / "24/7 operation" / "Betriebszeit" / "Dauerbetrieb"
- ❌ "Volumenstrom liegt im Standardbereich" / "Flow rate in standard range" / "Volumenstrom geeignet"
- ❌ "Temperatur ist günstig" / "Temperature suitable" / "im Standardbereich" / "Temperatur reduziert"
- ❌ "Sauerstoffgehalt ausreichend" / "Oxygen content sufficient" / "O2-Gehalt geeignet"
- ❌ "Keine halogenierten VOCs" / "No halogenated VOCs" / "Halogen-frei"
- ❌ "Oxytec hat Erfahrung" / "Oxytec has experience" / "bewährte Technologie"
- ❌ "Kunde verfügt über Betriebserfahrung" / "Customer has operational experience" / "Betriebserfahrung seit" / "qualifiziertes Personal" / "Schulungsaufwand reduziert"
- ❌ "Keine ATEX-Probleme" / "No ATEX issues" / "ATEX-konform"
- ❌ "Lärmschutz erreichbar" / "Noise protection achievable"
- ❌ "Modulare Bauweise möglich" / "Modular design possible"
- ❌ "Kunde hat Infrastruktur" / "Customer has infrastructure" / "Utilities verfügbar"
- ❌ "Anlage läuft seit" / "Plant operating since" / "langjährige Erfahrung"

**EXTRACTION STRATEGY:**
Look ONLY for LOW-severity risks in risk_assessment.technical_risks that mention:
- **Existing technical infrastructure** that saves significant CAPEX: "Existing alkaline scrubber can be integrated (saves €150k vs new installation)"
- **Unusual chemical advantages** enabling cost reduction: "High VOC concentration (>1500 mg/Nm3) enables autothermal operation (€25k/year OPEX saving vs dilute streams)"
- **Waste heat recovery opportunities**: "Process waste heat at 180 degC can pre-heat gas stream (€20k/year energy saving)"
- **Existing emission monitoring**: "Site already has continuous emission monitoring system (€30k CAPEX saving, faster permit approval)"

**DO NOT consider these as positive factors:**
- ❌ Customer operational experience, qualified personnel, training capabilities
- ❌ Standard operating conditions (temperature, pressure, flow rate, oxygen content)
- ❌ Absence of problems (no halogens, no ATEX, no space constraints)
- ❌ Standard Oxytec capabilities (modular design, proven technology)
- ❌ Normal customer capabilities (utilities available, maintenance team)

**OUTPUT FORMAT:**
- **MOST COMMON (90% of cases):** Omit the entire "## Positive Faktoren" section (no heading, no content)
- **RARE (10% of cases):** Include section with 1-2 genuine advantages with exact €X or Y% quantification
- If you find 3+ factors → You're including basics, omit the entire section instead

**ACCEPTABLE EXAMPLES (rare - only with specific cost savings):**
- ✅ "Bestehende alkalische Wäsche kann integriert werden (Einsparung €150k CAPEX gegenüber Neuinstallation)"
- ✅ "Hohe VOC-Konzentration (1800 mg/Nm3) ermöglicht autotherme Betriebsweise mit geschätzten €25k/Jahr OPEX-Einsparung gegenüber verdünnten Strömen"
- ✅ "Vorhandene Abwärme aus Prozess (180 degC) kann Gasstrom vorheizen (€20k/Jahr Energieeinsparung)"

**UNACCEPTABLE EXAMPLES (will be criticized by experts):**
- ❌ "Kontinuierlicher Betrieb ermöglicht stabile Prozessführung"
- ❌ "Volumenstrom von 7.000 m³/h liegt im Standardbereich"
- ❌ "Temperatur von 100 degC ist für NTP-Behandlung günstig"
- ❌ "Sauerstoffgehalt von 10% ausreichend für Oxidationsprozesse"
- ❌ "Bestehende Betriebserfahrung seit 2013 reduziert Schulungsaufwand um 30%"
- ❌ "Kunde verfügt über qualifiziertes Personal"

**CRITICAL INSTRUCTION:** When in doubt, OMIT THE ENTIRE SECTION. It is BETTER to omit the section completely than to list a questionable factor. Most projects have 0 genuine positive factors - omitting the section is normal and acceptable.

**QUALITY GATE:** If you list ANY positive factor, ask yourself: "Does this save the customer €X or provide Y% measurable advantage compared to a typical project?" If the answer is unclear or "maybe" → OMIT THE ENTIRE SECTION.

**FORMAT:**
- **If 0 genuine factors:** OMIT the entire section (no "## Positive Faktoren" heading)
- **If 1-2 genuine factors with quantified benefits:** Include section with bullet list ("-" markers)

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

{UNIT_FORMATTING_INSTRUCTIONS}

**FORMATTING EXAMPLE (Case 1: No genuine positive factors - section omitted):**
```markdown
## Zusammenfassung

### Ausgangslage

Der Kunde aus der chemischen Industrie verarbeitet VOCs mit Konzentrationen von 500-1800 mg/Nm³ bei Volumenströmen von 3000 Nm³/h. Aktuell keine Abgasbehandlung vorhanden. Ziel ist Einhaltung der TA-Luft-Grenzwerte (<20 mg/Nm³).

### Bewertung

Die VOC-Behandlung ist mit NTP-Technologie technisch machbar, erfordert jedoch eine mehrstufige Lösung zur Handhabung der Schwefelsäurebildung. Die technische Umsetzbarkeit ist gegeben, jedoch sollten vor Angebotsabgabe die fehlenden Feuchtedaten erhoben werden.

**🟡 MACHBAR**

## VOC-Zusammensetzung und Eignung

NTP-Technologie ist für die vorliegenden VOCs grundsätzlich geeignet. Die Mischung aus Alkoholen und Aromaten lässt sich mit 90-95% Wirkungsgrad behandeln.
Die kritische Herausforderung liegt in der Schwefelsäurebildung durch SO₂-Oxidation. Ein alkalischer Vorwäscher ist technisch zwingend erforderlich. Die erwartete Gesamteffizienz des Hybridsystems liegt bei ≥99% TVOC-Abscheidung. Eine detaillierte Kostenabschätzung (CAPEX/OPEX) erfordert die Auswahl konkreter Produktkomponenten aus dem Oxytec-Katalog und eine detaillierte Angebotserstellung.

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

**FORMATTING EXAMPLE (Case 2: WITH genuine positive factors - section included):**
```markdown
## VOC-Zusammensetzung und Eignung

[... same as above ...]

## Positive Faktoren

- Bestehende alkalische Wäsche kann integriert werden (Einsparung €150k CAPEX gegenüber Neuinstallation)
- Hohe VOC-Konzentration (1800 mg/Nm3) ermöglicht autotherme Betriebsweise mit geschätzten €25k/Jahr OPEX-Einsparung

## Kritische Herausforderungen

[... continues ...]
```

**KEY POINT:** In Case 1 (most common), the "## Positive Faktoren" heading and section are COMPLETELY OMITTED. The report flows directly from "## VOC-Zusammensetzung und Eignung" to "## Kritische Herausforderungen". Only include the section when quantified benefits exist.

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
