"""Metrics and reporting utilities for EXTRACTOR evaluation."""

from typing import Dict, List, Any
from .comparators import ExtractionComparison, FieldComparison
from .text_comparators import TextComparison, calculate_parsing_quality_score


def calculate_extraction_score(
    comparison: ExtractionComparison, critical_fields: List[str] = None
) -> Dict[str, Any]:
    """
    Calculate comprehensive extraction quality scores for Layer 2 (LLM interpretation).

    Args:
        comparison: ExtractionComparison result
        critical_fields: List of field paths that are critical

    Returns:
        {
            "overall_accuracy": float,          # 0.0 to 1.0
            "critical_field_accuracy": float,   # 0.0 to 1.0
            "unit_parsing_accuracy": float,     # 0.0 to 1.0
            "value_parsing_accuracy": float,    # 0.0 to 1.0
            "structure_accuracy": float,        # 0.0 to 1.0
            "error_breakdown": {...}
        }
    """
    critical_fields = critical_fields or []

    total_fields = len(comparison.matches) + len(comparison.mismatches)
    overall_accuracy = (
        len(comparison.matches) / total_fields if total_fields > 0 else 0.0
    )

    # Critical field accuracy
    critical_matches = [
        m for m in comparison.matches if m.field_path in critical_fields
    ]
    critical_mismatches = [
        m for m in comparison.mismatches if m.field_path in critical_fields
    ]
    total_critical = len(critical_matches) + len(critical_mismatches)
    critical_accuracy = (
        len(critical_matches) / total_critical if total_critical > 0 else 1.0
    )

    # Error type breakdown
    unit_errors = [m for m in comparison.mismatches if m.error_type == "unit_error"]
    value_errors = [m for m in comparison.mismatches if m.error_type == "value_error"]
    structure_errors = [
        m for m in comparison.mismatches if m.error_type == "structure_error"
    ]

    # Category-specific accuracies
    total_unit_fields = len(
        [m for m in comparison.matches if ".unit" in m.field_path]
    ) + len(unit_errors)
    unit_accuracy = (
        1.0 - (len(unit_errors) / total_unit_fields) if total_unit_fields > 0 else 1.0
    )

    total_value_fields = len(
        [m for m in comparison.matches if ".value" in m.field_path]
    ) + len(value_errors)
    value_accuracy = (
        1.0 - (len(value_errors) / total_value_fields)
        if total_value_fields > 0
        else 1.0
    )

    structure_accuracy = (
        1.0 - (len(structure_errors) / total_fields) if total_fields > 0 else 1.0
    )

    return {
        "overall_accuracy": overall_accuracy,
        "critical_field_accuracy": critical_accuracy,
        "unit_parsing_accuracy": unit_accuracy,
        "value_parsing_accuracy": value_accuracy,
        "structure_accuracy": structure_accuracy,
        "error_breakdown": {
            "unit_errors": len(unit_errors),
            "value_errors": len(value_errors),
            "structure_errors": len(structure_errors),
            "missing_fields": len(comparison.missing_fields),
        },
        "detailed_errors": {
            "unit_errors": [
                {"field": e.field_path, "expected": e.expected, "actual": e.actual}
                for e in unit_errors
            ],
            "value_errors": [
                {"field": e.field_path, "expected": e.expected, "actual": e.actual}
                for e in value_errors
            ],
            "structure_errors": [
                {"field": e.field_path, "expected": e.expected, "actual": e.actual}
                for e in structure_errors
            ],
        },
    }


def generate_layer1_report(test_results: List[Dict]) -> str:
    """
    Generate report for Layer 1 (document parsing quality).

    Args:
        test_results: List of parsing quality results

    Returns:
        Formatted markdown report
    """
    report_lines = ["# Layer 1: Document Parsing Quality Report\n"]
    report_lines.append(f"**Total Test Cases**: {len(test_results)}\n")

    # Overall statistics
    avg_similarity = sum(
        r["text_similarity"] for r in test_results
    ) / len(test_results)
    avg_encoding = sum(
        r["encoding_quality"] for r in test_results
    ) / len(test_results)
    avg_completeness = sum(
        r["completeness"] for r in test_results
    ) / len(test_results)

    total_encoding_issues = sum(
        len(r.get("encoding_issues", [])) for r in test_results
    )

    report_lines.append("## Summary Statistics\n")
    report_lines.append(f"- **Average Text Similarity**: {avg_similarity:.2%}")
    report_lines.append(f"- **Average Encoding Quality**: {avg_encoding:.2%}")
    report_lines.append(f"- **Average Completeness**: {avg_completeness:.2%}")
    report_lines.append(f"- **Total Encoding Issues**: {total_encoding_issues}\n")

    # Per-format breakdown
    formats = {}
    for result in test_results:
        fmt = result.get("format", "unknown")
        if fmt not in formats:
            formats[fmt] = []
        formats[fmt].append(result)

    if formats:
        report_lines.append("## Per-Format Quality\n")
        for fmt, results in formats.items():
            avg_fmt_similarity = sum(r["text_similarity"] for r in results) / len(
                results
            )
            report_lines.append(
                f"- **{fmt.upper()}**: {avg_fmt_similarity:.2%} ({len(results)} tests)"
            )

    report_lines.append("")

    # Individual test details
    report_lines.append("## Test Case Details\n")
    for idx, result in enumerate(test_results, 1):
        report_lines.append(f"### Case {idx}: {result.get('test_name', 'Unknown')}")
        report_lines.append(f"- Text Similarity: {result['text_similarity']:.2%}")
        report_lines.append(f"- Encoding Quality: {result['encoding_quality']:.2%}")

        if result.get("encoding_issues"):
            report_lines.append(
                f"- ⚠️  Encoding issues: {', '.join(result['encoding_issues'])}"
            )

        report_lines.append("")

    return "\n".join(report_lines)


