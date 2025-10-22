# EXTRACTOR Quality Evaluation Strategy

## Overview

This document outlines a comprehensive strategy to evaluate the EXTRACTOR agent's quality across three critical error dimensions:

1. **Unit Parsing Errors**: Incorrect interpretation of units (m3/h → m^3/h, scientific notation issues)
2. **Data Value Errors**: Numeric parsing issues (comma vs. dot decimal separators, scientific notation)
3. **Structural Errors**: Data mapped to incorrect JSON fields

## Architecture Overview

### Test Structure

```
backend/tests/extractor_evaluation/
├── __init__.py
├── conftest.py                    # Pytest fixtures and utilities
├── test_extractor_unit_parsing.py # Unit parsing tests
├── test_extractor_value_parsing.py # Numeric value tests
├── test_extractor_structure.py    # JSON field mapping tests
├── test_extractor_integration.py  # Full end-to-end tests
├── utils/
│   ├── __init__.py
│   ├── validators.py              # JSON schema validators
│   ├── comparators.py             # Expected vs. actual comparison
│   └── metrics.py                 # Scoring and reporting
└── test_documents/
    ├── ground_truth/
    │   ├── case_001_expected.json
    │   ├── case_002_expected.json
    │   └── ...
    ├── pdf/
    │   ├── case_001_standard.pdf
    │   ├── case_002_scanned.pdf
    │   ├── case_003_mixed_units.pdf
    │   └── ...
    ├── docx/
    │   ├── case_001_table_heavy.docx
    │   ├── case_002_multipage.docx
    │   └── ...
    ├── xlsx/
    │   ├── case_001_measurement_table.xlsx
    │   ├── case_002_merged_cells.xlsx
    │   └── ...
    └── csv/
        ├── case_001_comma_decimal.csv
        ├── case_002_semicolon_sep.csv
        └── ...
```

## Test Document Design

### Document Categories

Each test case should target specific extraction challenges:

#### 1. Unit Parsing Challenge Documents

**Focus**: Test correct preservation of units as written in documents

- **case_unit_001_standard.pdf**: Standard units (m3/h, mg/Nm3, degC, mbar)
- **case_unit_002_superscript.pdf**: Superscript units (m³/h, Nm³/h) - should extract as "m3/h", "Nm3/h"
- **case_unit_003_unicode.pdf**: Unicode symbols (°C, ², ³) - should normalize to "degC", "m3/h"
- **case_unit_004_scientific.pdf**: Scientific notation (1.5e3 m3/h, 8.5E+2 mg/Nm3)
- **case_unit_005_mixed.pdf**: Mix of unit formats (m³/h and m3/h in same document)
- **case_unit_006_per_notation.docx**: Various "per" notations (m3/h, m³ h⁻¹, m3 per hour)
- **case_unit_007_pressure.xlsx**: Pressure variations (mbar, Pa, kPa, bar, atm)
- **case_unit_008_concentration.xlsx**: Concentration units (mg/m3, mg/Nm3, ppm, ppb, vol%, g/h)

**Expected behaviors**:
```json
{
  "process_parameters": {
    "flow_rate": {
      "value": 5000,
      "unit": "m3/h"  // NOT "m^3/h" or "m³/h"
    },
    "temperature": {
      "value": 45,
      "unit": "degC"  // NOT "°C" or "C"
    }
  }
}
```

#### 2. Numeric Value Challenge Documents

**Focus**: Test correct parsing of numbers with various formats

- **case_value_001_decimal_comma.xlsx**: European format (5.000,50 meaning 5000.50)
- **case_value_002_decimal_dot.xlsx**: US format (5,000.50 meaning 5000.50)
- **case_value_003_scientific.pdf**: Scientific notation (1.5E+03, 8.5e-02, 1,5E+03)
- **case_value_004_ranges.docx**: Value ranges (100-500 m3/h, 20±5 degC)
- **case_value_005_mixed_notation.pdf**: Mix of formats in same document
- **case_value_006_thousands.csv**: Thousands separators (1.000 vs 1,000 vs 1 000)
- **case_value_007_precision.xlsx**: High precision (0.000125, 1.2345E-04)
- **case_value_008_units_in_values.docx**: Units embedded in values ("5000m3/h" vs "5000 m3/h")

