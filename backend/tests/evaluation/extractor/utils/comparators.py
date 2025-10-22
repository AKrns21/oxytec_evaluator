"""Comparison utilities for EXTRACTOR evaluation."""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class FieldComparison:
    """Result of comparing a single field."""

    field_path: str
    expected: Any
    actual: Any
    match: bool
    error_type: Optional[str] = None  # "unit_error", "value_error", "structure_error", "missing"


@dataclass
class ExtractionComparison:
    """Result of comparing full extraction."""

    matches: List[FieldComparison] = field(default_factory=list)
    mismatches: List[FieldComparison] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    extra_fields: List[str] = field(default_factory=list)


def compare_units(actual: str, expected: str) -> bool:
    """
    Compare two unit strings with normalization.

    Args:
        actual: Actual unit extracted
        expected: Expected unit from ground truth

    Returns:
        True if units match (after normalization)
    """
    if actual == expected:
        return True

    # Normalize for comparison
    actual_norm = actual.replace(" ", "").lower()
    expected_norm = expected.replace(" ", "").lower()

    return actual_norm == expected_norm


def compare_values_with_tolerance(
    actual: float, expected: float, rel_tol: float = 0.01, abs_tol: float = 0.0001
) -> bool:
    """
    Compare numeric values with relative and absolute tolerance.

    Args:
        actual: Actual value extracted
        expected: Expected value from ground truth
        rel_tol: Relative tolerance (default 1%)
        abs_tol: Absolute tolerance (default 0.0001)

    Returns:
        True if values match within tolerance
    """
    if actual == expected:
        return True

    # Handle None cases
    if actual is None or expected is None:
        return False

    # Convert to float if needed
    try:
        actual_float = float(actual)
        expected_float = float(expected)
    except (ValueError, TypeError):
        return False

    # Relative tolerance
    if abs(actual_float - expected_float) / max(abs(expected_float), 1.0) <= rel_tol:
        return True

    # Absolute tolerance
    if abs(actual_float - expected_float) <= abs_tol:
        return True

    return False


def deep_compare_extraction(
    actual: dict,
    expected: dict,
    critical_fields: Optional[List[str]] = None,
    acceptable_variations: Optional[Dict[str, List[Any]]] = None,
) -> ExtractionComparison:
    """
    Deep comparison of extraction results.

    Args:
        actual: Actual extraction result
        expected: Expected extraction result
        critical_fields: List of field paths that are critical (e.g., "process_parameters.flow_rate.value")
        acceptable_variations: Dict of field paths to acceptable value variations

    Returns:
        ExtractionComparison with detailed results
    """
    matches = []
    mismatches = []
    missing_fields = []

    critical_fields = critical_fields or []
    acceptable_variations = acceptable_variations or {}

    def compare_recursive(actual_val, expected_val, path=""):
        """Recursively compare nested structures."""
        if isinstance(expected_val, dict):
            if not isinstance(actual_val, dict):
                mismatches.append(
                    FieldComparison(
                        field_path=path,
                        expected=expected_val,
                        actual=actual_val,
                        match=False,
                        error_type="structure_error",
                    )
                )
                return

            for key, exp_value in expected_val.items():
                new_path = f"{path}.{key}" if path else key
                if key not in actual_val:
                    missing_fields.append(new_path)
                    continue
                compare_recursive(actual_val[key], exp_value, new_path)

        elif isinstance(expected_val, list):
            if not isinstance(actual_val, list):
                mismatches.append(
                    FieldComparison(
                        field_path=path,
                        expected=expected_val,
                        actual=actual_val,
                        match=False,
                        error_type="structure_error",
                    )
                )
                return

            # For lists, compare each element
            for idx, exp_item in enumerate(expected_val):
                if idx >= len(actual_val):
                    missing_fields.append(f"{path}[{idx}]")
                    continue
                compare_recursive(actual_val[idx], exp_item, f"{path}[{idx}]")

        else:
            # Leaf value comparison
            match = False
            error_type = "value_error"

            # Check acceptable variations
            if path in acceptable_variations:
                match = actual_val in acceptable_variations[path]

            # Type-specific comparison
            elif isinstance(expected_val, str) and ".unit" in path:
                if isinstance(actual_val, str):
                    match = compare_units(actual_val, expected_val)
                    error_type = "unit_error" if not match else None
                else:
                    match = False
                    error_type = "unit_error"

            elif isinstance(expected_val, (int, float)) and expected_val is not None:
                match = compare_values_with_tolerance(actual_val, expected_val)
                error_type = "value_error" if not match else None

            elif expected_val is None:
                # For null expected values, actual can be null or empty
                match = actual_val is None or actual_val == "" or actual_val == []
                if not match:
                    error_type = "value_error"

            else:
                match = actual_val == expected_val
                if not match:
                    error_type = "value_error"

            comparison = FieldComparison(
                field_path=path,
                expected=expected_val,
                actual=actual_val,
                match=match,
                error_type=error_type if not match else None,
            )

            if match:
                matches.append(comparison)
            else:
                mismatches.append(comparison)

    compare_recursive(actual, expected)

    return ExtractionComparison(
        matches=matches,
        mismatches=mismatches,
        missing_fields=missing_fields,
        extra_fields=[],
    )


def compare_field_mappings(
    actual: dict, field_mapping: Dict[str, str], expected_values: Dict[str, Any]
) -> List[FieldComparison]:
    """
    Compare specific field mappings.

    Args:
        actual: Actual extraction result
        field_mapping: Dict mapping field names to their paths (e.g., {"exhaust_flow": "process_parameters.flow_rate.value"})
        expected_values: Dict mapping field names to expected values

    Returns:
        List of FieldComparison objects
    """
    results = []

    for field_name, field_path in field_mapping.items():
        # Navigate to the field in actual
        parts = field_path.split(".")
        actual_val = actual
        try:
            for part in parts:
                actual_val = actual_val[part]
        except (KeyError, TypeError):
            results.append(
                FieldComparison(
                    field_path=field_path,
                    expected=expected_values.get(field_name),
                    actual=None,
                    match=False,
                    error_type="missing",
                )
            )
            continue

        expected_val = expected_values.get(field_name)

        # Compare based on type
        if isinstance(expected_val, str) and "unit" in field_name:
            match = compare_units(actual_val, expected_val)
            error_type = "unit_error" if not match else None
        elif isinstance(expected_val, (int, float)):
            match = compare_values_with_tolerance(actual_val, expected_val)
            error_type = "value_error" if not match else None
        else:
            match = actual_val == expected_val
            error_type = "value_error" if not match else None

        results.append(
            FieldComparison(
                field_path=field_path,
                expected=expected_val,
                actual=actual_val,
                match=match,
                error_type=error_type,
            )
        )

    return results
