# EXTRACTOR Quality Evaluation Strategy v2.0

## Critical Update: Two-Layer Evaluation Approach

**Key Insight**: Extraction errors can originate from two distinct sources:

1. **Document Parsing Layer** (DocumentService) - Text extraction from files
2. **LLM Interpretation Layer** (EXTRACTOR agent) - Structured data extraction from text

We must evaluate **both layers independently** to accurately diagnose where errors occur.

## Architecture: Two-Layer Testing

```
Test Document (PDF/DOCX/XLSX)
         ↓
    ┌────────────────────────────────────┐
    │  Layer 1: Document Parsing         │
    │  (DocumentService.extract_text)    │
    └────────────────────────────────────┘
         ↓
    Extracted Raw Text
    ├─→ [Ground Truth Text Comparison] ← Layer 1 Tests
    │
    └─→ LLM with Extraction Prompt
         ↓
    ┌────────────────────────────────────┐
    │  Layer 2: LLM Interpretation       │
    │  (EXTRACTOR agent)                 │
    └────────────────────────────────────┘
         ↓
    Structured JSON
    └─→ [Ground Truth JSON Comparison] ← Layer 2 Tests
```

## Test Structure

```
backend/tests/extractor_evaluation/
├── __init__.py
├── conftest.py
├── thresholds.py
│
├── layer1_document_parsing/           # NEW: Document extraction quality
│   ├── __init__.py
│   ├── test_pdf_parsing.py
│   ├── test_docx_parsing.py
│   ├── test_xlsx_parsing.py
│   ├── test_csv_parsing.py
│   └── test_vision_fallback.py
│
├── layer2_llm_interpretation/         # LLM extraction quality
│   ├── __init__.py
│   ├── test_unit_parsing.py
│   ├── test_value_parsing.py
│   ├── test_structure_mapping.py
│   └── test_integration.py
│
├── utils/
│   ├── __init__.py
│   ├── validators.py
│   ├── comparators.py
│   ├── metrics.py
│   └── text_comparators.py           # NEW: For comparing extracted text
│
└── test_documents/
    ├── ground_truth/
    │   ├── text/                      # NEW: Expected extracted text
    │   │   ├── case_001_expected_text.txt
    │   │   └── ...
    │   └── json/                      # Expected final JSON
    │       ├── case_001_expected.json
    │       └── ...
    ├── pdf/
    ├── docx/
    ├── xlsx/
    └── csv/
```

## Layer 1: Document Parsing Evaluation

### Objective
Evaluate whether DocumentService correctly extracts text, tables, units, and numeric values from various file formats.

### Ground Truth for Layer 1

Each test document needs a `*_expected_text.txt` file showing what **should** be extracted:

**Example: case_001_expected_text.txt**
```
--- Page 1 ---
VOC Measurement Report

Exhaust Air Parameters:
Flow rate: 5000 m3/h
Temperature: 45 degC
Pressure: -5 mbar

Pollutant Analysis:
| Substance      | CAS Number | Concentration | Unit    |
|----------------|------------|---------------|---------|
| Toluene        | 108-88-3   | 850.5         | mg/Nm3  |
| Ethyl acetate  | 141-78-6   | 420.0         | mg/Nm3  |

Total VOC: 1270.5 mg/Nm3
```

### Key Evaluation Points for Layer 1

1. **Unit Preservation**: Does extracted text preserve units exactly as written?
   - ✅ GOOD: "5000 m3/h" extracted from "5000 m³/h" in PDF
   - ❌ BAD: "5000 m h" extracted from "5000 m³/h" (lost formatting)

2. **Numeric Value Preservation**: Are numbers extracted with correct decimal separators?
   - ✅ GOOD: "850,5" extracted from German Excel file
   - ❌ BAD: "8505" or "850.5" (wrong interpretation at parsing stage)

3. **Table Structure Preservation**: Are tables kept in readable format?
   - ✅ GOOD: Columns aligned, headers preserved
   - ❌ BAD: Cells merged incorrectly, columns scrambled

4. **Special Characters**: Are symbols correctly extracted?
   - ✅ GOOD: "±5 degC" preserved
   - ❌ BAD: "Â±5 Â°C" (encoding issues)

### Layer 1 Test Implementation