**Expected behaviors**:
```json
{
  "pollutant_characterization": {
    "pollutant_list": [
      {
        "name": "Toluene",
        "concentration": 850.5,  // Parsed from "850,5" (German format)
        "concentration_unit": "mg/Nm3"
      }
    ]
  },
  "process_parameters": {
    "flow_rate": {
      "value": 5000,  // Parsed from "5.000" or "5,000" depending on context
      "unit": "m3/h",
      "min_value": 4500,  // From range "4500-5500"
      "max_value": 5500
    }
  }
}
```

#### 3. Structural Mapping Challenge Documents

**Focus**: Test correct assignment to JSON schema fields

- **case_struct_001_ambiguous_flow.pdf**: Distinguish between exhaust air flow vs. water flow vs. gas flow
- **case_struct_002_multiple_temps.docx**: Multiple temperatures (exhaust air, ambient, process)
- **case_struct_003_nested_data.xlsx**: Complex nested tables
- **case_struct_004_implicit_data.pdf**: Information requiring inference (industry from process description)
- **case_struct_005_scattered_data.docx**: Related data across multiple pages
- **case_struct_006_questions_embedded.pdf**: Customer questions mixed with technical data
- **case_struct_007_current_vs_target.xlsx**: Current system vs. target requirements
- **case_struct_008_multiple_streams.pdf**: Multiple exhaust air streams with different parameters

**Expected behaviors**:
```json
{
  "process_parameters": {
    "flow_rate": {
      "value": 5000,
      "unit": "m3/h"
      // Should be exhaust air flow, NOT water flow from scrubber description
    },
    "temperature": {
      "value": 45,
      "unit": "degC"
      // Should be exhaust air temperature, NOT ambient temperature
    }
  },
  "site_conditions": {
    "ambient_conditions": {
      "temperature_range": "-10 to 40 degC"
      // Ambient temperature should go here
    }
  }
}
```

#### 4. Format-Specific Challenge Documents

**Focus**: Test format-specific extraction challenges

##### PDF Challenges
- **case_pdf_001_scanned.pdf**: Scanned document requiring OCR
- **case_pdf_002_multicolumn.pdf**: Multi-column layout
- **case_pdf_003_rotated_tables.pdf**: Rotated tables in landscape pages
- **case_pdf_004_embedded_images.pdf**: Data in image tables
- **case_pdf_005_complex_footer.pdf**: Headers/footers with data

##### DOCX Challenges
- **case_docx_001_nested_tables.docx**: Tables within tables
- **case_docx_002_text_boxes.docx**: Data in text boxes
- **case_docx_003_track_changes.docx**: Document with tracked changes
- **case_docx_004_comments.docx**: Data in comments/annotations

##### XLSX Challenges
- **case_xlsx_001_merged_cells.xlsx**: Merged cells in measurement tables
- **case_xlsx_002_multiple_sheets.xlsx**: Data across multiple sheets
- **case_xlsx_003_hidden_rows.xlsx**: Important data in hidden rows
- **case_xlsx_004_formulas.xlsx**: Values in formulas vs. displayed values
- **case_xlsx_005_conditional_format.xlsx**: Color-coded data requiring context

##### CSV Challenges
- **case_csv_001_semicolon.csv**: Semicolon separator (European)
- **case_csv_002_tab.csv**: Tab-separated values
- **case_csv_003_quoted_commas.csv**: Commas within quoted fields
- **case_csv_004_mixed_encoding.csv**: UTF-8 vs. ISO-8859-1 encoding

## Ground Truth Creation

### Ground Truth JSON Structure

Each test case needs a corresponding `*_expected.json` file with the following structure:

```json
{
  "test_case_id": "case_001",
  "description": "Standard VOC measurement report with flow rate and pollutant data",
  "difficulty": "easy",
  "focus_areas": ["unit_parsing", "pollutant_extraction"],
  "expected_extraction": {
    "pollutant_characterization": {
      "pollutant_list": [
        {
          "name": "Toluene",
          "cas_number": "108-88-3",
          "concentration": 850,
          "concentration_unit": "mg/Nm3",
          "category": "VOC"
        }
      ],
      "total_load": {
        "tvoc": 1270,
        "tvoc_unit": "mg/Nm3",
        "total_carbon": null,
        "odor_units": null
      }
    },
    "process_parameters": {
      "flow_rate": {
        "value": 5000,
        "unit": "m3/h",
        "min_value": null,
        "max_value": null
      }
    }
    // ... rest of schema
  },
  "critical_fields": [
    "pollutant_characterization.pollutant_list[0].concentration",
    "pollutant_characterization.pollutant_list[0].concentration_unit",
    "process_parameters.flow_rate.value",
    "process_parameters.flow_rate.unit"
  ],
  "acceptable_variations": {
    "pollutant_characterization.pollutant_list[0].cas_number": [
      "108-88-3",
      "108883",
      null  // Acceptable if not found
    ]
  }
}
```

