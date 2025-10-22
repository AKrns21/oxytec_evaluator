"""Quality thresholds for EXTRACTOR evaluation."""

# Layer 1: Document Parsing Quality Thresholds
LAYER1_THRESHOLDS = {
    "pdf_text_based": {
        "text_similarity": 0.95,  # Text-based PDFs should extract near-perfectly
        "encoding_quality": 1.0,  # No encoding issues allowed
        "completeness": 0.95,
    },
    "pdf_scanned": {
        "text_similarity": 0.85,  # OCR has inherent limitations
        "encoding_quality": 0.90,  # Some OCR artifacts acceptable
        "completeness": 0.80,
    },
    "xlsx": {
        "text_similarity": 0.90,  # Excel tables should extract well
        "encoding_quality": 1.0,
        "completeness": 0.92,
    },
    "docx": {
        "text_similarity": 0.93,
        "encoding_quality": 1.0,
        "completeness": 0.93,
    },
    "csv": {
        "text_similarity": 0.98,  # CSV is simplest format
        "encoding_quality": 1.0,
        "completeness": 0.98,
    },
}

# Layer 2: LLM Interpretation Quality Thresholds
LAYER2_THRESHOLDS = {
    "easy_cases": {
        "overall_accuracy": 0.95,
        "critical_field_accuracy": 1.0,  # All critical fields must be correct
        "unit_parsing_accuracy": 0.98,
        "value_parsing_accuracy": 0.98,
        "structure_accuracy": 0.95,
    },
    "medium_cases": {
        "overall_accuracy": 0.90,
        "critical_field_accuracy": 0.95,
        "unit_parsing_accuracy": 0.92,
        "value_parsing_accuracy": 0.92,
        "structure_accuracy": 0.90,
    },
    "hard_cases": {
        "overall_accuracy": 0.85,
        "critical_field_accuracy": 0.90,
        "unit_parsing_accuracy": 0.85,
        "value_parsing_accuracy": 0.85,
        "structure_accuracy": 0.85,
    },
    "very_hard_cases": {
        "overall_accuracy": 0.80,
        "critical_field_accuracy": 0.85,
        "unit_parsing_accuracy": 0.80,
        "value_parsing_accuracy": 0.80,
        "structure_accuracy": 0.80,
    },
}

# Combined (End-to-End) Thresholds
COMBINED_THRESHOLDS = {
    "overall_pipeline_quality": 0.90,  # Combined Layer 1 + Layer 2 must exceed 90%
    "max_parsing_errors": 2,  # Maximum acceptable Layer 1 errors per document
    "max_llm_errors": 3,  # Maximum acceptable Layer 2 errors per document
    "max_critical_field_errors": 0,  # Zero tolerance for critical field errors
}


def check_layer1_thresholds(results: dict, document_format: str) -> tuple[bool, list[str]]:
    """
    Check if Layer 1 results meet quality thresholds.

    Args:
        results: Dictionary containing text_similarity, encoding_quality, completeness
        document_format: Format type (pdf_text_based, pdf_scanned, xlsx, docx, csv)

    Returns:
        (passed, list_of_failures)
    """
    thresholds = LAYER1_THRESHOLDS.get(document_format, LAYER1_THRESHOLDS["pdf_text_based"])
    failures = []

    for metric, threshold in thresholds.items():
        if metric in results and results[metric] < threshold:
            failures.append(
                f"Layer 1 {metric}: {results[metric]:.2%} < {threshold:.2%} (threshold)"
            )

    return len(failures) == 0, failures


def check_layer2_thresholds(results: dict, difficulty: str = "medium_cases") -> tuple[bool, list[str]]:
    """
    Check if Layer 2 results meet quality thresholds.

    Args:
        results: Dictionary containing accuracy metrics
        difficulty: Difficulty level (easy_cases, medium_cases, hard_cases, very_hard_cases)

    Returns:
        (passed, list_of_failures)
    """
    thresholds = LAYER2_THRESHOLDS.get(difficulty, LAYER2_THRESHOLDS["medium_cases"])
    failures = []

    for metric, threshold in thresholds.items():
        if metric in results and results[metric] < threshold:
            failures.append(
                f"Layer 2 {metric}: {results[metric]:.2%} < {threshold:.2%} (threshold)"
            )

    return len(failures) == 0, failures