```python
# backend/tests/extractor_evaluation/layer1_document_parsing/test_pdf_parsing.py
import pytest
from pathlib import Path
from app.services.document_service import DocumentService
from ..utils.text_comparators import compare_extracted_text, normalize_whitespace

class TestPDFParsing:
    """Test DocumentService PDF extraction quality."""

    @pytest.mark.asyncio
    async def test_pdf_standard_text_extraction(self, document_service, test_documents_dir):
        """Test extraction from standard text-based PDF."""
        doc_path = test_documents_dir / "pdf" / "case_001_standard.pdf"
        expected_text_path = test_documents_dir / "ground_truth" / "text" / "case_001_expected_text.txt"

        # Extract text using DocumentService
        extracted_text = await document_service.extract_text(str(doc_path))

        # Load expected text
        with open(expected_text_path, 'r', encoding='utf-8') as f:
            expected_text = f.read()

        # Compare with normalization
        comparison = compare_extracted_text(extracted_text, expected_text)

        assert comparison.similarity_score > 0.95, \
            f"Text extraction quality too low: {comparison.similarity_score:.2%}\n" \
            f"Differences:\n{comparison.diff_summary}"

    @pytest.mark.asyncio
    async def test_pdf_unit_preservation(self, document_service, test_documents_dir):
        """Test that units are correctly extracted from PDF."""
        doc_path = test_documents_dir / "pdf" / "case_unit_002_superscript.pdf"

        extracted_text = await document_service.extract_text(str(doc_path))

        # Check for specific unit patterns
        # Document contains "5000 m³/h" - should be extractable
        assert "m3/h" in extracted_text or "m³/h" in extracted_text, \
            "Flow rate unit not found in extracted text"

        # Should NOT have garbled encoding
        assert "mÂ³" not in extracted_text, \
            "Encoding issues detected in unit extraction"

    @pytest.mark.asyncio
    async def test_pdf_table_extraction(self, document_service, test_documents_dir):
        """Test that tables are extracted in readable format."""
        doc_path = test_documents_dir / "pdf" / "case_003_table_heavy.pdf"

        extracted_text = await document_service.extract_text(str(doc_path))

        # Check for key table elements
        assert "Toluene" in extracted_text, "Pollutant name not extracted"
        assert "108-88-3" in extracted_text or "108883" in extracted_text, \
            "CAS number not extracted"
        assert "850" in extracted_text, "Concentration value not extracted"

    @pytest.mark.asyncio
    async def test_pdf_scanned_with_vision_fallback(self, document_service, test_documents_dir):
        """Test vision API fallback for scanned PDFs."""
        doc_path = test_documents_dir / "pdf" / "case_pdf_001_scanned.pdf"
        expected_text_path = test_documents_dir / "ground_truth" / "text" / "case_pdf_001_expected_text.txt"

        extracted_text = await document_service.extract_text(str(doc_path))

        with open(expected_text_path, 'r', encoding='utf-8') as f:
            expected_text = f.read()

        comparison = compare_extracted_text(extracted_text, expected_text)

        # Lower threshold for OCR (vision API)
        assert comparison.similarity_score > 0.85, \
            f"Vision API extraction quality too low: {comparison.similarity_score:.2%}"


# backend/tests/extractor_evaluation/layer1_document_parsing/test_xlsx_parsing.py
class TestXLSXParsing:
    """Test DocumentService Excel extraction quality."""

    @pytest.mark.asyncio
    async def test_xlsx_decimal_comma_preservation(self, document_service, test_documents_dir):
        """Test that decimal commas in Excel are preserved."""
        doc_path = test_documents_dir / "xlsx" / "case_value_001_decimal_comma.xlsx"

        extracted_text = await document_service.extract_text(str(doc_path))

        # European format: 850,5 (not 850.5)
        assert "850,5" in extracted_text or "850.5" in extracted_text, \
            "Decimal value not extracted from Excel"

    @pytest.mark.asyncio
    async def test_xlsx_merged_cells(self, document_service, test_documents_dir):
        """Test extraction from Excel with merged cells."""
        doc_path = test_documents_dir / "xlsx" / "case_xlsx_001_merged_cells.xlsx"

        extracted_text = await document_service.extract_text(str(doc_path))

        # Check that merged cell content appears
        assert "Process Parameters" in extracted_text, \
            "Merged cell header not extracted"

    @pytest.mark.asyncio
    async def test_xlsx_multiple_sheets(self, document_service, test_documents_dir):
        """Test extraction from Excel with multiple sheets."""
        doc_path = test_documents_dir / "xlsx" / "case_xlsx_002_multiple_sheets.xlsx"

        extracted_text = await document_service.extract_text(str(doc_path))

        # Should extract from all sheets
        assert "Sheet1" in extracted_text or "Measurements" in extracted_text, \
            "First sheet not extracted"
        assert "Sheet2" in extracted_text or "Process Data" in extracted_text, \
            "Second sheet not extracted"
```

