"""Validation utilities for EXTRACTOR evaluation."""

import re
from typing import Any, Dict, List, Tuple


VALID_UNIT_PATTERNS = {
    "flow": [r"^m3/h$", r"^Nm3/h$", r"^kg/h$", r"^l/min$"],
    "concentration": [
        r"^mg/Nm3$",
        r"^mg/m3$",
        r"^ppm$",
        r"^ppb$",
        r"^vol%$",
        r"^g/h$",
    ],
    "temperature": [r"^degC$", r"^K$", r"^F$"],
    "pressure": [r"^mbar$", r"^Pa$", r"^kPa$", r"^bar$", r"^atm$"],
}

INVALID_PATTERNS = [
    r"\^",  # Should not contain caret (m^3/h)
    r"°",  # Should not contain degree symbol
    r"³",  # Should not contain unicode superscript
    r"²",  # Should not contain unicode superscript
]


def validate_unit_format(unit: str, unit_type: str = None) -> bool:
    """
    Validate that unit follows allowed format conventions.

    Args:
        unit: Unit string to validate
        unit_type: Optional type hint (flow, concentration, temperature, pressure)

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(unit, str):
        return False

    # Check for invalid patterns
    for pattern in INVALID_PATTERNS:
        if re.search(pattern, unit):
            return False

    # If type is specified, check against valid patterns
    if unit_type and unit_type in VALID_UNIT_PATTERNS:
        patterns = VALID_UNIT_PATTERNS[unit_type]
        return any(re.match(pattern, unit) for pattern in patterns)

    return True


def validate_numeric_value(value: Any) -> bool:
    """Validate that value is a proper numeric type."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_json_schema(extraction: dict) -> Tuple[bool, List[str]]:
    """
    Validate that extraction follows expected JSON schema structure.

    Returns:
        (is_valid, list_of_errors)
    """
    errors = []

    required_top_level = [
        "pollutant_characterization",
        "process_parameters",
        "current_abatement_systems",
        "industry_and_process",
        "requirements_and_constraints",
        "site_conditions",
        "customer_knowledge_and_expectations",
        "customer_specific_questions",
        "timeline_and_project_phase",
        "data_quality_issues",
    ]

    for field in required_top_level:
        if field not in extraction:
            errors.append(f"Missing top-level field: {field}")

    # Validate nested structure
    if "process_parameters" in extraction:
        pp = extraction["process_parameters"]
        if "flow_rate" in pp and pp["flow_rate"]:
            fr = pp["flow_rate"]
            if "value" not in fr:
                errors.append("Missing process_parameters.flow_rate.value")
            if "unit" not in fr:
                errors.append("Missing process_parameters.flow_rate.unit")

    # Validate pollutant list structure
    if "pollutant_characterization" in extraction:
        pc = extraction["pollutant_characterization"]
        if "pollutant_list" in pc and isinstance(pc["pollutant_list"], list):
            for idx, pollutant in enumerate(pc["pollutant_list"]):
                if not isinstance(pollutant, dict):
                    errors.append(
                        f"pollutant_list[{idx}] is not a dict: {type(pollutant)}"
                    )
                    continue

                required_pollutant_fields = [
                    "name",
                    "concentration",
                    "concentration_unit",
                    "category",
                ]
                for field in required_pollutant_fields:
                    if field not in pollutant:
                        errors.append(f"pollutant_list[{idx}] missing field: {field}")

    # Validate customer questions structure
    if "customer_specific_questions" in extraction:
        questions = extraction["customer_specific_questions"]
        if not isinstance(questions, list):
            errors.append(
                f"customer_specific_questions should be list, got {type(questions)}"
            )
        else:
            for idx, question in enumerate(questions):
                required_q_fields = [
                    "question_text",
                    "question_type",
                    "priority",
                    "source_document",
                ]
                for field in required_q_fields:
                    if field not in question:
                        errors.append(
                            f"customer_specific_questions[{idx}] missing field: {field}"
                        )

                if "priority" in question and question["priority"] not in [
                    "HIGH",
                    "MEDIUM",
                    "LOW",
                ]:
                    errors.append(
                        f"customer_specific_questions[{idx}] has invalid priority: {question['priority']}"
                    )

    return len(errors) == 0, errors


def validate_extraction_completeness(extraction: dict) -> Dict[str, Any]:
    """
    Check completeness of extraction - how many fields are populated vs. null.

    Returns:
        {
            "total_fields": int,
            "populated_fields": int,
            "null_fields": int,
            "empty_string_fields": int,
            "empty_list_fields": int,
            "completeness_ratio": float  # 0.0 to 1.0
        }
    """

    def count_fields(obj, stats=None):
        if stats is None:
            stats = {
                "total": 0,
                "populated": 0,
                "null": 0,
                "empty_string": 0,
                "empty_list": 0,
            }

        if isinstance(obj, dict):
            for value in obj.values():
                count_fields(value, stats)
        elif isinstance(obj, list):
            stats["total"] += 1
            if len(obj) == 0:
                stats["empty_list"] += 1
            else:
                for item in obj:
                    count_fields(item, stats)
                stats["populated"] += 1
        else:
            stats["total"] += 1
            if obj is None:
                stats["null"] += 1
            elif isinstance(obj, str) and obj == "":
                stats["empty_string"] += 1
            else:
                stats["populated"] += 1

        return stats

    stats = count_fields(extraction)

    return {
        "total_fields": stats["total"],
        "populated_fields": stats["populated"],
        "null_fields": stats["null"],
        "empty_string_fields": stats["empty_string"],
        "empty_list_fields": stats["empty_list"],
        "completeness_ratio": (
            stats["populated"] / stats["total"] if stats["total"] > 0 else 0.0
        ),
    }
