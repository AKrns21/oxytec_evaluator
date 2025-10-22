"""Known substance CAS number corrections for common lab report errors.

This module contains mappings of commonly misidentified CAS numbers to their
correct values based on substance name. This helps correct systematic errors
in source documents (lab reports, SDSs) where CAS numbers may be mistyped.
"""

from typing import Dict, Tuple, Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Mapping of (substance_name_keyword, wrong_cas) -> correct_cas
# Key is lowercase substring match of substance name
KNOWN_CAS_CORRECTIONS: Dict[Tuple[str, str], str] = {
    # Ethylbenzene: Common typo in lab reports (100-61-4 -> 100-41-4)
    ("ethylbenzen", "100-61-4"): "100-41-4",
    ("ethylbenzene", "100-61-4"): "100-41-4",

    # Add more known corrections here as they are discovered
    # Format: (substance_name_keyword_lowercase, wrong_cas): correct_cas
}

# Alternative: Correct CAS numbers for common substances (for lookup)
SUBSTANCE_CAS_REGISTRY: Dict[str, str] = {
    "ethylbenzen": "100-41-4",
    "ethylbenzene": "100-41-4",
    "toluol": "108-88-3",
    "toluene": "108-88-3",
    "xylol": "1330-20-7",  # Mixture
    "xylene": "1330-20-7",
    "benzol": "71-43-2",
    "benzene": "71-43-2",
    "styrol": "100-42-5",
    "styrene": "100-42-5",
    "formaldehyd": "50-00-0",
    "formaldehyde": "50-00-0",
}


def correct_known_cas_errors(
    substance_name: str,
    cas_number: str
) -> Tuple[str, bool, Optional[str]]:
    """
    Correct known CAS number errors based on substance name.

    This function checks if a substance name + CAS combination is a known
    error and returns the correct CAS number if available.

    Args:
        substance_name: Name of the substance
        cas_number: CAS number extracted from document

    Returns:
        Tuple of (corrected_cas, was_corrected, reason)
        - corrected_cas: The CAS number (corrected if known error, original otherwise)
        - was_corrected: True if a correction was applied
        - reason: Explanation of the correction (or None)
    """
    if not substance_name or not cas_number:
        return (cas_number, False, None)

    # Normalize substance name for matching
    name_lower = substance_name.lower().strip()

    # Check direct corrections map
    for (keyword, wrong_cas), correct_cas in KNOWN_CAS_CORRECTIONS.items():
        if keyword in name_lower and cas_number == wrong_cas:
            logger.info(
                "known_cas_correction_applied",
                substance=substance_name,
                wrong_cas=wrong_cas,
                correct_cas=correct_cas
            )
            reason = f"Known error: {wrong_cas} is incorrect for {substance_name}, corrected to {correct_cas}"
            return (correct_cas, True, reason)

    # Check registry for substance name match (more aggressive)
    for substance_key, correct_cas in SUBSTANCE_CAS_REGISTRY.items():
        if substance_key in name_lower and cas_number != correct_cas:
            # Found a mismatch - substance name suggests different CAS
            logger.warning(
                "cas_mismatch_detected",
                substance=substance_name,
                extracted_cas=cas_number,
                expected_cas=correct_cas
            )
            # Don't auto-correct in this case, just flag it
            # (might be a variant or mixture)
            return (cas_number, False, None)

    # No correction needed
    return (cas_number, False, None)


def apply_substance_corrections(extracted_facts: Dict) -> Dict:
    """
    Apply known substance CAS corrections to all pollutants in extracted facts.

    This should be called after extraction but before validation.

    Args:
        extracted_facts: The extracted facts dictionary

    Returns:
        Modified extracted_facts with corrected CAS numbers
    """
    pollutant_char = extracted_facts.get("pollutant_characterization", {})
    pollutant_list = pollutant_char.get("pollutant_list", [])

    corrections_made = 0

    for pollutant in pollutant_list:
        name = pollutant.get("name")
        cas = pollutant.get("cas_number")

        if name and cas:
            corrected_cas, was_corrected, reason = correct_known_cas_errors(name, cas)

            if was_corrected:
                pollutant["cas_number"] = corrected_cas
                corrections_made += 1

                # Add to data quality issues
                if "data_quality_issues" not in extracted_facts:
                    extracted_facts["data_quality_issues"] = []

                extracted_facts["data_quality_issues"].append({
                    "issue": f"CAS number corrected for {name}",
                    "severity": "INFO",
                    "impact_description": f"Source document had wrong CAS {cas} for {name}, auto-corrected to {corrected_cas}",
                    "examples": [reason],
                    "recommendation": "Verify source document quality and consider updating lab report templates"
                })

    if corrections_made > 0:
        logger.info(
            "substance_corrections_applied",
            total_corrections=corrections_made
        )

    return extracted_facts