### New Utility: Text Comparison

```python
# backend/tests/extractor_evaluation/utils/text_comparators.py
"""Text comparison utilities for evaluating document parsing quality."""

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
    """Normalize whitespace for comparison."""
    # Replace multiple spaces/tabs with single space
    text = re.sub(r'[ \t]+', ' ', text)
    # Normalize line breaks
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    return text.strip()


def detect_encoding_issues(text: str) -> List[str]:
    """Detect common encoding problems."""
    issues = []

    # Common encoding artifacts
    patterns = {
        r'Â±': 'Corrupted ± symbol',
        r'Â°': 'Corrupted ° symbol',
        r'â€™': 'Corrupted apostrophe',
        r'â€"': 'Corrupted dash',
        r'Ã¤|Ã¶|Ã¼': 'Corrupted German umlauts',
        r'\\x[0-9a-f]{2}': 'Escaped hex characters',
    }

    for pattern, issue_desc in patterns.items():
        if re.search(pattern, text):
            issues.append(issue_desc)

    return issues


def compare_extracted_text(
    actual: str,
    expected: str,
    ignore_whitespace: bool = True
) -> TextComparison:
    """
    Compare extracted text against expected text.

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
    diff = list(difflib.unified_diff(
        expected_norm.splitlines(keepends=True),
        actual_norm.splitlines(keepends=True),
        lineterm='',
        fromfile='expected',
        tofile='actual'
    ))

    # Identify missing content (in expected but not in actual)
    missing = []
    extra = []

    for line in diff:
        if line.startswith('-') and not line.startswith('---'):
            missing.append(line[1:].strip())
        elif line.startswith('+') and not line.startswith('+++'):
            extra.append(line[1:].strip())

    # Check for encoding issues
    encoding_issues = detect_encoding_issues(actual)

    # Generate diff summary
    if len(diff) > 0:
        diff_summary = ''.join(diff[:50])  # First 50 lines
        if len(diff) > 50:
            diff_summary += f"\n... ({len(diff) - 50} more lines)"
    else:
        diff_summary = "No differences"

    return TextComparison(
        similarity_score=similarity,
        missing_content=missing[:10],  # First 10 items
        extra_content=extra[:10],
        encoding_issues=encoding_issues,
        diff_summary=diff_summary
    )


def extract_numeric_values(text: str) -> List[Tuple[float, str]]:
    """
    Extract all numeric values with their surrounding context.

    Returns:
        List of (value, context) tuples
    """
    # Pattern: number (with optional decimal) followed by optional unit
    pattern = r'(\d+(?:[.,]\d+)?(?:e[+-]?\d+)?)\s*([a-zA-Z°³²/]+)?'

    matches = []
    for match in re.finditer(pattern, text):
        value_str = match.group(1)
        unit = match.group(2) or ""

        # Try to parse the number
        try:
            # Handle European decimal format
            value_str_normalized = value_str.replace(',', '.')
            value = float(value_str_normalized)
            context = text[max(0, match.start()-20):min(len(text), match.end()+20)]
            matches.append((value, context.strip()))
        except ValueError:
            pass

    return matches


def extract_units(text: str) -> List[str]:
    """
    Extract all unit-like strings from text.

    Returns:
        List of unique units found
    """
    # Common unit patterns
    unit_pattern = r'\b(?:m3?/?h?|Nm3?/?h?|mg/Nm3?|mg/m3?|ppm|ppb|degC|°C|mbar|Pa|kPa|bar|kg/h|l/min)\b'

    units = re.findall(unit_pattern, text)
    return list(set(units))
```

## Layer 2: LLM Interpretation Evaluation

### Objective
Given **correctly extracted text**, evaluate whether the LLM correctly interprets it into structured JSON.

### Testing Approach

**Option A: Use Real Document + Real Extraction**
- Test the full pipeline (DocumentService → LLM)
- Cannot isolate whether error is from parsing or interpretation
- ❌ **Problem**: Can't distinguish error sources