### Ground Truth Creation Workflow

1. **Manual Creation**: Domain experts create documents with known correct values
2. **Annotation**: Mark critical fields that MUST be extracted correctly
3. **Variation Specification**: Define acceptable variations (e.g., CAS number formats)
4. **Peer Review**: Second expert reviews ground truth JSON
5. **Versioning**: Track ground truth versions with test documents

## Test Implementation

### Test Suite Structure

```python
# backend/tests/extractor_evaluation/conftest.py
import pytest
import json
from pathlib import Path
from app.agents.nodes.extractor import extractor_node
from app.services.document_service import DocumentService

@pytest.fixture
def test_documents_dir():
    """Return path to test documents directory."""
    return Path(__file__).parent / "test_documents"

@pytest.fixture
def ground_truth_dir(test_documents_dir):
    """Return path to ground truth JSON files."""
    return test_documents_dir / "ground_truth"

@pytest.fixture
async def document_service():
    """Provide document service instance."""
    return DocumentService()

@pytest.fixture
def load_expected_result():
    """Factory fixture to load expected JSON results."""
    def _load(case_id: str, ground_truth_dir: Path) -> dict:
        expected_file = ground_truth_dir / f"{case_id}_expected.json"
        with open(expected_file) as f:
            return json.load(f)
    return _load

@pytest.fixture
async def run_extractor():
    """Factory fixture to run extractor on a test document."""
    async def _run(document_path: Path, mime_type: str = None) -> dict:
        state = {
            "session_id": "test-session",
            "documents": [
                {
                    "filename": document_path.name,
                    "file_path": str(document_path),
                    "mime_type": mime_type or "application/pdf"
                }
            ]
        }
        result = await extractor_node(state)
        return result["extracted_facts"]
    return _run
```

### Test Categories

#### 1. Unit Parsing Tests

```python
# backend/tests/extractor_evaluation/test_extractor_unit_parsing.py
import pytest
from .utils.validators import validate_unit_format
from .utils.comparators import compare_units

class TestUnitParsing:
    """Test correct parsing and preservation of measurement units."""

    @pytest.mark.asyncio
    async def test_standard_units(self, run_extractor, test_documents_dir,
                                   load_expected_result, ground_truth_dir):
        """Test extraction of standard units (m3/h, mg/Nm3, degC)."""
        doc_path = test_documents_dir / "pdf" / "case_unit_001_standard.pdf"
        expected = load_expected_result("case_unit_001", ground_truth_dir)

        result = await run_extractor(doc_path)

        # Validate unit format
        flow_unit = result["process_parameters"]["flow_rate"]["unit"]
        assert validate_unit_format(flow_unit), \
            f"Invalid unit format: {flow_unit}"

        # Compare against expected
        assert compare_units(
            result["process_parameters"]["flow_rate"]["unit"],
            expected["expected_extraction"]["process_parameters"]["flow_rate"]["unit"]
        ), "Flow rate unit mismatch"

    @pytest.mark.asyncio
    async def test_superscript_units_normalization(self, run_extractor,
                                                     test_documents_dir):
        """Test that superscript units (m³/h) are normalized to m3/h."""
        doc_path = test_documents_dir / "pdf" / "case_unit_002_superscript.pdf"
        result = await run_extractor(doc_path)

        flow_unit = result["process_parameters"]["flow_rate"]["unit"]

        # Should NOT contain unicode superscripts
        assert "³" not in flow_unit, "Unit contains unicode superscript"
        assert "²" not in flow_unit, "Unit contains unicode superscript"

        # Should be normalized form
        assert flow_unit == "m3/h" or flow_unit == "Nm3/h", \
            f"Unit not normalized: {flow_unit}"

    @pytest.mark.asyncio
    async def test_scientific_notation_preservation(self, run_extractor,
                                                      test_documents_dir):
        """Test that scientific notation is correctly parsed to float."""
        doc_path = test_documents_dir / "pdf" / "case_unit_004_scientific.pdf"
        result = await run_extractor(doc_path)

        flow_value = result["process_parameters"]["flow_rate"]["value"]

        # 1.5e3 should become 1500.0
        assert isinstance(flow_value, (int, float)), \
            f"Flow value not numeric: {type(flow_value)}"
        assert 1400 < flow_value < 1600, \
            f"Scientific notation not parsed correctly: {flow_value}"
```

