"""Pytest fixtures for EXTRACTOR evaluation tests."""

import pytest
import json
import tempfile
from pathlib import Path
from typing import Callable
from app.services.document_service import DocumentService


@pytest.fixture
def test_documents_dir() -> Path:
    """Return path to test documents directory."""
    return Path(__file__).parent / "test_documents"


@pytest.fixture
def ground_truth_dir(test_documents_dir) -> Path:
    """Return path to ground truth directory."""
    return test_documents_dir / "ground_truth"


@pytest.fixture
def ground_truth_text_dir(ground_truth_dir) -> Path:
    """Return path to ground truth text files (Layer 1 expected outputs)."""
    return ground_truth_dir / "text"


@pytest.fixture
def ground_truth_json_dir(ground_truth_dir) -> Path:
    """Return path to ground truth JSON files (Layer 2 expected outputs)."""
    return ground_truth_dir / "json"


@pytest.fixture
async def document_service() -> DocumentService:
    """Provide DocumentService instance for testing."""
    return DocumentService()


@pytest.fixture
def load_expected_text(ground_truth_text_dir) -> Callable:
    """
    Factory fixture to load expected text results for Layer 1 tests.

    Usage:
        expected_text = load_expected_text("case_001_expected_text.txt")
    """

    def _load(filename: str) -> str:
        text_file = ground_truth_text_dir / filename
        if not text_file.exists():
            raise FileNotFoundError(f"Ground truth text file not found: {text_file}")
        with open(text_file, "r", encoding="utf-8") as f:
            return f.read()

    return _load


@pytest.fixture
def load_expected_json(ground_truth_json_dir) -> Callable:
    """
    Factory fixture to load expected JSON results for Layer 2 tests.

    Usage:
        expected_data = load_expected_json("case_001_expected.json")
    """

    def _load(filename: str) -> dict:
        json_file = ground_truth_json_dir / filename
        if not json_file.exists():
            raise FileNotFoundError(f"Ground truth JSON file not found: {json_file}")
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)

    return _load


@pytest.fixture
async def run_extractor() -> Callable:
    """
    Factory fixture to run extractor on a test document.

    This runs the full EXTRACTOR node (Layer 1 + Layer 2).

    Usage:
        result = await run_extractor(document_path, mime_type="application/pdf")
    """
    from app.agents.nodes.extractor import extractor_node

    async def _run(document_path: Path, mime_type: str = None) -> dict:
        state = {
            "session_id": "test-session",
            "documents": [
                {
                    "filename": document_path.name,
                    "file_path": str(document_path),
                    "mime_type": mime_type or "application/pdf",
                }
            ],
        }
        result = await extractor_node(state)
        return result["extracted_facts"]

    return _run


@pytest.fixture
def create_synthetic_document() -> Callable:
    """
    Factory fixture to create synthetic text documents for Layer 2 testing.

    This allows testing LLM interpretation with known, clean input text.

    Usage:
        doc_path = create_synthetic_document(
            text_content="Flow rate: 5000 m³/h",
            filename="test_units.txt"
        )
    """

    def _create(text_content: str, filename: str = "test.txt") -> Path:
        # Create a temporary file
        temp_dir = Path(tempfile.mkdtemp(prefix="extractor_eval_"))
        doc_path = temp_dir / filename
        doc_path.write_text(text_content, encoding="utf-8")
        return doc_path

    return _create


@pytest.fixture
async def extract_text_only(document_service) -> Callable:
    """
    Factory fixture to extract text from document without running LLM.

    This is for Layer 1 testing only.

    Usage:
        extracted_text = await extract_text_only(document_path, mime_type="application/pdf")
    """

    async def _extract(document_path: Path, mime_type: str = None) -> str:
        return await document_service.extract_text(str(document_path), mime_type)

    return _extract


@pytest.fixture
def assert_no_encoding_issues() -> Callable:
    """
    Fixture to assert that text has no encoding issues.

    Usage:
        assert_no_encoding_issues(extracted_text, "case_001")
    """
    from .utils.text_comparators import detect_encoding_issues

    def _assert(text: str, test_case: str = ""):
        issues = detect_encoding_issues(text)
        assert (
            len(issues) == 0
        ), f"Encoding issues detected in {test_case}:\n" + "\n".join(
            f"  - {issue}" for issue in issues
        )

    return _assert


@pytest.fixture
def assert_unit_format_valid() -> Callable:
    """
    Fixture to assert that a unit string follows valid format.

    Usage:
        assert_unit_format_valid("m3/h", "flow")
    """
    from .utils.validators import validate_unit_format

    def _assert(unit: str, unit_type: str = None, field_path: str = ""):
        assert validate_unit_format(
            unit, unit_type
        ), f"Invalid unit format at {field_path}: {unit}"

    return _assert


@pytest.fixture
def assert_numeric_value_valid() -> Callable:
    """
    Fixture to assert that a value is a valid numeric type.

    Usage:
        assert_numeric_value_valid(850.5, "concentration")
    """
    from .utils.validators import validate_numeric_value

    def _assert(value, field_path: str = ""):
        assert validate_numeric_value(
            value
        ), f"Invalid numeric value at {field_path}: {value} (type: {type(value)})"

    return _assert


@pytest.fixture
def compare_with_tolerance() -> Callable:
    """
    Fixture to compare numeric values with tolerance.

    Usage:
        compare_with_tolerance(actual=850.5, expected=850.0, tolerance=1.0)
    """
    from .utils.comparators import compare_values_with_tolerance

    def _compare(
        actual: float,
        expected: float,
        rel_tol: float = 0.01,
        abs_tol: float = 0.0001,
        field_path: str = "",
    ):
        assert compare_values_with_tolerance(
            actual, expected, rel_tol, abs_tol
        ), f"Value mismatch at {field_path}: expected {expected}, got {actual}"

    return _compare


# Markers for test categorization
def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "layer1: Layer 1 tests (document parsing quality)"
    )
    config.addinivalue_line(
        "markers", "layer2: Layer 2 tests (LLM interpretation quality)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (both layers together)"
    )
    config.addinivalue_line("markers", "pdf: Tests specific to PDF documents")
    config.addinivalue_line("markers", "xlsx: Tests specific to Excel documents")
    config.addinivalue_line("markers", "docx: Tests specific to Word documents")
    config.addinivalue_line("markers", "csv: Tests specific to CSV documents")
    config.addinivalue_line("markers", "unit_parsing: Tests for unit parsing errors")
    config.addinivalue_line(
        "markers", "value_parsing: Tests for numeric value parsing errors"
    )
    config.addinivalue_line(
        "markers", "structure_mapping: Tests for JSON structure mapping errors"
    )
    config.addinivalue_line("markers", "slow: Slow tests (vision API, large documents)")


@pytest.fixture(scope="session")
def test_data_summary():
    """
    Fixture to collect test results for final summary report.

    This can be used to aggregate results across all tests.
    """
    summary = {"layer1_results": [], "layer2_results": [], "diagnostics": []}

    yield summary

    # After all tests complete, could generate a final report here
    # (This would require pytest-html or similar plugin)
