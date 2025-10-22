"""Data quality validation for extracted facts from documents.

This module provides validation checks to ensure critical data is not missing
from extraction, particularly for Safety Data Sheets (SDS) Section 3.
"""

from typing import Dict, Any, List, Optional
from app.utils.logger import get_logger
from app.utils.cas_validator import validate_cas_checksum, validate_and_correct_cas

logger = get_logger(__name__)


def validate_sds_section3_presence(
    extracted_facts: Dict[str, Any],
    document_metadata: Optional[Dict[str, Any]] = None
) -> List[Dict[str, str]]:
    """
    Validate that Safety Data Sheet Section 3 (composition) data is present.

    SDS Section 3 contains product composition with component percentages.
    Missing this section means missing the main ingredients (often 10-100% of product).

    Args:
        extracted_facts: The extracted facts dictionary from extractor
        document_metadata: Optional metadata about source documents

    Returns:
        List of data quality issues found (empty if no issues)
    """
    issues = []

    # Check if we have pollutant characterization data
    pollutant_char = extracted_facts.get("pollutant_characterization", {})
    pollutant_list = pollutant_char.get("pollutant_list", [])

    if not pollutant_list:
        # No pollutants extracted at all - this is suspicious for SDS
        issues.append({
            "issue": "No composition data extracted",
            "severity": "CRITICAL",
            "impact_description": "SDS Section 3 (Zusammensetzung/Composition) appears to be completely missing. Cannot determine product ingredients or VOC content.",
            "examples": [],
            "recommendation": "Check if document contains 'ABSCHNITT 3' or 'SECTION 3: Zusammensetzung/Composition' table and re-extract"
        })
        return issues

    # Check if any components have formulation_percentage
    components_with_percentage = [
        p for p in pollutant_list
        if p.get("formulation_percentage")
    ]

    # Check total percentage coverage
    total_percentage = 0
    has_percentage_ranges = False

    for component in components_with_percentage:
        percentage_str = component.get("formulation_percentage", "")

        if not percentage_str:
            continue

        # Parse percentage (handle formats like "10-25%", "≥10 - <25", "≤3%", "40-60%")
        try:
            # Remove % and spaces
            clean_str = percentage_str.replace("%", "").replace(" ", "").strip()

            # Handle ranges (take midpoint)
            if "-" in clean_str or "–" in clean_str:
                has_percentage_ranges = True
                parts = clean_str.replace("–", "-").replace("≥", "").replace("<", "").split("-")
                if len(parts) == 2:
                    try:
                        lower = float(parts[0])
                        upper = float(parts[1])
                        midpoint = (lower + upper) / 2
                        total_percentage += midpoint
                    except ValueError:
                        pass
            # Handle "≤3%" or "<5%"
            elif "≤" in clean_str or "<" in clean_str:
                has_percentage_ranges = True
                num_str = clean_str.replace("≤", "").replace("<", "").strip()
                try:
                    # Use half of the upper limit as estimate
                    total_percentage += float(num_str) / 2
                except ValueError:
                    pass
            # Handle "≥10%"
            elif "≥" in clean_str or ">" in clean_str:
                has_percentage_ranges = True
                # Can't estimate total from lower bounds alone
                pass
            else:
                # Simple number
                try:
                    total_percentage += float(clean_str)
                except ValueError:
                    pass
        except Exception as e:
            logger.warning(
                "percentage_parse_error",
                component=component.get("name"),
                percentage_str=percentage_str,
                error=str(e)
            )

    # Validate percentage coverage
    if not components_with_percentage:
        issues.append({
            "issue": "No formulation percentages extracted from SDS Section 3",
            "severity": "CRITICAL",
            "impact_description": f"Found {len(pollutant_list)} components but NONE have formulation_percentage. This suggests SDS Section 3 composition table was not extracted. Cannot determine product composition or calculate emissions.",
            "examples": [p.get("name", "Unknown") for p in pollutant_list[:3]],
            "recommendation": "Verify 'ABSCHNITT 3: Zusammensetzung/Angaben zu Bestandteilen' table was extracted. Look for percentage columns (%, ≥10 - <25, etc.)"
        })
    elif total_percentage < 5:
        issues.append({
            "issue": "Extracted formulation percentages sum to very low value",
            "severity": "HIGH",
            "impact_description": f"Found {len(components_with_percentage)} components with percentages totaling only ~{total_percentage:.1f}%. Major components (typically 10-100%) appear to be missing from extraction.",
            "examples": [
                f"{p.get('name')}: {p.get('formulation_percentage')}"
                for p in components_with_percentage[:5]
            ],
            "recommendation": "Check if main product ingredients from SDS Section 3 were missed. Look for components with percentages >10%."
        })
    elif total_percentage < 50 and not has_percentage_ranges:
        issues.append({
            "issue": "Formulation percentages sum to less than 50%",
            "severity": "MEDIUM",
            "impact_description": f"Extracted components total ~{total_percentage:.1f}%. Some major components may be missing, or components have percentage ranges that can't be summed reliably.",
            "examples": [
                f"{p.get('name')}: {p.get('formulation_percentage')}"
                for p in components_with_percentage[:5]
            ],
            "recommendation": "Verify all components from SDS Section 3 table were extracted"
        })

    return issues