#### 2. Numeric Value Parsing Tests

```python
# backend/tests/extractor_evaluation/test_extractor_value_parsing.py
import pytest
from .utils.validators import validate_numeric_value
from .utils.comparators import compare_values_with_tolerance

class TestValueParsing:
    """Test correct parsing of numeric values with various formats."""

    @pytest.mark.asyncio
    async def test_european_decimal_format(self, run_extractor,
                                            test_documents_dir):
        """Test parsing of European decimal format (5.000,50)."""
        doc_path = test_documents_dir / "xlsx" / "case_value_001_decimal_comma.xlsx"
        result = await run_extractor(doc_path, mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        concentration = result["pollutant_characterization"]["pollutant_list"][0]["concentration"]

        # Document contains "850,5" which should parse to 850.5
        assert isinstance(concentration, (int, float)), \
            f"Concentration not numeric: {type(concentration)}"
        assert abs(concentration - 850.5) < 0.01, \
            f"Decimal comma not parsed correctly: {concentration}"

    @pytest.mark.asyncio
    async def test_thousands_separator_handling(self, run_extractor,
                                                  test_documents_dir):
        """Test correct handling of thousands separators."""
        doc_path = test_documents_dir / "csv" / "case_value_006_thousands.csv"
        result = await run_extractor(doc_path, mime_type="text/csv")

        flow_value = result["process_parameters"]["flow_rate"]["value"]

        # Document contains "5.000" (European) which should parse to 5000
        assert flow_value == 5000, \
            f"Thousands separator not handled correctly: {flow_value}"

    @pytest.mark.asyncio
    async def test_range_extraction(self, run_extractor, test_documents_dir):
        """Test extraction of min/max from range notation."""
        doc_path = test_documents_dir / "docx" / "case_value_004_ranges.docx"
        result = await run_extractor(doc_path)

        flow_rate = result["process_parameters"]["flow_rate"]

        # Document contains "4500-5500 m3/h"
        assert flow_rate["min_value"] == 4500, \
            f"Min value from range incorrect: {flow_rate['min_value']}"
        assert flow_rate["max_value"] == 5500, \
            f"Max value from range incorrect: {flow_rate['max_value']}"
```

#### 3. Structural Mapping Tests

```python
# backend/tests/extractor_evaluation/test_extractor_structure.py
import pytest
from .utils.validators import validate_json_schema
from .utils.comparators import compare_field_mappings

class TestStructuralMapping:
    """Test correct assignment of data to JSON schema fields."""

    @pytest.mark.asyncio
    async def test_ambiguous_flow_distinction(self, run_extractor,
                                               test_documents_dir):
        """Test distinction between exhaust air flow and other flows."""
        doc_path = test_documents_dir / "pdf" / "case_struct_001_ambiguous_flow.pdf"
        result = await run_extractor(doc_path)

        # Document contains exhaust air flow (5000 m3/h) and scrubber water flow (10 m3/h)
        exhaust_flow = result["process_parameters"]["flow_rate"]["value"]

        assert exhaust_flow == 5000, \
            f"Wrong flow extracted (should be exhaust air, not water): {exhaust_flow}"

        # Water flow should NOT appear in process_parameters.flow_rate
        assert exhaust_flow != 10, \
            "Water flow incorrectly mapped to exhaust air flow"

    @pytest.mark.asyncio
    async def test_temperature_field_separation(self, run_extractor,
                                                 test_documents_dir):
        """Test correct separation of exhaust vs. ambient temperature."""
        doc_path = test_documents_dir / "docx" / "case_struct_002_multiple_temps.docx"
        result = await run_extractor(doc_path)

        # Document contains exhaust temp (45°C) and ambient temp (-10 to 40°C)
        exhaust_temp = result["process_parameters"]["temperature"]["value"]
        ambient_temp_range = result["site_conditions"]["ambient_conditions"]["temperature_range"]

        assert exhaust_temp == 45, \
            f"Wrong temperature in process_parameters: {exhaust_temp}"
        assert "-10" in ambient_temp_range and "40" in ambient_temp_range, \
            f"Ambient temperature not in correct field: {ambient_temp_range}"

    @pytest.mark.asyncio
    async def test_customer_questions_extraction(self, run_extractor,
                                                   test_documents_dir):
        """Test extraction of customer-specific questions."""
        doc_path = test_documents_dir / "pdf" / "case_struct_006_questions_embedded.pdf"
        result = await run_extractor(doc_path)

        questions = result.get("customer_specific_questions", [])

        # Document contains 2 explicit customer questions
        assert len(questions) >= 2, \
            f"Not all customer questions extracted: found {len(questions)}"

        # Check question structure
        for q in questions:
            assert "question_text" in q, "Missing question_text field"
            assert "question_type" in q, "Missing question_type field"
            assert "priority" in q, "Missing priority field"
            assert q["priority"] in ["HIGH", "MEDIUM", "LOW"], \
                f"Invalid priority: {q['priority']}"
```

