"""EXTRACTOR agent node - extracts structured facts from documents."""

from typing import Any
from app.agents.state import GraphState
from app.services.llm_service import LLMService
from app.services.document_service import DocumentService
from app.utils.logger import get_logger
from app.utils.extraction_quality_validator import validate_extracted_facts
from app.utils.substance_corrections import apply_substance_corrections
from app.agents.prompts import CARCINOGEN_DATABASE
from app.agents.prompts.versions import get_prompt_version
from app.config import settings
from app.models.database import AgentOutput
from app.db.session import AsyncSessionLocal

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


def clean_extracted_data(data: dict) -> dict:
    """
    Clean and normalize extracted data for consistency.

    - Adds % suffix to formulation_percentage values that lack it
    - Converts empty strings "" to null for optional fields
    - Ensures unit fields are present where appropriate

    Args:
        data: Extracted facts dictionary

    Returns:
        Cleaned data
    """
    # Clean pollutant list
    pollutant_char = data.get("pollutant_characterization", {})
    pollutant_list = pollutant_char.get("pollutant_list", [])

    for pollutant in pollutant_list:
        # Add % suffix to formulation_percentage if missing
        fp = pollutant.get("formulation_percentage")
        if fp and isinstance(fp, str) and fp.strip():
            # Check if it has %, if not add it
            if not fp.strip().endswith("%") and not fp.strip().endswith(" %"):
                pollutant["formulation_percentage"] = fp.strip() + " %"

    # Clean utilities - empty strings to null
    utilities = data.get("utilities_available", {})
    if utilities:
        for key in list(utilities.keys()):
            if utilities[key] == "":
                utilities[key] = None

    # Ensure unit fields exist where values exist
    proc_params = data.get("process_parameters", {})

    flow_rate = proc_params.get("flow_rate", {})
    if flow_rate and flow_rate.get("value") is not None and not flow_rate.get("unit"):
        flow_rate["unit"] = "m3/h"  # Default unit

    pressure = proc_params.get("pressure", {})
    if pressure and pressure.get("value") is not None and not pressure.get("unit"):
        pressure["unit"] = "hPa"  # Default unit

    # Particulate load
    particulate_load = proc_params.get("particulate_load")
    if isinstance(particulate_load, dict):
        if particulate_load.get("value") is not None and not particulate_load.get("unit"):
            particulate_load["unit"] = "mg/m3"

    return data


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

        # Load versioned prompt
        prompt_data = get_prompt_version("extractor", settings.extractor_prompt_version)
        prompt_template = prompt_data["PROMPT_TEMPLATE"]
        system_prompt = prompt_data["SYSTEM_PROMPT"]

        # Create extraction prompt from template
        extraction_prompt = prompt_template.format(
            CARCINOGEN_DATABASE=CARCINOGEN_DATABASE,
            combined_text=combined_text
        )

        # Execute extraction with configured OpenAI model (gpt-5 by default)
        extracted_facts = await llm_service.execute_structured(
            prompt=extraction_prompt,
            system_prompt=system_prompt,  # Use versioned system prompt
            response_format="json",
            temperature=settings.extractor_temperature,
            use_openai=True,
            openai_model=settings.extractor_model
        )

        # Post-process: Normalize units (safety net for LLM)
        extracted_facts = normalize_units(extracted_facts)

        # Clean and normalize data (% suffix, null instead of "", unit defaults)
        extracted_facts = clean_extracted_data(extracted_facts)

        # Apply known substance CAS corrections (before validation)
        extracted_facts = apply_substance_corrections(extracted_facts)

        # Run data quality validation checks
        extracted_facts = validate_extracted_facts(extracted_facts)

        logger.info(
            "extractor_completed",
            session_id=session_id,
            facts_extracted=bool(extracted_facts)
        )

        # Save agent output with prompt version to database
        try:
            async with AsyncSessionLocal() as db:
                agent_output = AgentOutput(
                    session_id=session_id,
                    agent_type="extractor",
                    output_type="facts",
                    content={
                        "extracted_facts": extracted_facts,
                        "rendered_prompt": extraction_prompt,
                        "system_prompt": system_prompt
                    },
                    prompt_version=settings.extractor_prompt_version
                )
                db.add(agent_output)
                await db.commit()
                logger.info("extractor_output_saved", session_id=session_id, prompt_version=settings.extractor_prompt_version)
        except Exception as db_error:
            logger.warning("extractor_output_save_failed", session_id=session_id, error=str(db_error))

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
