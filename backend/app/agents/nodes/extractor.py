"""EXTRACTOR agent node - extracts structured facts from documents."""

from typing import Any
from app.agents.state import GraphState
from app.services.llm_service import LLMService
from app.services.document_service import DocumentService
from app.utils.logger import get_logger
from app.agents.prompts import CARCINOGEN_DATABASE

logger = get_logger(__name__)


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
5. Preserve original formatting:
   - Exact units as written (don't convert m3/h to m^3/h)
   - Original decimal separators (comma vs period)
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
Flow rate: 5000 m3/h
VOC concentration: Toluene 850 mg/Nm3, Ethyl acetate 420 mg/Nm3
Temperature: 45 degC
Note: Humidity measurement pending"

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
      "min_value": null,
      "max_value": null
    }},
    "temperature": {{
      "value": 45,
      "unit": "degC"
    }},
    "humidity": {{
      "value": null,
      "unit": null,
      "type": null
    }},
    "pressure": {{
      "value": null,
      "unit": null,
      "type": null
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
      "issue": "Humidity not specified",
      "severity": "HIGH",
      "impact_description": "±20-30% uncertainty in scrubber sizing and condensation risk assessment",
      "examples": ["Measurement pending according to document"]
    }},
    {{
      "issue": "CAS numbers not provided for VOCs",
      "severity": "MEDIUM",
      "impact_description": "±10% uncertainty in reactivity assessment, requires database lookup",
      "examples": []
    }}
  ]
}}

This example shows: correct nesting, null for missing numbers, severity classification for data quality issues.

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