#### 4. Integration Tests

```python
# backend/tests/extractor_evaluation/test_extractor_integration.py
import pytest
from .utils.metrics import calculate_extraction_score
from .utils.comparators import deep_compare_extraction

class TestExtractorIntegration:
    """End-to-end integration tests with full scoring."""

    @pytest.mark.asyncio
    async def test_complete_extraction_easy_case(self, run_extractor,
                                                   test_documents_dir,
                                                   load_expected_result,
                                                   ground_truth_dir):
        """Test complete extraction on easy case with full scoring."""
        doc_path = test_documents_dir / "pdf" / "case_001_standard.pdf"
        expected = load_expected_result("case_001", ground_truth_dir)

        result = await run_extractor(doc_path)

        # Deep comparison
        comparison = deep_compare_extraction(
            result,
            expected["expected_extraction"],
            critical_fields=expected["critical_fields"],
            acceptable_variations=expected.get("acceptable_variations", {})
        )

        # Calculate score
        score = calculate_extraction_score(comparison)

        # Easy case should achieve >95% accuracy
        assert score["overall_accuracy"] > 0.95, \
            f"Accuracy too low for easy case: {score['overall_accuracy']:.2%}"
        assert score["critical_field_accuracy"] == 1.0, \
            f"Critical field errors in easy case: {score['critical_field_accuracy']:.2%}"

    @pytest.mark.parametrize("case_id,min_accuracy", [
        ("case_002", 0.90),  # Medium difficulty
        ("case_003", 0.85),  # Hard difficulty
        ("case_004", 0.80),  # Very hard difficulty
    ])
    @pytest.mark.asyncio
    async def test_extraction_difficulty_levels(self, run_extractor,
                                                  test_documents_dir,
                                                  load_expected_result,
                                                  ground_truth_dir,
                                                  case_id,
                                                  min_accuracy):
        """Test extraction across difficulty levels with appropriate thresholds."""
        doc_path = test_documents_dir / "pdf" / f"{case_id}_standard.pdf"
        expected = load_expected_result(case_id, ground_truth_dir)

        result = await run_extractor(doc_path)

        comparison = deep_compare_extraction(
            result,
            expected["expected_extraction"],
            critical_fields=expected["critical_fields"]
        )

        score = calculate_extraction_score(comparison)

        assert score["overall_accuracy"] >= min_accuracy, \
            f"Accuracy below threshold for {case_id}: " \
            f"{score['overall_accuracy']:.2%} < {min_accuracy:.2%}"
```

## Validation Utilities

### Unit Validators

