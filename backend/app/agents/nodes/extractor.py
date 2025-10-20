"""EXTRACTOR agent node - extracts structured facts from documents."""

from typing import Any
from app.agents.state import GraphState
from app.services.llm_service import LLMService
from app.services.document_service import DocumentService
from app.utils.logger import get_logger

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

**Constraints:**
- Output only ONE valid JSON object following the schema below
- Do not add commentary, bullet points, or prose outside the JSON
- If a field is unknown use null or ""
- Always preserve original wording, units, decimal separators, and table structure
- For tables: include all rows/columns exactly as seen
- **CRITICAL**: Properly escape all special characters in JSON strings (replace curly quotes with straight quotes)

**CRITICAL: Flag data quality issues**
For each missing or anomalous parameter, add an entry to "data_quality_issues" array:
- Duplicate identifiers (CAS numbers, substance names)
- Unusual parameter ranges (e.g., very low/high temperatures, pressures)
- Missing critical parameters (humidity, oxygen content, particle load)
- Inconsistent units or incompatible values

Documents:
{combined_text}

Extract the following information (if available):

1. **Pollutant Characterization**:
   - List of pollutants with names, concentrations, and units
   - Pollutant categories: VOCs, odors, inorganic gases (NH₃, H₂S, SO₂, HCl, etc.), particulates, bioaerosols
   - Total pollutant load (TVOC, Total-C, odor units, etc.)
   - Any measurement data tables (preserve all rows/columns)
   - Chemical formulas and CAS numbers where available

2. **Process Parameters**:
   - Exhaust air flow rate (preserve exact units: m³/h, Nm³/h, kg/h, etc.)
   - Gas temperature (exact value and unit)
   - Pressure (exact value and unit; note if positive/negative)
   - Humidity/relative humidity/dew point
   - Oxygen content (if specified)
   - Particulate/aerosol load (if specified)
   - Operating schedule (continuous, batch, hours per day, seasonal)

3. **Current Abatement Systems** (if any):
   - Existing treatment technologies in place
   - Current removal efficiencies or outlet concentrations
   - Problems with existing systems (fouling, OPEX, compliance issues)
   - Maintenance schedules and costs

4. **Industry and Process Context**:
   - Industry sector (chemical, food, printing, coating, wastewater, etc.)
   - Specific processes generating exhaust air
   - Production volumes or capacity
   - Raw materials used (relevant to pollutant composition)

5. **Requirements & Constraints**:
   - Target removal efficiency (%) or outlet concentration limits
   - Regulatory requirements (TA Luft, IED BAT, local permits, emission limits)
   - Space constraints (footprint, height, weight limits)
   - Energy consumption limits or targets
   - Budget constraints (CAPEX/OPEX)
   - ATEX classification (if mentioned: Zone 0/1/2, explosive atmospheres)
   - Safety requirements (fire protection, corrosion resistance, etc.)

6. **Site Conditions**:
   - Available utilities (electricity voltage/phases, water, compressed air, steam)
   - Installation location (indoor/outdoor, rooftop, ground level)
   - Ambient conditions (temperature range, humidity, corrosive environment)
   - Access constraints

7. **Customer Knowledge & Expectations**:
   - Does customer mention oxytec, NTP, UV/ozone, or scrubbers explicitly?
   - What technologies is customer currently considering or has experience with?
   - Any previous quotes, pilots, or engagements mentioned?
   - Specific technology preferences or constraints stated?
   - Customer's technical sophistication level (if apparent from document style)

8. **Timeline & Project Phase**:
   - Project timeline or urgency
   - Current project phase (inquiry, feasibility, detailed design, tender)

9. **Data Quality Issues** (CRITICAL - always populate):
   - List all missing standard parameters (e.g., "Humidity not specified")
   - Flag anomalies (e.g., "Duplicate CAS 104-76-7 for different substances")
   - Note unusual values (e.g., "Gas temperature 10°C unusually low for industrial exhaust")
   - Estimate impact: CRITICAL (prevents sizing), HIGH (±30% uncertainty), MEDIUM (±10-20%), LOW (<10%)

Return ONLY a valid JSON object. Preserve all original wording, numbers, and units exactly as they appear.
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