**Option B: Use Synthetic Text Input**
- Skip DocumentService, provide clean text directly to LLM
- Tests LLM interpretation in isolation
- ✅ **Benefit**: Pure LLM evaluation

**Option C: Use Both (Recommended)**
- Test full pipeline (Layer 1 + Layer 2)
- Also test LLM with synthetic text inputs
- Can diagnose error attribution

### Layer 2 Test Implementation

```python
# backend/tests/extractor_evaluation/layer2_llm_interpretation/test_unit_parsing.py
import pytest
from app.agents.nodes.extractor import extractor_node

class TestLLMUnitParsing:
    """Test LLM's ability to correctly interpret and preserve units."""

    @pytest.mark.asyncio
    async def test_llm_superscript_normalization(self, create_synthetic_document):
        """Test that LLM normalizes superscript units correctly."""

        # Synthetic document with known text content
        synthetic_text = """
        VOC Measurement Report

        Exhaust Air Parameters:
        Flow rate: 5000 m³/h
        Temperature: 45°C
        """

        # Create temporary document with this text
        doc_path = create_synthetic_document(synthetic_text, filename="test_superscript.txt")

        # Run extractor
        state = {
            "session_id": "test-session",
            "documents": [{
                "filename": "test_superscript.txt",
                "file_path": str(doc_path),
                "mime_type": "text/plain"
            }]
        }

        result = await extractor_node(state)
        extracted_facts = result["extracted_facts"]

        # LLM should normalize to "m3/h" (not "m³/h" or "m^3/h")
        flow_unit = extracted_facts["process_parameters"]["flow_rate"]["unit"]
        assert flow_unit == "m3/h", \
            f"LLM did not normalize superscript unit correctly: {flow_unit}"

        # LLM should normalize to "degC" (not "°C")
        temp_unit = extracted_facts["process_parameters"]["temperature"]["unit"]
        assert temp_unit == "degC", \
            f"LLM did not normalize temperature unit correctly: {temp_unit}"

    @pytest.mark.asyncio
    async def test_llm_european_decimal_parsing(self, create_synthetic_document):
        """Test that LLM correctly parses European decimal format."""

        synthetic_text = """
        Pollutant Measurements

        Toluene: 850,5 mg/Nm3
        Ethyl acetate: 1.250,75 mg/Nm3
        """

        doc_path = create_synthetic_document(synthetic_text, filename="test_decimals.txt")

        state = {
            "session_id": "test-session",
            "documents": [{
                "filename": "test_decimals.txt",
                "file_path": str(doc_path),
                "mime_type": "text/plain"
            }]
        }

        result = await extractor_node(state)
        extracted_facts = result["extracted_facts"]

        pollutants = extracted_facts["pollutant_characterization"]["pollutant_list"]

        # Find Toluene
        toluene = next(p for p in pollutants if p["name"] == "Toluene")
        assert abs(toluene["concentration"] - 850.5) < 0.01, \
            f"LLM did not parse European decimal correctly: {toluene['concentration']}"

        # Find Ethyl acetate with thousands separator
        ethyl_acetate = next(p for p in pollutants if "Ethyl" in p["name"])
        assert abs(ethyl_acetate["concentration"] - 1250.75) < 0.01, \
            f"LLM did not parse thousands separator correctly: {ethyl_acetate['concentration']}"
```

### Fixtures for Layer 2 Testing

```python
# backend/tests/extractor_evaluation/conftest.py (additions)

@pytest.fixture
def create_synthetic_document(tmp_path):
    """
    Factory fixture to create synthetic text documents for testing LLM interpretation.

    This allows us to test the LLM with known, clean input text.
    """
    def _create(text_content: str, filename: str = "test.txt") -> Path:
        doc_path = tmp_path / filename
        doc_path.write_text(text_content, encoding='utf-8')
        return doc_path

    return _create


@pytest.fixture
async def document_service():
    """Provide DocumentService instance for testing."""
    from app.services.document_service import DocumentService
    return DocumentService()
```

## Integrated Testing: Full Pipeline

### Test both layers together to diagnose errors