```python
# backend/tests/extractor_evaluation/utils/validators.py
import re
from typing import Any

VALID_UNIT_PATTERNS = {
    "flow": [r"^m3/h$", r"^Nm3/h$", r"^kg/h$", r"^l/min$"],
    "concentration": [r"^mg/Nm3$", r"^mg/m3$", r"^ppm$", r"^ppb$", r"^vol%$", r"^g/h$"],
    "temperature": [r"^degC$", r"^K$", r"^F$"],
    "pressure": [r"^mbar$", r"^Pa$", r"^kPa$", r"^bar$", r"^atm$"],
}

INVALID_PATTERNS = [
    r"\^",  # Should not contain caret (m^3/h)
    r"°",   # Should not contain degree symbol
    r"³",   # Should not contain unicode superscript
    r"²",   # Should not contain unicode superscript
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


def validate_json_schema(extraction: dict) -> tuple[bool, list[str]]:
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
        "data_quality_issues"
    ]

    for field in required_top_level:
        if field not in extraction:
            errors.append(f"Missing top-level field: {field}")

    # Validate nested structure
    if "process_parameters" in extraction:
        pp = extraction["process_parameters"]
        if "flow_rate" in pp:
            fr = pp["flow_rate"]
            if "value" not in fr:
                errors.append("Missing process_parameters.flow_rate.value")
            if "unit" not in fr:
                errors.append("Missing process_parameters.flow_rate.unit")

    return len(errors) == 0, errors
```

### Comparison Utilities

```python
# backend/tests/extractor_evaluation/utils/comparators.py
from typing import Any, Dict, List, Set
from dataclasses import dataclass

@dataclass
class FieldComparison:
    """Result of comparing a single field."""
    field_path: str
    expected: Any
    actual: Any
    match: bool
    error_type: str  # "unit_error", "value_error", "structure_error", "missing"

@dataclass
class ExtractionComparison:
    """Result of comparing full extraction."""
    matches: List[FieldComparison]
    mismatches: List[FieldComparison]
    missing_fields: List[str]
    extra_fields: List[str]

def compare_units(actual: str, expected: str) -> bool:
    """Compare two unit strings with normalization."""
    if actual == expected:
        return True

    # Normalize for comparison
    actual_norm = actual.replace(" ", "").lower()
    expected_norm = expected.replace(" ", "").lower()

    return actual_norm == expected_norm


def compare_values_with_tolerance(actual: float, expected: float,
                                   rel_tol: float = 0.01,
                                   abs_tol: float = 0.0001) -> bool:
    """Compare numeric values with relative and absolute tolerance."""
    if actual == expected:
        return True

    # Relative tolerance
    if abs(actual - expected) / max(abs(expected), 1.0) <= rel_tol:
        return True

    # Absolute tolerance
    if abs(actual - expected) <= abs_tol:
        return True

    return False


def deep_compare_extraction(actual: dict, expected: dict,
                             critical_fields: List[str] = None,
                             acceptable_variations: Dict[str, List[Any]] = None) -> ExtractionComparison:
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
                mismatches.append(FieldComparison(
                    field_path=path,
                    expected=expected_val,
                    actual=actual_val,
                    match=False,
                    error_type="structure_error"
                ))
                return

            for key, exp_value in expected_val.items():
                new_path = f"{path}.{key}" if path else key
                if key not in actual_val:
                    missing_fields.append(new_path)
                    continue
                compare_recursive(actual_val[key], exp_value, new_path)

        elif isinstance(expected_val, list):
            if not isinstance(actual_val, list):
                mismatches.append(FieldComparison(
                    field_path=path,
                    expected=expected_val,
                    actual=actual_val,
                    match=False,
                    error_type="structure_error"
                ))
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
                match = compare_units(actual_val, expected_val)
                error_type = "unit_error" if not match else None
            elif isinstance(expected_val, (int, float)):
                match = compare_values_with_tolerance(actual_val, expected_val)
                error_type = "value_error" if not match else None
            else:
                match = actual_val == expected_val

            comparison = FieldComparison(
                field_path=path,
                expected=expected_val,
                actual=actual_val,
                match=match,
                error_type=error_type if not match else None
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
        extra_fields=[]
    )
```

### Metrics and Reporting