def generate_layer2_report(test_results: List[Dict]) -> str:
    """
    Generate report for Layer 2 (LLM interpretation quality).

    Args:
        test_results: List of extraction score results

    Returns:
        Formatted markdown report
    """
    report_lines = ["# Layer 2: LLM Interpretation Quality Report\n"]
    report_lines.append(f"**Total Test Cases**: {len(test_results)}\n")

    # Overall statistics
    avg_overall = sum(r["overall_accuracy"] for r in test_results) / len(test_results)
    avg_critical = sum(r["critical_field_accuracy"] for r in test_results) / len(
        test_results
    )
    avg_unit = sum(r["unit_parsing_accuracy"] for r in test_results) / len(
        test_results
    )
    avg_value = sum(r["value_parsing_accuracy"] for r in test_results) / len(
        test_results
    )
    avg_structure = sum(r["structure_accuracy"] for r in test_results) / len(
        test_results
    )

    report_lines.append("## Summary Statistics\n")
    report_lines.append(f"- **Overall Accuracy**: {avg_overall:.2%}")
    report_lines.append(f"- **Critical Field Accuracy**: {avg_critical:.2%}")
    report_lines.append(f"- **Unit Parsing Accuracy**: {avg_unit:.2%}")
    report_lines.append(f"- **Value Parsing Accuracy**: {avg_value:.2%}")
    report_lines.append(f"- **Structure Accuracy**: {avg_structure:.2%}\n")

    # Error breakdown
    total_unit_errors = sum(
        r["error_breakdown"]["unit_errors"] for r in test_results
    )
    total_value_errors = sum(
        r["error_breakdown"]["value_errors"] for r in test_results
    )
    total_structure_errors = sum(
        r["error_breakdown"]["structure_errors"] for r in test_results
    )
    total_missing = sum(
        r["error_breakdown"]["missing_fields"] for r in test_results
    )

    report_lines.append("## Error Breakdown\n")
    report_lines.append(f"- **Unit Parsing Errors**: {total_unit_errors}")
    report_lines.append(f"- **Value Parsing Errors**: {total_value_errors}")
    report_lines.append(f"- **Structure Mapping Errors**: {total_structure_errors}")
    report_lines.append(f"- **Missing Fields**: {total_missing}\n")

    # Individual test case details
    report_lines.append("## Test Case Details\n")
    for idx, result in enumerate(test_results, 1):
        report_lines.append(f"### Case {idx}")
        report_lines.append(f"- Overall: {result['overall_accuracy']:.2%}")
        report_lines.append(
            f"- Critical Fields: {result['critical_field_accuracy']:.2%}"
        )

        if result["error_breakdown"]["unit_errors"] > 0:
            report_lines.append(
                f"- ⚠️  {result['error_breakdown']['unit_errors']} unit parsing errors"
            )
        if result["error_breakdown"]["value_errors"] > 0:
            report_lines.append(
                f"- ⚠️  {result['error_breakdown']['value_errors']} value parsing errors"
            )
        if result["error_breakdown"]["structure_errors"] > 0:
            report_lines.append(
                f"- ⚠️  {result['error_breakdown']['structure_errors']} structure errors"
            )

        report_lines.append("")

    return "\n".join(report_lines)