```python
# backend/tests/extractor_evaluation/test_end_to_end_diagnosis.py
import pytest
from app.services.document_service import DocumentService
from app.agents.nodes.extractor import extractor_node
from .utils.text_comparators import compare_extracted_text
from .utils.comparators import deep_compare_extraction


class TestEndToEndDiagnosis:
    """
    Test full pipeline and diagnose where errors occur.
    """

    @pytest.mark.asyncio
    async def test_full_pipeline_with_diagnosis(
        self,
        test_documents_dir,
        ground_truth_dir
    ):
        """
        Test complete extraction pipeline and diagnose error sources.
        """
        doc_path = test_documents_dir / "pdf" / "case_001_standard.pdf"

        # Load ground truths
        expected_text_path = ground_truth_dir / "text" / "case_001_expected_text.txt"
        expected_json_path = ground_truth_dir / "json" / "case_001_expected.json"

        # STEP 1: Test document parsing quality
        document_service = DocumentService()
        extracted_text = await document_service.extract_text(str(doc_path))

        with open(expected_text_path, 'r') as f:
            expected_text = f.read()

        text_comparison = compare_extracted_text(extracted_text, expected_text)

        # STEP 2: Test LLM interpretation
        state = {
            "session_id": "test-session",
            "documents": [{
                "filename": doc_path.name,
                "file_path": str(doc_path),
                "mime_type": "application/pdf"
            }]
        }

        result = await extractor_node(state)
        extracted_facts = result["extracted_facts"]

        import json
        with open(expected_json_path, 'r') as f:
            expected_data = json.load(f)

        json_comparison = deep_compare_extraction(
            extracted_facts,
            expected_data["expected_extraction"],
            critical_fields=expected_data.get("critical_fields", [])
        )

        # STEP 3: Diagnose errors
        diagnosis = diagnose_error_sources(
            text_comparison,
            json_comparison,
            extracted_text,
            extracted_facts
        )

        # Report
        print("\n" + "="*60)
        print("DIAGNOSTIC REPORT")
        print("="*60)
        print(f"Layer 1 (Document Parsing) Quality: {text_comparison.similarity_score:.2%}")
        print(f"Layer 2 (LLM Interpretation) Quality: {len(json_comparison.matches) / (len(json_comparison.matches) + len(json_comparison.mismatches)):.2%}")
        print(f"\nError Attribution:")
        print(f"  - Document parsing errors: {diagnosis['parsing_errors']}")
        print(f"  - LLM interpretation errors: {diagnosis['llm_errors']}")
        print(f"  - Compounding errors: {diagnosis['compound_errors']}")

        # Assert quality thresholds
        assert text_comparison.similarity_score > 0.95, \
            "Document parsing quality too low"
        assert len(json_comparison.mismatches) < 3, \
            "Too many LLM interpretation errors"


def diagnose_error_sources(text_comparison, json_comparison, extracted_text, extracted_facts):
    """
    Diagnose whether errors originated in document parsing or LLM interpretation.

    Returns:
        {
            "parsing_errors": int,
            "llm_errors": int,
            "compound_errors": int
        }
    """
    parsing_errors = 0
    llm_errors = 0
    compound_errors = 0

    # Check each JSON mismatch
    for mismatch in json_comparison.mismatches:
        # Try to find the expected value in the extracted text
        expected_str = str(mismatch.expected)

        if expected_str in extracted_text:
            # Value was in the text but LLM didn't extract it correctly
            llm_errors += 1
        elif expected_str not in extracted_text and mismatch.expected not in text_comparison.missing_content:
            # Value wasn't in extracted text - parsing error
            parsing_errors += 1
        else:
            # Both layers may have contributed
            compound_errors += 1

    return {
        "parsing_errors": parsing_errors,
        "llm_errors": llm_errors,
        "compound_errors": compound_errors
    }
```

## Updated Metrics

### Layer 1 Metrics (Document Parsing)

```python
from .utils.text_comparators import TextComparison

def calculate_parsing_quality_score(comparison: TextComparison) -> dict:
    """
    Calculate document parsing quality metrics.

    Returns:
        {
            "text_similarity": float,           # Overall similarity
            "encoding_quality": float,          # 1.0 if no encoding issues
            "completeness": float,              # 1.0 if no missing content
            "precision": float,                 # 1.0 if no extra content
        }
    """
    encoding_quality = 1.0 if len(comparison.encoding_issues) == 0 else 0.5
    completeness = 1.0 - (len(comparison.missing_content) / 100)  # Normalize
    precision = 1.0 - (len(comparison.extra_content) / 100)

    return {
        "text_similarity": comparison.similarity_score,
        "encoding_quality": encoding_quality,
        "completeness": max(0.0, completeness),
        "precision": max(0.0, precision),
        "overall_parsing_quality": (
            comparison.similarity_score * 0.5 +
            encoding_quality * 0.2 +
            completeness * 0.2 +
            precision * 0.1
        )
    }
```

