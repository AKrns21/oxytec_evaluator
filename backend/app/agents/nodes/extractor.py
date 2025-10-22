"""EXTRACTOR agent node - extracts structured facts from documents."""

from typing import Any
from app.agents.state import GraphState
from app.services.llm_service import LLMService
from app.services.document_service import DocumentService
from app.utils.logger import get_logger
from app.agents.prompts import CARCINOGEN_DATABASE

logger = get_logger(__name__)


def normalize_units(data: dict) -> dict:
    """
    Post-processing function to normalize Unicode units to ASCII format.

    This is a safety net in case the LLM doesn't follow unit normalization instructions.
    Converts: ³ → 3, ² → 2, ° → deg

    Args:
        data: Extracted facts dictionary

    Returns:
        Dictionary with normalized units
    """
    def normalize_string(s: Any) -> Any:
        """Recursively normalize strings in data structure."""
        if isinstance(s, str):
            # Normalize superscripts
            s = s.replace('³', '3')
            s = s.replace('²', '2')
            s = s.replace('°C', 'degC')
            s = s.replace('°F', 'degF')
            s = s.replace('°', 'deg')
            return s
        elif isinstance(s, dict):
            return {k: normalize_string(v) for k, v in s.items()}
        elif isinstance(s, list):
            return [normalize_string(item) for item in s]
        else:
            return s

    return normalize_string(data)


