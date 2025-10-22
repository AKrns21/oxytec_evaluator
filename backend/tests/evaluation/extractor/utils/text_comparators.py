"""Text comparison utilities for evaluating document parsing quality (Layer 1)."""

from dataclasses import dataclass
from typing import List, Tuple
import difflib
import re


@dataclass
class TextComparison:
    """Result of comparing extracted text against expected text."""

    similarity_score: float  # 0.0 to 1.0
    missing_content: List[str]
    extra_content: List[str]
    encoding_issues: List[str]
    diff_summary: str


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace for comparison.

    Args:
        text: Input text

    Returns:
        Text with normalized whitespace
    """
    # Replace multiple spaces/tabs with single space
    text = re.sub(r"[ \t]+", " ", text)
    # Normalize line breaks
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def detect_encoding_issues(text: str) -> List[str]:
    """
    Detect common encoding problems in extracted text.

    Args:
        text: Extracted text to check

    Returns:
        List of detected encoding issues
    """
    issues = []

    # Common encoding artifacts
    patterns = {
        r"Â±": "Corrupted plus-minus symbol (ISO-8859-1 as UTF-8)",
        r"Â°": "Corrupted degree symbol (ISO-8859-1 as UTF-8)",
        r"\\x[0-9a-f]{2}": "Escaped hex characters",
        r"\\u[0-9a-f]{4}": "Escaped unicode characters",
    }

    for pattern, issue_desc in patterns.items():
        matches = re.findall(pattern, text)
        if matches:
            issues.append(f"{issue_desc} - found {len(matches)} occurrences")

    return issues


def compare_extracted_text(
    actual: str, expected: str, ignore_whitespace: bool = True
) -> TextComparison:
    """
    Compare extracted text against expected text.

    This is used to evaluate Layer 1 (document parsing quality).

    Args:
        actual: Text extracted by DocumentService
        expected: Expected text from ground truth
        ignore_whitespace: Whether to normalize whitespace before comparison

    Returns:
        TextComparison with detailed results
    """
    if ignore_whitespace:
        actual_norm = normalize_whitespace(actual)
        expected_norm = normalize_whitespace(expected)
    else:
        actual_norm = actual
        expected_norm = expected

    # Calculate similarity using SequenceMatcher
    similarity = difflib.SequenceMatcher(None, actual_norm, expected_norm).ratio()

    # Find differences
    diff = list(
        difflib.unified_diff(
            expected_norm.splitlines(keepends=True),
            actual_norm.splitlines(keepends=True),
            lineterm="",
            fromfile="expected",
            tofile="actual",
        )
    )

    # Identify missing content (in expected but not in actual)
    missing = []
    extra = []

    for line in diff:
        if line.startswith("-") and not line.startswith("---"):
            missing.append(line[1:].strip())
        elif line.startswith("+") and not line.startswith("+++"):
            extra.append(line[1:].strip())

    # Check for encoding issues
    encoding_issues = detect_encoding_issues(actual)

    # Generate diff summary
    if len(diff) > 0:
        diff_summary = "".join(diff[:50])  # First 50 lines
        if len(diff) > 50:
            diff_summary += f"\n... ({len(diff) - 50} more lines)"
    else:
        diff_summary = "No differences"

    return TextComparison(
        similarity_score=similarity,
        missing_content=missing[:10],  # First 10 items
        extra_content=extra[:10],
        encoding_issues=encoding_issues,
        diff_summary=diff_summary,
    )


def extract_numeric_values(text: str) -> List[Tuple[float, str, str]]:
    """
    Extract all numeric values with their units and surrounding context.

    This helps identify if numbers are being extracted correctly from documents.

    Args:
        text: Extracted text

    Returns:
        List of (value, unit, context) tuples
    """
    # Pattern: number (with optional decimal/scientific notation) followed by optional unit
    pattern = r"(\d+(?:[.,]\d+)?(?:[eE][+-]?\d+)?)\s*([a-zA-Z°³²/\-]+)?"

    matches = []
    for match in re.finditer(pattern, text):
        value_str = match.group(1)
        unit = match.group(2) or ""

        # Try to parse the number
        try:
            # Handle European decimal format
            value_str_normalized = value_str.replace(",", ".")
            value = float(value_str_normalized)

            # Get surrounding context (20 chars before and after)
            context = text[max(0, match.start() - 20) : min(len(text), match.end() + 20)]
            matches.append((value, unit, context.strip()))
        except ValueError:
            pass

    return matches


def extract_units(text: str) -> List[str]:
    """
    Extract all unit-like strings from text.

    This helps verify that units are being preserved correctly during document parsing.

    Args:
        text: Extracted text

    Returns:
        List of unique units found
    """
    # Common unit patterns in exhaust air treatment domain
    unit_pattern = r"\b(?:m3?/?h?|Nm3?/?h?|mg/Nm3?|mg/m3?|ppm|ppb|vol%|degC|°C|K|F|mbar|Pa|kPa|bar|atm|kg/h|g/h|l/min)\b"

    units = re.findall(unit_pattern, text, re.IGNORECASE)
    return list(set(units))


def check_table_preservation(text: str) -> dict:
    """
    Check if table structures are preserved in extracted text.

    Args:
        text: Extracted text

    Returns:
        {
            "has_table_markers": bool,      # Contains |, -, or tab separators
            "potential_tables": int,        # Number of potential table structures
            "column_separators": list       # Types of separators found
        }
    """
    separators = []

    # Check for common table separators
    if "|" in text:
        separators.append("pipe")
    if "\t" in text:
        separators.append("tab")
    if re.search(r"-{3,}", text):  # Three or more dashes
        separators.append("dash")

    # Count potential table structures
    # A table typically has multiple lines with the same separator pattern
    lines = text.split("\n")
    potential_tables = 0

    for i in range(len(lines) - 2):
        # Check if 3 consecutive lines have similar structure (same number of separators)
        if "|" in lines[i] and "|" in lines[i + 1] and "|" in lines[i + 2]:
            count1 = lines[i].count("|")
            count2 = lines[i + 1].count("|")
            count3 = lines[i + 2].count("|")
            if count1 == count2 == count3 and count1 > 1:
                potential_tables += 1
                break  # Count each contiguous table once

    return {
        "has_table_markers": len(separators) > 0,
        "potential_tables": potential_tables,
        "column_separators": separators,
    }


def calculate_parsing_quality_score(comparison: TextComparison) -> dict:
    """
    Calculate document parsing quality metrics from text comparison.

    Args:
        comparison: TextComparison result

    Returns:
        {
            "text_similarity": float,           # Overall similarity (0.0 to 1.0)
            "encoding_quality": float,          # 1.0 if no encoding issues
            "completeness": float,              # 1.0 if no missing content
            "precision": float,                 # 1.0 if no extra content
            "overall_parsing_quality": float    # Weighted average
        }
    """
    encoding_quality = 1.0 if len(comparison.encoding_issues) == 0 else 0.5

    # Normalize missing/extra content counts (assume max 100 differences)
    completeness = max(0.0, 1.0 - (len(comparison.missing_content) / 100))
    precision = max(0.0, 1.0 - (len(comparison.extra_content) / 100))

    # Weighted overall score
    overall_parsing_quality = (
        comparison.similarity_score * 0.5
        + encoding_quality * 0.2
        + completeness * 0.2
        + precision * 0.1
    )

    return {
        "text_similarity": comparison.similarity_score,
        "encoding_quality": encoding_quality,
        "completeness": completeness,
        "precision": precision,
        "overall_parsing_quality": overall_parsing_quality,
    }