```python
# backend/tests/extractor_evaluation/utils/metrics.py
from typing import Dict, List
from .comparators import ExtractionComparison, FieldComparison

def calculate_extraction_score(comparison: ExtractionComparison,
                                critical_fields: List[str] = None) -> Dict[str, float]:
    """
    Calculate comprehensive extraction quality scores.

    Returns:
        {
            "overall_accuracy": float,          # 0.0 to 1.0
            "critical_field_accuracy": float,   # 0.0 to 1.0
            "unit_parsing_accuracy": float,     # 0.0 to 1.0
            "value_parsing_accuracy": float,    # 0.0 to 1.0
            "structure_accuracy": float,        # 0.0 to 1.0
            "error_breakdown": {
                "unit_errors": int,
                "value_errors": int,
                "structure_errors": int,
                "missing_fields": int
            }
        }
    """
    critical_fields = critical_fields or []

    total_fields = len(comparison.matches) + len(comparison.mismatches)
    overall_accuracy = len(comparison.matches) / total_fields if total_fields > 0 else 0.0

    # Critical field accuracy
    critical_matches = [m for m in comparison.matches if m.field_path in critical_fields]
    critical_mismatches = [m for m in comparison.mismatches if m.field_path in critical_fields]
    total_critical = len(critical_matches) + len(critical_mismatches)
    critical_accuracy = len(critical_matches) / total_critical if total_critical > 0 else 1.0

    # Error type breakdown
    unit_errors = [m for m in comparison.mismatches if m.error_type == "unit_error"]
    value_errors = [m for m in comparison.mismatches if m.error_type == "value_error"]
    structure_errors = [m for m in comparison.mismatches if m.error_type == "structure_error"]

    # Category-specific accuracies
    total_unit_fields = len([m for m in comparison.matches if ".unit" in m.field_path]) + len(unit_errors)
    unit_accuracy = 1.0 - (len(unit_errors) / total_unit_fields) if total_unit_fields > 0 else 1.0

    total_value_fields = len([m for m in comparison.matches if ".value" in m.field_path]) + len(value_errors)
    value_accuracy = 1.0 - (len(value_errors) / total_value_fields) if total_value_fields > 0 else 1.0

    structure_accuracy = 1.0 - (len(structure_errors) / total_fields) if total_fields > 0 else 1.0

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
            "missing_fields": len(comparison.missing_fields)
        },
        "detailed_errors": {
            "unit_errors": [{"field": e.field_path, "expected": e.expected, "actual": e.actual}
                            for e in unit_errors],
            "value_errors": [{"field": e.field_path, "expected": e.expected, "actual": e.actual}
                             for e in value_errors],
            "structure_errors": [{"field": e.field_path, "expected": e.expected, "actual": e.actual}
                                 for e in structure_errors],
        }
    }


def generate_test_report(test_results: List[Dict]) -> str:
    """
    Generate human-readable test report.

    Args:
        test_results: List of test results from calculate_extraction_score

    Returns:
        Formatted markdown report
    """
    report_lines = ["# EXTRACTOR Evaluation Report\n"]
    report_lines.append(f"**Total Test Cases**: {len(test_results)}\n")

    # Overall statistics
    avg_overall = sum(r["overall_accuracy"] for r in test_results) / len(test_results)
    avg_critical = sum(r["critical_field_accuracy"] for r in test_results) / len(test_results)
    avg_unit = sum(r["unit_parsing_accuracy"] for r in test_results) / len(test_results)
    avg_value = sum(r["value_parsing_accuracy"] for r in test_results) / len(test_results)
    avg_structure = sum(r["structure_accuracy"] for r in test_results) / len(test_results)

    report_lines.append("## Summary Statistics\n")
    report_lines.append(f"- **Overall Accuracy**: {avg_overall:.2%}")
    report_lines.append(f"- **Critical Field Accuracy**: {avg_critical:.2%}")
    report_lines.append(f"- **Unit Parsing Accuracy**: {avg_unit:.2%}")
    report_lines.append(f"- **Value Parsing Accuracy**: {avg_value:.2%}")
    report_lines.append(f"- **Structure Accuracy**: {avg_structure:.2%}\n")

    # Error breakdown
    total_unit_errors = sum(r["error_breakdown"]["unit_errors"] for r in test_results)
    total_value_errors = sum(r["error_breakdown"]["value_errors"] for r in test_results)
    total_structure_errors = sum(r["error_breakdown"]["structure_errors"] for r in test_results)
    total_missing = sum(r["error_breakdown"]["missing_fields"] for r in test_results)

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
        report_lines.append(f"- Critical Fields: {result['critical_field_accuracy']:.2%}")

        if result["error_breakdown"]["unit_errors"] > 0:
            report_lines.append(f"- ⚠️ {result['error_breakdown']['unit_errors']} unit parsing errors")
        if result["error_breakdown"]["value_errors"] > 0:
            report_lines.append(f"- ⚠️ {result['error_breakdown']['value_errors']} value parsing errors")
        if result["error_breakdown"]["structure_errors"] > 0:
            report_lines.append(f"- ⚠️ {result['error_breakdown']['structure_errors']} structure errors")

        report_lines.append("")

    return "\n".join(report_lines)
```