async def extractor_node(state: GraphState) -> dict[str, Any]:
    """
    EXTRACTOR node: Extract structured information from uploaded documents.

    This agent analyzes all uploaded documents and extracts key facts like:
    - VOC composition and concentrations
    - Flow rates and volumes
    - Temperature and pressure requirements
    - Industry type and specific requirements
    - Regulatory constraints

    Args:
        state: Current graph state

    Returns:
        Updated state with extracted_facts populated
    """

    session_id = state["session_id"]
    documents = state["documents"]

    logger.info(
        "extractor_started",
        session_id=session_id,
        num_documents=len(documents)
    )

    try:
        # Initialize services
        doc_service = DocumentService()
        llm_service = LLMService()

        # Extract text from all documents
        extracted_texts = []
        for doc in documents:
            text = await doc_service.extract_text(doc["file_path"], doc.get("mime_type"))
            extracted_texts.append({
                "filename": doc["filename"],
                "text": text
            })

        # Combine all texts for analysis
        combined_text = "\n\n---\n\n".join(
            f"Document: {item['filename']}\n{item['text']}"
            for item in extracted_texts
        )

        # Create extraction prompt
        extraction_prompt = f"""You are an agent responsible for extracting all explicit facts from industrial exhaust air treatment inquiry documents. These may include questionnaires, measurement reports, safety documents, permits, or process descriptions.

{CARCINOGEN_DATABASE}

Documents:
{combined_text}

Extract the following information into this EXACT JSON structure:

{{
  "pollutant_characterization": {{
    "pollutant_list": [
      {{
        "name": "string (substance name)",
        "cas_number": "string or null",
        "concentration": "number or null",
        "concentration_unit": "string (e.g., mg/Nm3, ppm)",
        "category": "string (VOC, odor, inorganic, particulate, bioaerosol)"
      }}
    ],
    "total_load": {{
      "tvoc": "number or null",
      "tvoc_unit": "string or null",
      "total_carbon": "number or null",
      "odor_units": "number or null"
    }},
    "measurement_tables": "string (preserve raw table text with all rows/columns)"
  }},
  "process_parameters": {{
    "flow_rate": {{
      "value": "number or null",
      "unit": "string (exact as written: m3/h, Nm3/h, kg/h)",
      "min_value": "number or null",
      "max_value": "number or null"
    }},
    "temperature": {{
      "value": "number or null",
      "unit": "string (exact as written: degC, K, F)"
    }},
    "pressure": {{
      "value": "number or null",
      "unit": "string (exact as written: mbar, Pa, bar)",
      "type": "string (positive, negative, atmospheric, or null)"
    }},
    "humidity": {{
      "value": "number or null",
      "unit": "string (%, g/m3, dew point degC)",
      "type": "string (relative, absolute, dew_point, or null)"
    }},
    "oxygen_content_percent": "number or null",
    "particulate_load": {{
      "value": "number or null",
      "unit": "string (mg/m3, g/h)"
    }},
    "operating_schedule": "string (continuous, batch, hours per day, seasonal, or null)"
  }},
  "current_abatement_systems": {{
    "technologies_in_place": ["string array (thermal oxidizer, scrubber, activated carbon, etc.)"],
    "removal_efficiencies": "string or null",
    "problems_reported": "string or null (fouling, high OPEX, compliance issues, etc.)",
    "maintenance_costs": "string or null"
  }},
  "industry_and_process": {{
    "industry_sector": "string (chemical, food, printing, coating, wastewater, etc.)",
    "specific_processes": "string (describe processes generating exhaust air)",
    "production_volumes": "string or null",
    "raw_materials": "string or null"
  }},
  "requirements_and_constraints": {{
    "target_removal_efficiency_percent": "number or null",
    "outlet_concentration_limit": {{
      "value": "number or null",
      "unit": "string (mg/Nm3, ppm)"
    }},
    "regulatory_requirements": "string (TA Luft, IED BAT, local permits, etc.)",
    "space_constraints": "string (footprint, height, weight limits)",
    "energy_consumption_limits": "string or null",
    "budget_constraints": {{
      "capex": "string or null",
      "opex": "string or null"
    }},
    "atex_classification": "string (Zone 0/1/2, explosive atmosphere details, or null)",
    "safety_requirements": "string (fire protection, corrosion resistance, etc.)"
  }},
  "site_conditions": {{
    "utilities_available": {{
      "electricity": "string (voltage, phases, e.g., 400V 3-phase)",
      "water": "string (pressure, quality, or null)",
      "compressed_air": "string (pressure, flow rate, or null)",
      "steam": "string (pressure, or null)"
    }},
    "installation_location": "string (indoor/outdoor, rooftop, ground level)",
    "ambient_conditions": {{
      "temperature_range": "string (e.g., -10 to 40 degC)",
      "humidity": "string or null",
      "corrosive_environment": "boolean or null"
    }},
    "access_constraints": "string or null"
  }},
  "customer_knowledge_and_expectations": {{
    "technologies_mentioned": ["string array (oxytec, NTP, UV/ozone, scrubbers, etc.)"],
    "technologies_currently_considering": ["string array"],
    "previous_experience": "string or null (quotes, pilots, engagements)",
    "technology_preferences": "string or null",
    "technical_sophistication": "string (high/medium/low/unknown based on document style)"
  }},
  "customer_specific_questions": [
    {{
      "question_text": "string (original question verbatim, including German wording)",
      "question_type": "technical_comparison | root_cause | recommendation_request | feasibility_check | performance_inquiry",
      "context": "string (paragraph/sentence before and after question for context)",
      "priority": "HIGH | MEDIUM | LOW",
      "source_document": "string (filename where question appears)"
    }}
  ],
  "timeline_and_project_phase": {{
    "timeline": "string or null (urgency, deadlines)",
    "project_phase": "string (inquiry, feasibility, detailed design, tender, or null)"
  }},
  "data_quality_issues": [
    {{
      "issue": "string (specific missing parameter or anomaly)",
      "severity": "string (CRITICAL, HIGH, MEDIUM, LOW)",
      "impact_description": "string (how this affects sizing/design uncertainty)",
      "examples": ["string array (specific anomalies: Duplicate CAS, unusual value, etc.)"]
    }}
  ]
}}

**CRITICAL FIELD MAPPING:**
- "pollutant_characterization" will be used by Chemical Analysis subagents
- "process_parameters" will be used by Flow/Mass Balance subagents
- "current_abatement_systems" will be used by Technology Screening subagents
- "requirements_and_constraints" will be used by Regulatory Compliance and Safety subagents
- "data_quality_issues" MUST always be populated (minimum: note what standard parameters are missing)

**JSON OUTPUT REQUIREMENTS (CRITICAL - MUST FOLLOW EXACTLY):**

1. Output MUST be valid JSON starting with {{ and ending with }} - no other characters allowed
2. Do NOT wrap JSON in markdown code blocks:
   ❌ WRONG: ```json\\n{{...}}\\n```
   ✅ CORRECT: {{...}}
3. Do NOT add explanatory text, commentary, or notes outside the JSON object
4. For missing data:
   - Use null for missing numbers/booleans
   - Use "" (empty string) for missing text where context matters
   - Use [] (empty array) for missing lists
5. Unit normalization and formatting:
   - **ALWAYS normalize Unicode superscripts to ASCII**: Convert ³ → 3, ² → 2, ° → deg
   - **ALWAYS use ASCII format for units**: m3/h (NOT m³/h), m2 (NOT m²), degC (NOT °C)
   - **When multiple unit formats exist in document** (e.g., both "m³/h" and "m3/h"), ALWAYS normalize to ASCII format (m3/h)
   - **Extract ALL process parameters when available**: pressure, humidity, temperature, oxygen - do NOT skip optional fields if data is present
   - Preserve original decimal separators (comma vs period)
   - Complete table structures with all rows/columns
6. Character escaping (RFC 8259):
   - Backslash: \\ → \\\\
   - Double quote: " → \\"
   - Newline: (line break) → \\n
   - Tab: (tab) → \\t
   - Replace curly quotes ""'' with straight quotes ""''
7. Validation: Your output will be parsed with json.loads() - it must not raise an exception

**EXAMPLE (abbreviated):**

INPUT DOCUMENTS:
"Document: VOC_Measurements.pdf
Flow rate: 5000 m³/h (also written as 3000-6000 m3/h range)
VOC concentration: Toluene 850 mg/Nm3, Ethyl acetate 420 mg/Nm3
Temperature: 45°C
Pressure: -5 mbar (negative)
Humidity: 60% RH
Note: Oxygen content not measured"

OUTPUT JSON:
{{
  "pollutant_characterization": {{
    "pollutant_list": [
      {{
        "name": "Toluene",
        "cas_number": null,
        "concentration": 850,
        "concentration_unit": "mg/Nm3",
        "category": "VOC"
      }},
      {{
        "name": "Ethyl acetate",
        "cas_number": null,
        "concentration": 420,
        "concentration_unit": "mg/Nm3",
        "category": "VOC"
      }}
    ],
    "total_load": {{
      "tvoc": 1270,
      "tvoc_unit": "mg/Nm3",
      "total_carbon": null,
      "odor_units": null
    }},
    "measurement_tables": ""
  }},
  "process_parameters": {{
    "flow_rate": {{
      "value": 5000,
      "unit": "m3/h",
      "min_value": 3000,
      "max_value": 6000
    }},
    "temperature": {{
      "value": 45,
      "unit": "degC"
    }},
    "humidity": {{
      "value": 60,
      "unit": "%",
      "type": "relative"
    }},
    "pressure": {{
      "value": -5,
      "unit": "mbar",
      "type": "negative"
    }},
    "oxygen_content_percent": null,
    "particulate_load": {{
      "value": null,
      "unit": null
    }},
    "operating_schedule": null
  }},
  "current_abatement_systems": {{
    "technologies_in_place": [],
    "removal_efficiencies": null,
    "problems_reported": null,
    "maintenance_costs": null
  }},
  "industry_and_process": {{
    "industry_sector": "unknown",
    "specific_processes": "",
    "production_volumes": null,
    "raw_materials": null
  }},
  "requirements_and_constraints": {{
    "target_removal_efficiency_percent": null,
    "outlet_concentration_limit": {{
      "value": null,
      "unit": null
    }},
    "regulatory_requirements": "",
    "space_constraints": "",
    "energy_consumption_limits": null,
    "budget_constraints": {{
      "capex": null,
      "opex": null
    }},
    "atex_classification": null,
    "safety_requirements": ""
  }},
  "site_conditions": {{
    "utilities_available": {{
      "electricity": null,
      "water": null,
      "compressed_air": null,
      "steam": null
    }},
    "installation_location": "",
    "ambient_conditions": {{
      "temperature_range": null,
      "humidity": null,
      "corrosive_environment": null
    }},
    "access_constraints": null
  }},
  "customer_knowledge_and_expectations": {{
    "technologies_mentioned": [],
    "technologies_currently_considering": [],
    "previous_experience": null,
    "technology_preferences": null,
    "technical_sophistication": "unknown"
  }},
  "timeline_and_project_phase": {{
    "timeline": null,
    "project_phase": null
  }},
  "data_quality_issues": [
    {{
      "issue": "Oxygen content not measured",
      "severity": "MEDIUM",
      "impact_description": "Affects LEL calculations and explosion protection assessment for thermal oxidation",
      "examples": ["Oxygen content not measured per document note"]
    }},
    {{
      "issue": "CAS numbers not provided for VOCs",
      "severity": "MEDIUM",
      "impact_description": "±10% uncertainty in reactivity assessment, requires database lookup",
      "examples": []
    }}
  ],
  "customer_specific_questions": []
}}

This example shows: (1) correct Unicode → ASCII unit normalization (m³/h → m3/h, °C → degC), (2) extraction of optional fields when available (pressure, humidity), (3) mixed format handling (both m³/h and m3/h normalized to m3/h), (4) null for missing numbers, (5) severity classification for data quality issues.

**CUSTOMER-SPECIFIC QUESTIONS DETECTION:**

You MUST scan all documents for explicit customer questions and capture them in the "customer_specific_questions" array. These questions require direct answers in the final feasibility report.

**DETECTION PATTERNS:**

1. **Explicit Question Markers (HIGH priority):**
   - German: "Frage:", "Fragen:", "?", "Kann Oxytec...", "Ist es möglich...", "Wäre es sinnvoll...", "Wie würde...", "Welche Technologie..."
   - English: "Question:", "Can you...", "Is it possible...", "Would it be...", "How would...", "Which technology..."
   - Numbered questions: "1.", "2.", "3." with question marks or explicit alternatives

2. **Comparative Questions (MEDIUM/HIGH priority):**
   - "oder" / "or" with alternatives: "Liegt es an X oder Y?"
   - "versus", "im Vergleich zu", "compared to"
   - Technology comparisons: "UV oder Ozon?", "NTP vs. thermal oxidizer"

3. **Implicit Questions from Uncertainty (MEDIUM priority):**
   - "Vermutung", "unklar", "nicht sicher", "suspicion", "unclear", "uncertain"
   - "Wir wissen nicht ob...", "We don't know if..."

4. **Request for Recommendations (HIGH priority):**
   - "Was empfehlen Sie...", "What do you recommend..."
   - "Sollten wir...", "Should we..."
   - "Brauchen wir...", "Do we need..."

**QUESTION CLASSIFICATION:**

- **technical_comparison**: Comparing technologies, approaches, or solutions ("UV oder Ozon?", "NTP vs. scrubber")
- **root_cause**: Diagnosing problems or failures ("Liegt es an X oder Y?", "Why is there odor?")
- **recommendation_request**: Seeking advice on approach ("Sollten wir Wäscher einsetzen?", "What do you recommend?")
- **feasibility_check**: Can something be done ("Ist NTP geeignet?", "Can this be treated?")
- **performance_inquiry**: Questions about efficiency, costs, or performance ("Wie hoch ist der Wirkungsgrad?")

**PRIORITY CLASSIFICATION:**

- **HIGH**: Explicit numbered questions, questions with "Frage:" label, multiple alternatives presented, questions directly impacting GO/NO-GO decision
- **MEDIUM**: Comparative questions, technology selection questions, questions about secondary concerns
- **LOW**: Clarification questions, questions about minor details

**EXAMPLE DETECTION (from ACO_input1.txt):**

INPUT TEXT:
"Im Rahmen der Tests wurden keine UV- sondern Ozonröhren eingesetzt und die Vermutung ist dass sich Aktivkohle-Ablagerungen und/oder benzoaldehyde bilden und dass es Geruch und rauch gibt. Frage: Liegt liegt es an den zusätzlichen Stoffen neben Styron oder an dass Ozonröhren eingesetzt wurden oder 3. wäre es sinnvoll einen Wäscher nach der UV-Anlage zu schalten oder ist NTP für die anderen Stoffe notwendig."

OUTPUT JSON:
{{
  "customer_specific_questions": [
    {{
      "question_text": "Liegt es an den zusätzlichen Stoffen neben Styron oder daran dass Ozonröhren eingesetzt wurden?",
      "question_type": "root_cause",
      "context": "Im Rahmen der Tests wurden keine UV- sondern Ozonröhren eingesetzt und die Vermutung ist dass sich Aktivkohle-Ablagerungen und/oder benzoaldehyde bilden und dass es Geruch und Rauch gibt.",
      "priority": "HIGH",
      "source_document": "ACO_input1.txt"
    }},
    {{
      "question_text": "Wäre es sinnvoll einen Wäscher nach der UV-Anlage zu schalten?",
      "question_type": "recommendation_request",
      "context": "Tests mit Ozonröhren zeigten Aktivkohle-Ablagerungen, Benzaldehydbildung, Geruch und Rauch. Kunde evaluiert zusätzliche Behandlungsstufen.",
      "priority": "HIGH",
      "source_document": "ACO_input1.txt"
    }},
    {{
      "question_text": "Ist NTP für die anderen Stoffe notwendig?",
      "question_type": "feasibility_check",
      "context": "Kunde testet aktuell Ozonröhren für Styron-Behandlung und fragt sich ob zusätzliche Stoffe neben Styron eine andere Technologie erfordern.",
      "priority": "HIGH",
      "source_document": "ACO_input1.txt"
    }}
  ]
}}

**IMPORTANT:**
- Capture questions VERBATIM in original language (German/English as written)
- If document contains NO explicit questions, use empty array: "customer_specific_questions": []
- DO NOT invent questions - only extract what customer explicitly asked
- Split multi-part questions into separate entries (as shown in example above)
- Context should provide 1-2 sentences of surrounding information

**CRITICAL CARCINOGEN & TOXICITY DETECTION:**

You MUST scan all pollutants and industry context against the carcinogen database above and flag in data_quality_issues:

**MANDATORY CHECKS:**
1. Check pollutant_list for ANY Group 1/2A carcinogens (formaldehyde, ethylene oxide, propylene oxide, benzene, acetaldehyde, etc.)
2. Check industry_sector for high-risk processes (surfactant production → ethylene/propylene oxide risk)
3. Check for oxidation of alcohols → formaldehyde/acetaldehyde formation risk
4. Check for H2S, benzene, or other highly toxic substances

**EXAMPLE CARCINOGEN FLAGGING:**

If document mentions "ethylene oxide" OR industry is "surfactant production" OR "ethoxylation":
```json
{{
  "issue": "CARCINOGEN: Ethylene oxide (Group 1 IARC) used in production process",
  "severity": "CRITICAL",
  "impact_description": "Carcinogenic substance requires special ATEX considerations, worker protection, and regulatory compliance beyond standard VOC treatment",
  "examples": ["Ethylene oxide mentioned in process description", "Surfactant ethoxylation process typical uses ETO"]
}}
```

If "alcohol oxidation" or "aldehyde" in VOC list:
```json
{{
  "issue": "CARCINOGEN RISK: Formaldehyde (Group 1 IARC) likely oxidation by-product from alcohols",
  "severity": "CRITICAL",
  "impact_description": "Alcohol oxidation produces formaldehyde (carcinogenic), requires catalytic post-treatment and strict emission monitoring",
  "examples": ["2-ethylhexanol, octanol, decanol in VOC list → formaldehyde formation expected"]
}}
```

If industry is "petroleum", "oil refining", "waste oil", "bilge", "sludge", "tank washings" OR VOCs described as "petroleum-derived":
```json
{{
  "issue": "CARCINOGEN RISK: Formaldehyde (Group 1 IARC) formation from petroleum VOC oxidation",
  "severity": "CRITICAL",
  "impact_description": "Petroleum products contain complex VOC mixtures (alcohols, aromatics, alkanes) that produce formaldehyde during NTP/UV/ozone oxidation. Requires catalytic post-treatment (KAT series) and continuous emission monitoring per TA Luft for carcinogenic substances.",
  "examples": ["Waste management of oily products (bilge, sludges, tank washings)", "VOCs from petroleum products → formaldehyde formation during oxidation"]
}}
```

Return ONLY the valid JSON object. Preserve all original wording, numbers, and units exactly as they appear.
"""

        # Execute extraction with configured OpenAI model (gpt-5 by default)
        from app.config import settings
        extracted_facts = await llm_service.execute_structured(
            prompt=extraction_prompt,
            system_prompt="You are an industrial exhaust air purification data extraction specialist. Extract information with absolute accuracy, preserving exact wording, units, and structure. Return only valid JSON.",
            response_format="json",
            temperature=settings.extractor_temperature,
            use_openai=True,
            openai_model=settings.extractor_model
        )

        # Post-process: Normalize units (safety net for LLM)
        extracted_facts = normalize_units(extracted_facts)

        logger.info(
            "extractor_completed",
            session_id=session_id,
            facts_extracted=bool(extracted_facts)
        )

        return {
            "extracted_facts": extracted_facts
        }

    except Exception as e:
        logger.error(
            "extractor_failed",
            session_id=session_id,
            error=str(e)
        )
        return {
            "extracted_facts": {},
            "errors": [f"Extraction failed: {str(e)}"]
        }
