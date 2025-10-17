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
        extraction_prompt = f"""You are an agent responsible for extracting all explicit facts from the user's documents regarding industrial exhaust air purification - including the measures currently implemented and the technologies employed (e.g., questionnaires, measurement reports, tables, time-series charts, safety documents). Your goal is to convert these facts into a structured JSON string for further processing.

**Constraints:**
- Output only ONE valid JSON object following the schema.
- Do not add commentary, bullet points, or prose.
- If a field is unknown use null or "".
- Always preserve original wording, units, decimal separators, and column/row structure.
- For tables: include all rows/columns exactly as seen.
- For charts: capture axis labels, ranges, tick marks, and qualitative patterns (never estimate missing numbers).
- For questionnaires: treat answers as factual entries, including explicit references to the source.
- **CRITICAL**: Properly escape all special characters in JSON strings. Replace curly quotes („ " " ") with straight quotes, escape backslashes and double quotes.

Documents:
{combined_text}

Extract the following information (if available):

1. **VOC Analysis**:
   - List of VOC compounds with names and concentrations (preserve exact units: ppm, mg/m³, etc.)
   - Total VOC concentration
   - Any particularly challenging compounds (halogenated, SVOC, etc.)
   - Any VOC-related tables or measurement data (include all rows/columns)

2. **Process Parameters**:
   - Flow rate (preserve exact units: m³/h, Nm³/h, etc.)
   - Temperature (preserve exact value and unit)
   - Pressure (preserve exact value and unit)
   - Humidity level if specified
   - Operating schedule (continuous, batch, hours/day, etc.)

3. **Current Abatement Measures/Technologies**:
   - Existing VOC treatment systems in place
   - Technologies employed (thermal oxidizer, scrubber, adsorption, etc.)
   - Performance of current systems
   - Limitations or problems with current setup

4. **Application Context**:
   - Industry type (printing, coating, chemical, etc.)
   - Process type (continuous, batch, etc.)
   - Specific processes generating VOCs

5. **Requirements & Constraints**:
   - Target removal efficiency (%)
   - Space constraints
   - Energy consumption targets or limits
   - Regulatory requirements (emissions limits, permits, etc.)
   - Budget constraints
   - ATEX/safety requirements

6. **Additional Information**:
   - Any special requirements
   - Timeline expectations
   - Existing infrastructure
   - Site conditions

Return ONLY the extracted facts as a valid JSON object. Preserve all original wording, numbers, and units exactly as they appear in the documents.
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
