"""Layer 1 tests - Excel document parsing quality."""

import pytest
from pathlib import Path
from ..utils.text_comparators import (
    compare_extracted_text,
    extract_numeric_values,
    check_table_preservation,
)


@pytest.mark.layer1
@pytest.mark.xlsx
class TestXLSXParsing:
    """Test DocumentService Excel extraction quality (Layer 1)."""

    @pytest.mark.asyncio
    async def test_xlsx_decimal_comma_preservation(
        self, extract_text_only, test_documents_dir
    ):
        """Test that decimal commas in Excel are preserved or correctly interpreted."""
        doc_path = test_documents_dir / "xlsx" / "case_value_001_decimal_comma.xlsx"

        if not doc_path.exists():
            pytest.skip(f"Test document not found: {doc_path}")

        extracted_text = await extract_text_only(
            doc_path, mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Extract numeric values
        numeric_values = extract_numeric_values(extracted_text)

        # Should find the value 850.5 (whether written as "850,5" or "850.5" in original)
        has_concentration = any(
            840 < value < 860 for value, _, _ in numeric_values
        )
        assert has_concentration, (
            f"Expected concentration value (~850.5) not found. "
            f"Values extracted: {numeric_values[:10]}"
        )

    @pytest.mark.asyncio
    async def test_xlsx_merged_cells(
        self, extract_text_only, test_documents_dir
    ):
        """Test extraction from Excel with merged cells."""
        doc_path = test_documents_dir / "xlsx" / "case_xlsx_001_merged_cells.xlsx"

        if not doc_path.exists():
            pytest.skip(f"Test document not found: {doc_path}")

        extracted_text = await extract_text_only(
            doc_path, mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Check that merged cell content appears
        # Typical merged cells contain section headers
        assert len(extracted_text) > 50, "Extracted text too short - merged cells may not have been read"

        # Check table structure
        table_check = check_table_preservation(extracted_text)
        assert table_check["has_table_markers"] or len(extracted_text.split("\n")) > 3, (
            "No table structure detected - merged cells extraction may have failed"
        )

    @pytest.mark.asyncio
    async def test_xlsx_multiple_sheets(
        self, extract_text_only, test_documents_dir
    ):
        """Test extraction from Excel with multiple sheets."""
        doc_path = test_documents_dir / "xlsx" / "case_xlsx_002_multiple_sheets.xlsx"

        if not doc_path.exists():
            pytest.skip(f"Test document not found: {doc_path}")

        extracted_text = await extract_text_only(
            doc_path, mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Should extract from all sheets
        # Look for sheet indicators or sufficient content length
        word_count = len(extracted_text.split())
        assert word_count > 50, (
            f"Extracted text too short ({word_count} words) - "
            "multiple sheets may not have been extracted"
        )

    @pytest.mark.asyncio
    async def test_xlsx_formulas_vs_values(
        self, extract_text_only, test_documents_dir
    ):
        """Test that cell values (not formulas) are extracted."""
        doc_path = test_documents_dir / "xlsx" / "case_xlsx_004_formulas.xlsx"

        if not doc_path.exists():
            pytest.skip(f"Test document not found: {doc_path}")

        extracted_text = await extract_text_only(
            doc_path, mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Should NOT contain formula syntax
        assert "=SUM(" not in extracted_text, "Formula syntax found in extracted text - should extract values only"
        assert "=AVERAGE(" not in extracted_text, "Formula syntax found in extracted text"

        # Should contain actual numeric values
        numeric_values = extract_numeric_values(extracted_text)
        assert len(numeric_values) > 0, "No numeric values extracted - formulas may not have been evaluated"

    @pytest.mark.asyncio
    async def test_xlsx_thousands_separator(
        self, extract_text_only, test_documents_dir
    ):
        """Test correct handling of thousands separators in Excel."""
        doc_path = test_documents_dir / "csv" / "case_value_006_thousands.csv"

        if not doc_path.exists():
            pytest.skip(f"Test document not found: {doc_path}")

        extracted_text = await extract_text_only(doc_path, mime_type="text/csv")

        # Extract numeric values
        numeric_values = extract_numeric_values(extracted_text)

        # Should find value 5000 (whether written as "5.000" or "5,000" in original)
        has_flow_value = any(
            4500 < value < 5500 for value, _, _ in numeric_values
        )
        assert has_flow_value, (
            f"Expected flow value (~5000) not found. "
            f"Values extracted: {numeric_values[:10]}"
        )

    @pytest.mark.asyncio
    async def test_xlsx_table_structure_preservation(
        self, extract_text_only, test_documents_dir, load_expected_text
    ):
        """Test that Excel table structure is preserved in extracted text."""
        doc_path = test_documents_dir / "xlsx" / "case_001_measurement_table.xlsx"

        if not doc_path.exists():
            pytest.skip(f"Test document not found: {doc_path}")

        extracted_text = await extract_text_only(
            doc_path, mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        try:
            expected_text = load_expected_text("case_001_measurement_table_expected_text.txt")
            comparison = compare_extracted_text(extracted_text, expected_text)
            assert comparison.similarity_score > 0.90, (
                f"Table structure not preserved well enough: {comparison.similarity_score:.2%}"
            )
        except FileNotFoundError:
            # If no ground truth, do basic checks
            table_check = check_table_preservation(extracted_text)
            assert table_check["has_table_markers"] or len(extracted_text.split("\n")) > 5, (
                "Table structure not detected in Excel extraction"
            )