def generate_two_layer_report(
    layer1_results: List[Dict],
    layer2_results: List[Dict],
    diagnosis_results: Dict = None,
) -> str:
    """
    Generate comprehensive report covering both layers with error attribution.

    Args:
        layer1_results: Document parsing quality results
        layer2_results: LLM interpretation quality results
        diagnosis_results: Optional error attribution results

    Returns:
        Formatted markdown report
    """
    report = ["# EXTRACTOR Two-Layer Evaluation Report\n"]

    # Layer 1 summary
    report.append("## Layer 1: Document Parsing Quality\n")
    avg_similarity = sum(r["text_similarity"] for r in layer1_results) / len(
        layer1_results
    )
    total_encoding_issues = sum(
        len(r.get("encoding_issues", [])) for r in layer1_results
    )

    # Calculate per-format accuracy
    pdf_results = [r for r in layer1_results if r.get("format") == "pdf"]
    xlsx_results = [r for r in layer1_results if r.get("format") == "xlsx"]
    pdf_accuracy = (
        sum(r["text_similarity"] for r in pdf_results) / len(pdf_results)
        if pdf_results
        else 0.0
    )
    xlsx_accuracy = (
        sum(r["text_similarity"] for r in xlsx_results) / len(xlsx_results)
        if xlsx_results
        else 0.0
    )

    report.append(f"- Average Text Similarity: {avg_similarity:.2%}")
    report.append(f"- Encoding Issues: {total_encoding_issues}")
    report.append(f"- PDF Parsing Accuracy: {pdf_accuracy:.2%}")
    report.append(f"- Excel Parsing Accuracy: {xlsx_accuracy:.2%}\n")

    # Layer 2 summary
    report.append("## Layer 2: LLM Interpretation Quality\n")
    avg_overall = sum(r["overall_accuracy"] for r in layer2_results) / len(
        layer2_results
    )
    avg_unit = sum(r["unit_parsing_accuracy"] for r in layer2_results) / len(
        layer2_results
    )
    avg_value = sum(r["value_parsing_accuracy"] for r in layer2_results) / len(
        layer2_results
    )
    avg_structure = sum(r["structure_accuracy"] for r in layer2_results) / len(
        layer2_results
    )

    report.append(f"- Overall Accuracy: {avg_overall:.2%}")
    report.append(f"- Unit Parsing Accuracy: {avg_unit:.2%}")
    report.append(f"- Value Parsing Accuracy: {avg_value:.2%}")
    report.append(f"- Structure Accuracy: {avg_structure:.2%}\n")

    # Error attribution
    if diagnosis_results:
        report.append("## Error Attribution\n")
        report.append(
            f"- Document Parsing Errors: {diagnosis_results.get('parsing_errors', 0)}"
        )
        report.append(
            f"- LLM Interpretation Errors: {diagnosis_results.get('llm_errors', 0)}"
        )
        report.append(
            f"- Compound Errors: {diagnosis_results.get('compound_errors', 0)}\n"
        )

        # Recommendations
        report.append("## Recommendations\n")
        if diagnosis_results.get("parsing_errors", 0) > diagnosis_results.get(
            "llm_errors", 0
        ):
            report.append(
                "- 🔧 **Priority**: Improve DocumentService extraction quality"
            )
            report.append(
                "  - Focus on table parsing, encoding handling, and OCR quality"
            )
        elif diagnosis_results.get("llm_errors", 0) > 0:
            report.append("- 🔧 **Priority**: Improve LLM prompt engineering")
            report.append(
                "  - Enhance extraction prompts for better unit/value interpretation"
            )

        if total_encoding_issues > 0:
            report.append("- 🔧 **Action**: Fix encoding issues in document extraction")

        report.append("")

    return "\n".join(report)


def diagnose_error_sources(
    text_comparison: TextComparison,
    json_comparison: ExtractionComparison,
    extracted_text: str,
    extracted_facts: dict,
) -> Dict[str, int]:
    """
    Diagnose whether errors originated in document parsing (Layer 1) or LLM interpretation (Layer 2).

    Args:
        text_comparison: Layer 1 comparison result
        json_comparison: Layer 2 comparison result
        extracted_text: Raw text extracted from document
        extracted_facts: Structured JSON from LLM

    Returns:
        {
            "parsing_errors": int,      # Errors from DocumentService
            "llm_errors": int,          # Errors from LLM interpretation
            "compound_errors": int      # Errors from both layers
        }
    """
    parsing_errors = 0
    llm_errors = 0
    compound_errors = 0

    # Check each JSON mismatch
    for mismatch in json_comparison.mismatches:
        # Convert expected value to string for searching
        expected_str = str(mismatch.expected)

        # Check if the expected value appears in the extracted text
        if expected_str in extracted_text:
            # Value was in the text but LLM didn't extract it correctly
            llm_errors += 1
        elif any(
            expected_str in missing for missing in text_comparison.missing_content
        ):
            # Value is in the missing content list - definitely a parsing error
            parsing_errors += 1
        else:
            # Could be either layer or both
            compound_errors += 1

    return {
        "parsing_errors": parsing_errors,
        "llm_errors": llm_errors,
        "compound_errors": compound_errors,
    }
