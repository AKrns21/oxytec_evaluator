"""Layer 1 tests - PDF document parsing quality."""

import pytest
from pathlib import Path
from ..utils.text_comparators import (
    compare_extracted_text,
    extract_units,
    extract_numeric_values,
    check_table_preservation,
)


@pytest.mark.layer1
@pytest.mark.pdf
class TestPDFParsing:
    """Test DocumentService PDF extraction quality (Layer 1)."""

    @pytest.mark.asyncio
    async def test_pdf_standard_text_extraction(
        self, extract_text_only, test_documents_dir, load_expected_text
    ):
        """Test extraction from standard text-based PDF."""
        doc_path = test_documents_dir / "pdf" / "case_001_standard.pdf"

        # Skip if test document doesn't exist yet
        if not doc_path.exists():
            pytest.skip(f"Test document not found: {doc_path}")

        # Extract text using DocumentService
        extracted_text = await extract_text_only(doc_path)

        # Load expected text
        expected_text = load_expected_text("case_001_expected_text.txt")

        # Compare with normalization
        comparison = compare_extracted_text(extracted_text, expected_text)

        assert (
            comparison.similarity_score > 0.95
        ), f"Text extraction quality too low: {comparison.similarity_score:.2%}\n" f"Differences:\n{comparison.diff_summary}"

    @pytest.mark.asyncio
    async def test_pdf_unit_preservation(
        self, extract_text_only, test_documents_dir, assert_no_encoding_issues
    ):
        """Test that units are correctly extracted from PDF without corruption."""
        doc_path = test_documents_dir / "pdf" / "case_unit_002_superscript.pdf"

        if not doc_path.exists():
            pytest.skip(f"Test document not found: {doc_path}")

        extracted_text = await extract_text_only(doc_path)

        # Check for encoding issues
        assert_no_encoding_issues(extracted_text, "case_unit_002")

        # Extract units from text
        units = extract_units(extracted_text)

        # Should find flow rate unit (either m3/h or m³/h is acceptable at this layer)
        flow_units = [u for u in units if "m" in u.lower() and "h" in u.lower()]
        assert len(flow_units) > 0, f"Flow rate unit not found in extracted text. Units found: {units}"

        # Should NOT have garbled encoding like "mÂ³"
        assert "mÂ³" not in extracted_text, "Encoding issues detected in unit extraction"
        assert "Â°" not in extracted_text, "Encoding issues detected in degree symbol"

    @pytest.mark.asyncio
    async def test_pdf_table_extraction(
        self, extract_text_only, test_documents_dir
    ):
        """Test that tables are extracted in readable format."""
        doc_path = test_documents_dir / "pdf" / "case_003_table_heavy.pdf"

        if not doc_path.exists():
            pytest.skip(f"Test document not found: {doc_path}")

        extracted_text = await extract_text_only(doc_path)

        # Check table preservation
        table_check = check_table_preservation(extracted_text)

        assert table_check["has_table_markers"], "No table structure markers found in extracted text"

        # Check for key table content (substance names, CAS numbers, values)
        assert "Toluene" in extracted_text or "toluene" in extracted_text, "Pollutant name not extracted"
        assert "108" in extracted_text and "88" in extracted_text, "CAS number components not extracted"

        # Check for numeric values
        numeric_values = extract_numeric_values(extracted_text)
        assert len(numeric_values) > 3, f"Too few numeric values extracted: {len(numeric_values)}"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_pdf_scanned_with_vision_fallback(
        self, extract_text_only, test_documents_dir, load_expected_text
    ):
        """Test vision API fallback for scanned PDFs (OCR)."""
        doc_path = test_documents_dir / "pdf" / "case_pdf_001_scanned.pdf"

        if not doc_path.exists():
            pytest.skip(f"Test document not found: {doc_path}")

        extracted_text = await extract_text_only(doc_path)

        expected_text = load_expected_text("case_pdf_001_expected_text.txt")

        comparison = compare_extracted_text(extracted_text, expected_text)

        # Lower threshold for OCR (vision API) - 85% is acceptable
        assert (
            comparison.similarity_score > 0.85
        ), f"Vision API extraction quality too low: {comparison.similarity_score:.2%}\n" f"This test uses OCR, so some degradation is expected.\n" f"Differences:\n{comparison.diff_summary}"

    @pytest.mark.asyncio
    async def test_pdf_numeric_value_preservation(
        self, extract_text_only, test_documents_dir
    ):
        """Test that numeric values are extracted with correct decimal separators."""
        doc_path = test_documents_dir / "pdf" / "case_value_003_scientific.pdf"

        if not doc_path.exists():
            pytest.skip(f"Test document not found: {doc_path}")

        extracted_text = await extract_text_only(doc_path)

        # Extract numeric values
        numeric_values = extract_numeric_values(extracted_text)

        # Should find values with units
        assert len(numeric_values) > 0, "No numeric values extracted from PDF"

        # Check that scientific notation is preserved or converted correctly
        # Document should contain "1.5e3" or "1500"
        has_large_value = any(value > 1000 for value, _, _ in numeric_values)
        assert has_large_value, f"Expected large value (>1000) not found. Values: {numeric_values}"

    @pytest.mark.asyncio
    async def test_pdf_multipage_extraction(
        self, extract_text_only, test_documents_dir
    ):
        """Test extraction from multi-page PDF."""
        doc_path = test_documents_dir / "pdf" / "case_002_multipage.pdf"

        if not doc_path.exists():
            pytest.skip(f"Test document not found: {doc_path}")

        extracted_text = await extract_text_only(doc_path)

        # Should contain page markers
        assert "Page 1" in extracted_text or "--- Page 1 ---" in extracted_text, "Page 1 marker not found"

        # Should extract content from multiple pages
        page_count = extracted_text.count("Page") or extracted_text.count("---")
        assert page_count >= 2, f"Expected multi-page extraction, found {page_count} page markers"