## Running the Evaluation Suite

### Basic Execution

```bash
# Run all extractor evaluation tests
pytest backend/tests/extractor_evaluation/ -v

# Run specific category
pytest backend/tests/extractor_evaluation/test_extractor_unit_parsing.py -v

# Run with coverage
pytest backend/tests/extractor_evaluation/ --cov=app.agents.nodes.extractor

# Generate detailed report
pytest backend/tests/extractor_evaluation/ -v --html=report.html --self-contained-html
```

### Continuous Testing

```bash
# Watch mode for development
pytest-watch backend/tests/extractor_evaluation/

# Run on file change
find backend/app/agents/nodes/extractor.py backend/app/services/document_service.py | entr pytest backend/tests/extractor_evaluation/
```

### CI/CD Integration

```yaml
# .github/workflows/extractor-evaluation.yml
name: EXTRACTOR Quality Evaluation

on:
  push:
    branches: [main, develop]
    paths:
      - 'backend/app/agents/nodes/extractor.py'
      - 'backend/app/services/document_service.py'
      - 'backend/tests/extractor_evaluation/**'
  pull_request:
    branches: [main]

jobs:
  evaluate:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov

      - name: Run EXTRACTOR evaluation suite
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          cd backend
          pytest tests/extractor_evaluation/ -v --cov=app.agents.nodes.extractor --cov-report=xml

      - name: Check quality thresholds
        run: |
          # Fail if overall accuracy < 90%
          python backend/tests/extractor_evaluation/check_thresholds.py

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml
```

## Threshold Configuration

Create a threshold configuration file for automated pass/fail:

```python
# backend/tests/extractor_evaluation/thresholds.py
QUALITY_THRESHOLDS = {
    "easy_cases": {
        "overall_accuracy": 0.95,
        "critical_field_accuracy": 1.0,
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
    }
}
```

## Initial Test Document Creation Priorities

### Phase 1: Foundation (Week 1)
1. Create 5 easy cases covering basic unit formats and standard values
2. Create ground truth JSON for each
3. Implement core validation and comparison utilities
4. Get baseline accuracy measurements

### Phase 2: Unit Coverage (Week 2)
1. Create 8 unit parsing challenge documents (case_unit_001 through case_unit_008)
2. Add superscript, unicode, and scientific notation variants
3. Test all pressure and concentration unit variations

### Phase 3: Value Parsing (Week 3)
1. Create 8 value parsing challenge documents (case_value_001 through case_value_008)
2. Cover European/US decimal formats, thousands separators, ranges
3. Test edge cases like very small/large numbers

### Phase 4: Structure (Week 4)
1. Create 8 structural mapping documents (case_struct_001 through case_struct_008)
2. Test ambiguous data, multiple streams, embedded questions
3. Validate correct field assignment

### Phase 5: Format Coverage (Week 5-6)
1. Create PDF challenges (scanned, multicolumn, rotated tables)
2. Create DOCX challenges (nested tables, text boxes, track changes)
3. Create XLSX challenges (merged cells, multiple sheets, formulas)
4. Create CSV challenges (different delimiters, encodings)

## Success Criteria

The evaluation suite is successful when:

1. **Test Coverage**: Minimum 40 test documents covering all error categories
2. **Baseline Established**: Current EXTRACTOR performance measured across all categories
3. **Regression Detection**: Tests catch degradation in accuracy after prompt/code changes
4. **Error Attribution**: Can identify whether errors are from LLM, document parsing, or prompt engineering
5. **Continuous Monitoring**: Automated CI/CD runs on every EXTRACTOR-related change

## Future Enhancements

1. **Fuzzy Matching**: Allow minor variations in extracted text (e.g., "Toluen" vs. "Toluene")
2. **Multi-language Support**: Test documents in multiple languages (German, English, French)
3. **Adversarial Cases**: Intentionally malformed or contradictory documents
4. **Performance Benchmarks**: Measure extraction time per document type
5. **Cost Tracking**: Monitor token usage per extraction
6. **Human Annotation**: Expert validation of ground truth and edge cases
7. **Active Learning**: Identify cases where model is uncertain and needs human review
