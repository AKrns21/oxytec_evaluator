"""Layer 2 tests - EXTRACTOR v2.0.0 extraction_notes field quality."""

import pytest
from pathlib import Path


@pytest.mark.layer2
@pytest.mark.extraction_notes
class TestExtractionNotes:
    """Test extraction_notes functionality in EXTRACTOR v2.0.0."""

    @pytest.mark.asyncio
    async def test_missing_cas_number_flagged(
        self, run_extractor, create_synthetic_document
    ):
        """Test that missing CAS numbers are flagged in extraction_notes."""

        synthetic_text = """
        VOC Measurement Report

        Pollutant Measurements:
        - Toluene: 850 mg/Nm3
        - Ethyl acetate: 420 mg/m3
        - Methanol: 150 ppm

        Note: CAS numbers not provided in source data.
        """

        doc_path = create_synthetic_document(synthetic_text, filename="test_missing_cas.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        # Check extraction_notes exists
        extraction_notes = extracted_facts.get("extraction_notes", [])
        assert isinstance(extraction_notes, list), "extraction_notes should be a list"

        # Should flag at least one missing CAS number
        cas_notes = [
            note for note in extraction_notes
            if "cas" in note.get("field", "").lower() or "cas" in note.get("note", "").lower()
        ]

        assert len(cas_notes) > 0, (
            f"Expected extraction_notes for missing CAS numbers. Got: {extraction_notes}"
        )

        # Validate note structure
        for note in cas_notes:
            assert "field" in note, "extraction_note must have 'field'"
            assert "status" in note, "extraction_note must have 'status'"
            assert "note" in note, "extraction_note must have 'note'"
            assert note["status"] in [
                "not_provided_in_documents",
                "missing_in_source",
                "unclear_format",
                "table_empty",
                "extraction_uncertain"
            ], f"Invalid status: {note['status']}"

    @pytest.mark.asyncio
    async def test_unclear_unit_flagged(
        self, run_extractor, create_synthetic_document
    ):
        """Test that unclear units are flagged in extraction_notes."""

        synthetic_text = """
        Process Parameters

        Flow rate: 5000 (unit not specified)
        Temperature: 45
        Pressure: -5
        """

        doc_path = create_synthetic_document(synthetic_text, filename="test_unclear_unit.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        extraction_notes = extracted_facts.get("extraction_notes", [])

        # Should flag unclear units
        unit_notes = [
            note for note in extraction_notes
            if "unit" in note.get("note", "").lower() or "unclear" in note.get("status", "").lower()
        ]

        assert len(unit_notes) > 0, (
            f"Expected extraction_notes for unclear units. Got: {extraction_notes}"
        )

        # At least one should be unclear_format status
        unclear_format_notes = [
            note for note in unit_notes
            if note.get("status") == "unclear_format"
        ]
        assert len(unclear_format_notes) > 0, "Expected at least one 'unclear_format' status"

    @pytest.mark.asyncio
    async def test_not_provided_in_documents(
        self, run_extractor, create_synthetic_document
    ):
        """Test that fields mentioned but not provided are flagged with 'not_provided_in_documents'."""

        synthetic_text = """
        VOC Treatment Inquiry

        Flow rate: 5000 m3/h
        Temperature: 45 degC

        Note: Oxygen content will be measured later.
        Note: Humidity data not available at this time.
        """

        doc_path = create_synthetic_document(synthetic_text, filename="test_not_provided.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        extraction_notes = extracted_facts.get("extraction_notes", [])

        # Should flag oxygen_content or humidity as not_provided_in_documents
        not_provided_notes = [
            note for note in extraction_notes
            if note.get("status") == "not_provided_in_documents"
        ]

        assert len(not_provided_notes) > 0, (
            f"Expected 'not_provided_in_documents' notes for oxygen/humidity. Got: {extraction_notes}"
        )

    @pytest.mark.asyncio
    async def test_no_notes_for_complete_data(
        self, run_extractor, create_synthetic_document
    ):
        """Test that extraction_notes is empty/minimal when all critical data is complete."""

        synthetic_text = """
        VOC Measurement Report

        Pollutants:
        - Toluene (CAS: 108-88-3): 850 mg/Nm3
        - Ethyl acetate (CAS: 141-78-6): 420 mg/Nm3

        Process Parameters:
        - Flow rate: 5000 m3/h (range: 3000-6000 m3/h)
        - Temperature: 45 degC
        - Pressure: -5 mbar (negative pressure)
        - Oxygen content: 21%
        - Humidity: 60% RH

        Industry: Chemical manufacturing
        Process: Solvent coating application
        """

        doc_path = create_synthetic_document(synthetic_text, filename="test_complete.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        extraction_notes = extracted_facts.get("extraction_notes", [])

        # Should have zero or very few notes (only for truly optional fields)
        assert len(extraction_notes) <= 2, (
            f"Expected minimal extraction_notes for complete data. Got {len(extraction_notes)} notes: {extraction_notes}"
        )

    @pytest.mark.asyncio
    async def test_table_empty_status(
        self, run_extractor, create_synthetic_document
    ):
        """Test that empty tables are flagged with 'table_empty' status."""

        synthetic_text = """
        VOC Measurement Report

        Table 1: Pollutant Concentrations
        | Substance | CAS | Concentration |
        |-----------|-----|---------------|
        | (empty)   | (empty) | (empty)   |

        Note: Measurements pending.
        """

        doc_path = create_synthetic_document(synthetic_text, filename="test_empty_table.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        extraction_notes = extracted_facts.get("extraction_notes", [])

        # Should flag empty table
        table_notes = [
            note for note in extraction_notes
            if note.get("status") == "table_empty" or "table" in note.get("note", "").lower()
        ]

        assert len(table_notes) > 0, (
            f"Expected 'table_empty' status for empty table. Got: {extraction_notes}"
        )

    @pytest.mark.asyncio
    async def test_extraction_uncertain_status(
        self, run_extractor, create_synthetic_document
    ):
        """Test that ambiguous data gets 'extraction_uncertain' status."""

        synthetic_text = """
        Process Data

        The exhaust air flow varies between 3000 and 8000, depending on production.
        Temperature is typically around 40-50 degrees.
        We use some kind of solvent, probably ethyl acetate or maybe toluene.
        """

        doc_path = create_synthetic_document(synthetic_text, filename="test_uncertain.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        extraction_notes = extracted_facts.get("extraction_notes", [])

        # Should flag uncertainty in units or substance identification
        uncertain_notes = [
            note for note in extraction_notes
            if note.get("status") in ["extraction_uncertain", "unclear_format"]
        ]

        assert len(uncertain_notes) > 0, (
            f"Expected uncertainty flags for ambiguous data. Got: {extraction_notes}"
        )

    @pytest.mark.asyncio
    async def test_no_severity_ratings_in_notes(
        self, run_extractor, create_synthetic_document
    ):
        """Test that extraction_notes do NOT contain severity ratings (v2.0.0 requirement)."""

        synthetic_text = """
        VOC Inquiry

        Pollutant: Formaldehyde
        Flow rate: Not measured
        Temperature: Unknown
        """

        doc_path = create_synthetic_document(synthetic_text, filename="test_no_severity.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        extraction_notes = extracted_facts.get("extraction_notes", [])

        # Ensure NO severity ratings in extraction_notes
        for note in extraction_notes:
            assert "severity" not in note, (
                f"extraction_notes should NOT have 'severity' field in v2.0.0. Got: {note}"
            )

            # Check that note text doesn't contain severity keywords
            note_text = note.get("note", "").lower()
            severity_keywords = ["critical", "high priority", "severely impacts", "severe"]

            for keyword in severity_keywords:
                assert keyword not in note_text, (
                    f"extraction_notes should not contain business judgments like '{keyword}'. "
                    f"Got: {note['note']}"
                )

    @pytest.mark.asyncio
    async def test_field_path_format(
        self, run_extractor, create_synthetic_document
    ):
        """Test that extraction_notes use correct field path format."""

        synthetic_text = """
        VOC Data

        Pollutants:
        1. Toluene - concentration 850 mg/Nm3 (no CAS)
        2. Ethyl acetate - no concentration data

        Flow rate: 5000 (unit unclear)
        """

        doc_path = create_synthetic_document(synthetic_text, filename="test_field_paths.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        extraction_notes = extracted_facts.get("extraction_notes", [])

        # Validate field path format
        for note in extraction_notes:
            field = note.get("field", "")

            # Should use dot notation or array notation
            assert "." in field or "[" in field, (
                f"Field path should use proper notation (e.g., 'pollutant_list[0].cas_number'). "
                f"Got: {field}"
            )

            # Should not be empty
            assert len(field) > 0, "Field path should not be empty"

    @pytest.mark.asyncio
    async def test_extraction_notes_array_consistency(
        self, run_extractor, create_synthetic_document
    ):
        """Test that extraction_notes maintains consistent structure across multiple issues."""

        synthetic_text = """
        Incomplete Data Report

        Pollutants: Toluene (no CAS, no concentration)
        Flow rate: Not measured
        Temperature: TBD
        Industry: Not specified
        """

        doc_path = create_synthetic_document(synthetic_text, filename="test_consistency.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        extraction_notes = extracted_facts.get("extraction_notes", [])

        # Should have multiple notes
        assert len(extraction_notes) >= 3, (
            f"Expected at least 3 extraction_notes for incomplete data. Got: {len(extraction_notes)}"
        )

        # All notes should have consistent structure
        required_keys = {"field", "status", "note"}
        for i, note in enumerate(extraction_notes):
            assert set(note.keys()) == required_keys, (
                f"extraction_note[{i}] has inconsistent keys. "
                f"Expected {required_keys}, got {set(note.keys())}"
            )

    @pytest.mark.asyncio
    async def test_no_carcinogen_flags_in_extraction_notes(
        self, run_extractor, create_synthetic_document
    ):
        """Test that carcinogen detection is NOT present in extraction_notes (v2.0.0 requirement)."""

        synthetic_text = """
        VOC Analysis

        Pollutants:
        - Formaldehyde: 50 mg/Nm3
        - Benzene: 20 mg/Nm3
        - Ethylene oxide: 5 ppm

        Industry: Chemical manufacturing
        Process: Oxidation reactor exhaust
        """

        doc_path = create_synthetic_document(synthetic_text, filename="test_no_carcinogen.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        extraction_notes = extracted_facts.get("extraction_notes", [])

        # Ensure NO carcinogen-related notes
        carcinogen_keywords = [
            "carcinogen", "carcinogenic", "iarc", "group 1", "group 2a",
            "toxic", "highly toxic", "h350", "cancer"
        ]

        for note in extraction_notes:
            note_text = note.get("note", "").lower()
            for keyword in carcinogen_keywords:
                assert keyword not in note_text, (
                    f"EXTRACTOR v2.0.0 should NOT flag carcinogens. "
                    f"Found '{keyword}' in extraction_note: {note['note']}"
                )

        # Also check data_quality_issues (should not have carcinogen flags)
        data_quality_issues = extracted_facts.get("data_quality_issues", [])
        for issue in data_quality_issues:
            issue_text = issue.get("issue", "").lower()
            for keyword in carcinogen_keywords:
                assert keyword not in issue_text, (
                    f"EXTRACTOR v2.0.0 should NOT flag carcinogens in data_quality_issues. "
                    f"Found '{keyword}' in: {issue['issue']}"
                )
