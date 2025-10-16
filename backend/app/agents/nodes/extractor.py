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
        extraction_prompt = f"""You are an expert technical analyst for Oxytec, a company specializing in plasma-based VOC treatment systems.

Analyze the following documents from a potential customer inquiry and extract all relevant technical facts in a structured JSON format.

Documents:
{combined_text}

Extract the following information (if available):

1. **VOC Analysis**:
   - List of VOC compounds with names and concentrations (ppm or mg/m³)
   - Total VOC concentration
   - Any particularly challenging compounds (halogenated, SVOC, etc.)

2. **Process Parameters**:
   - Flow rate (m³/h or similar units)
   - Temperature (°C)
   - Pressure (bar or Pa)
   - Humidity level if specified

3. **Application Context**:
   - Industry type (printing, coating, chemical, etc.)
   - Process type (continuous, batch, etc.)
   - Current treatment method (if any)

4. **Requirements & Constraints**:
   - Target removal efficiency (%)
   - Space constraints
   - Energy consumption targets
   - Regulatory requirements
   - Budget constraints

5. **Additional Information**:
   - Any special requirements
   - Timeline expectations
   - Existing infrastructure

Return the extracted facts as a well-structured JSON object. If information is not available, use null for that field.
"""

        # Execute extraction with Claude
        extracted_facts = await llm_service.execute_structured(
            prompt=extraction_prompt,
            system_prompt="You are a technical data extraction expert. Extract information accurately and return valid JSON.",
            response_format="json"
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