def check_combined_thresholds(diagnosis: dict, layer1_score: float, layer2_score: float) -> tuple[bool, list[str]]:
    """
    Check if combined pipeline meets quality thresholds.

    Args:
        diagnosis: Error attribution results
        layer1_score: Layer 1 overall quality score
        layer2_score: Layer 2 overall accuracy score

    Returns:
        (passed, list_of_failures)
    """
    failures = []

    # Overall pipeline quality (weighted average of both layers)
    pipeline_quality = (layer1_score * 0.4 + layer2_score * 0.6)
    if pipeline_quality < COMBINED_THRESHOLDS["overall_pipeline_quality"]:
        failures.append(
            f"Overall pipeline quality: {pipeline_quality:.2%} < {COMBINED_THRESHOLDS['overall_pipeline_quality']:.2%}"
        )

    # Error counts
    if diagnosis["parsing_errors"] > COMBINED_THRESHOLDS["max_parsing_errors"]:
        failures.append(
            f"Too many parsing errors: {diagnosis['parsing_errors']} > {COMBINED_THRESHOLDS['max_parsing_errors']}"
        )

    if diagnosis["llm_errors"] > COMBINED_THRESHOLDS["max_llm_errors"]:
        failures.append(
            f"Too many LLM errors: {diagnosis['llm_errors']} > {COMBINED_THRESHOLDS['max_llm_errors']}"
        )

    return len(failures) == 0, failures


# Error severity classification
ERROR_SEVERITY = {
    "unit_parsing": {
        "m3/h vs m^3/h": "HIGH",  # Could cause confusion in calculations
        "degC vs °C": "LOW",  # Just formatting, meaning is clear
        "Nm3/h vs m3/h": "CRITICAL",  # Different physical meaning (normal vs actual)
    },
    "value_parsing": {
        "decimal_separator": "CRITICAL",  # 850,5 vs 8505 is a factor of 10 error
        "thousands_separator": "CRITICAL",  # 5.000 vs 5000.0 is major
        "scientific_notation": "HIGH",  # 1.5e3 vs 15 is significant
        "precision_loss": "MEDIUM",  # 0.0125 vs 0.01 is acceptable in some contexts
    },
    "structure_mapping": {
        "wrong_field": "CRITICAL",  # Data in completely wrong JSON location
        "missing_field": "HIGH",  # Data not extracted at all
        "wrong_nesting": "HIGH",  # Data in wrong nested level
    },
}


def classify_error_severity(error_type: str, error_details: dict) -> str:
    """
    Classify the severity of an extraction error.

    Args:
        error_type: Type of error (unit_error, value_error, structure_error)
        error_details: Details about the specific error

    Returns:
        Severity level (CRITICAL, HIGH, MEDIUM, LOW)
    """
    # Default severities by error type
    default_severity = {
        "unit_error": "HIGH",
        "value_error": "CRITICAL",
        "structure_error": "HIGH",
        "missing": "HIGH",
    }

    # Check for specific error patterns
    if error_type == "unit_error":
        field = error_details.get("field", "")
        expected = str(error_details.get("expected", ""))
        actual = str(error_details.get("actual", ""))

        # Normal vs actual cubic meters confusion
        if ("Nm3" in expected and "m3" in actual) or ("m3" in expected and "Nm3" in actual):
            return "CRITICAL"

        # Superscript vs caret
        if ("m³" in expected and "m^3" in actual) or ("m3" in expected and "m^3" in actual):
            return "HIGH"

        # Degree symbol variations
        if "deg" in expected and "°" in actual:
            return "LOW"

    elif error_type == "value_error":
        expected = error_details.get("expected")
        actual = error_details.get("actual")

        # Check magnitude of error
        if expected and actual and isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            ratio = abs(expected - actual) / max(abs(expected), 1.0)

            if ratio > 0.5:  # More than 50% error
                return "CRITICAL"
            elif ratio > 0.1:  # 10-50% error
                return "HIGH"
            elif ratio > 0.01:  # 1-10% error
                return "MEDIUM"
            else:
                return "LOW"

    return default_severity.get(error_type, "MEDIUM")