def validate_cas_numbers(
    extracted_facts: Dict[str, Any]
) -> List[Dict[str, str]]:
    """
    Validate CAS Registry Numbers using checksum algorithm.

    Args:
        extracted_facts: The extracted facts dictionary from extractor

    Returns:
        List of data quality issues found (empty if no issues)
    """
    issues = []

    pollutant_char = extracted_facts.get("pollutant_characterization", {})
    pollutant_list = pollutant_char.get("pollutant_list", [])

    invalid_cas = []

    for component in pollutant_list:
        cas = component.get("cas_number")
        if not cas:
            continue

        name = component.get("name", "Unknown")

        # Validate CAS checksum
        formatted_cas, is_valid, suggestion = validate_and_correct_cas(cas)

        if not is_valid:
            invalid_cas.append({
                "name": name,
                "extracted_cas": cas,
                "suggestion": suggestion
            })

            logger.warning(
                "invalid_cas_checksum",
                component=name,
                cas=cas,
                suggestion=suggestion
            )

    if invalid_cas:
        issues.append({
            "issue": f"{len(invalid_cas)} invalid CAS numbers detected (failed checksum)",
            "severity": "MEDIUM",
            "impact_description": "CAS numbers failed checksum validation. This could indicate OCR errors, typos in source document, or substance misidentification.",
            "examples": [
                f"{item['name']}: {item['extracted_cas']}" +
                (f" → suggested: {item['suggestion']}" if item['suggestion'] else "")
                for item in invalid_cas[:5]
            ],
            "recommendation": "Verify CAS numbers against source document. Consider using suggestion if OCR error is likely."
        })

    return issues


def validate_extracted_facts(
    extracted_facts: Dict[str, Any],
    document_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run all data quality validation checks on extracted facts.

    This function runs multiple validation checks and appends any issues found
    to the data_quality_issues array in extracted_facts.

    Args:
        extracted_facts: The extracted facts dictionary from extractor
        document_metadata: Optional metadata about source documents

    Returns:
        Modified extracted_facts with additional data_quality_issues appended
    """
    all_issues = []

    # Run SDS Section 3 validation
    sds_issues = validate_sds_section3_presence(extracted_facts, document_metadata)
    all_issues.extend(sds_issues)

    # Run CAS number validation
    cas_issues = validate_cas_numbers(extracted_facts)
    all_issues.extend(cas_issues)

    # Append to existing data_quality_issues
    if "data_quality_issues" not in extracted_facts:
        extracted_facts["data_quality_issues"] = []

    extracted_facts["data_quality_issues"].extend(all_issues)

    # Log summary
    if all_issues:
        logger.warning(
            "data_quality_validation_complete",
            total_issues=len(all_issues),
            critical_issues=len([i for i in all_issues if i.get("severity") == "CRITICAL"]),
            high_issues=len([i for i in all_issues if i.get("severity") == "HIGH"]),
            medium_issues=len([i for i in all_issues if i.get("severity") == "MEDIUM"])
        )
    else:
        logger.info("data_quality_validation_complete", total_issues=0)

    return extracted_facts