### Combined Reporting

```python
def generate_two_layer_report(layer1_results, layer2_results, diagnosis_results):
    """
    Generate comprehensive report covering both layers.
    """
    report = ["# EXTRACTOR Two-Layer Evaluation Report\n"]

    report.append("## Layer 1: Document Parsing Quality\n")
    report.append(f"- Average Text Similarity: {layer1_results['avg_similarity']:.2%}")
    report.append(f"- Encoding Issues: {layer1_results['total_encoding_issues']}")
    report.append(f"- PDF Parsing Accuracy: {layer1_results['pdf_accuracy']:.2%}")
    report.append(f"- Excel Parsing Accuracy: {layer1_results['xlsx_accuracy']:.2%}\n")

    report.append("## Layer 2: LLM Interpretation Quality\n")
    report.append(f"- Overall Accuracy: {layer2_results['overall_accuracy']:.2%}")
    report.append(f"- Unit Parsing Accuracy: {layer2_results['unit_accuracy']:.2%}")
    report.append(f"- Value Parsing Accuracy: {layer2_results['value_accuracy']:.2%}")
    report.append(f"- Structure Accuracy: {layer2_results['structure_accuracy']:.2%}\n")

    report.append("## Error Attribution\n")
    report.append(f"- Document Parsing Errors: {diagnosis_results['parsing_errors']}")
    report.append(f"- LLM Interpretation Errors: {diagnosis_results['llm_errors']}")
    report.append(f"- Compound Errors: {diagnosis_results['compound_errors']}\n")

    return "\n".join(report)
```

## Updated Implementation Roadmap

### Phase 1 (Week 1): Foundation + Layer 1
1. Create test directory structure
2. Implement text comparison utilities
3. Create 3 PDF test documents with expected text ground truth
4. Implement Layer 1 PDF parsing tests
5. Measure baseline document parsing quality

### Phase 2 (Week 2): Layer 1 Completion
1. Create Excel/DOCX/CSV test documents with text ground truth
2. Implement Layer 1 tests for all formats
3. Test encoding issues, table extraction, merged cells
4. Identify document parsing weaknesses

### Phase 3 (Week 3): Layer 2 Foundation
1. Create synthetic text documents for LLM testing
2. Implement Layer 2 unit parsing tests
3. Implement Layer 2 value parsing tests
4. Test LLM interpretation in isolation

### Phase 4 (Week 4): Layer 2 Completion
1. Implement Layer 2 structure mapping tests
2. Test customer question extraction
3. Test carcinogen detection
4. Measure baseline LLM interpretation quality

### Phase 5 (Week 5): Integration & Diagnosis
1. Implement end-to-end diagnostic tests
2. Create error attribution logic
3. Generate comprehensive two-layer reports
4. Identify improvement priorities

### Phase 6 (Week 6): Automation
1. Set up CI/CD for both layers
2. Configure quality thresholds per layer
3. Create automated regression detection
4. Document findings and recommendations

## Success Criteria

The evaluation suite is successful when:

1. **Layer Separation**: Can independently measure Layer 1 and Layer 2 quality
2. **Error Attribution**: Can diagnose whether errors come from parsing or LLM
3. **Baseline Established**: Know current performance of both layers
4. **Regression Detection**: Tests catch degradation in either layer
5. **Actionable Insights**: Reports clearly indicate which component needs improvement

## Key Questions This Strategy Answers

✅ **Is the DocumentService extracting text correctly?**
   - Layer 1 tests with text ground truth

✅ **Is the LLM interpreting the text correctly?**
   - Layer 2 tests with synthetic clean inputs

✅ **Where are errors occurring in the pipeline?**
   - Diagnostic tests with error attribution

✅ **How do different file formats affect quality?**
   - Format-specific Layer 1 tests

✅ **Is the LLM normalizing units correctly?**
   - Layer 2 unit parsing tests with controlled inputs

✅ **Are decimal separators being handled correctly?**
   - Layer 1 tests for extraction + Layer 2 tests for interpretation
