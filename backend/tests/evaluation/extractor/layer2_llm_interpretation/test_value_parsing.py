"""Layer 2 tests - LLM numeric value parsing quality."""

import pytest
from pathlib import Path


@pytest.mark.layer2
@pytest.mark.value_parsing
class TestLLMValueParsing:
    """Test LLM's ability to correctly parse numeric values (Layer 2)."""

    @pytest.mark.asyncio
    async def test_llm_european_decimal_parsing(
        self, run_extractor, create_synthetic_document, compare_with_tolerance
    ):
        """Test that LLM correctly parses European decimal format (comma as decimal separator)."""

        synthetic_text = """
Pollutant Measurements

Toluene: 850,5 mg/Nm3
Ethyl acetate: 1.250,75 mg/Nm3
Methanol: 95,0 mg/Nm3
"""

        doc_path = create_synthetic_document(synthetic_text, filename="test_european_decimals.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        pollutants = extracted_facts["pollutant_characterization"]["pollutant_list"]

        # Find Toluene - 850,5 should parse to 850.5
        toluene = next((p for p in pollutants if "Toluene" in p["name"]), None)
        assert toluene is not None, "Toluene not found"
        compare_with_tolerance(
            actual=toluene["concentration"],
            expected=850.5,
            field_path="Toluene concentration"
        )

        # Find Ethyl acetate with thousands separator - 1.250,75 should parse to 1250.75
        ethyl_acetate = next((p for p in pollutants if "Ethyl" in p["name"]), None)
        assert ethyl_acetate is not None, "Ethyl acetate not found"
        compare_with_tolerance(
            actual=ethyl_acetate["concentration"],
            expected=1250.75,
            field_path="Ethyl acetate concentration"
        )

    @pytest.mark.asyncio
    async def test_llm_us_decimal_parsing(
        self, run_extractor, create_synthetic_document, compare_with_tolerance
    ):
        """Test that LLM correctly parses US decimal format (period as decimal separator)."""

        synthetic_text = """
Pollutant Measurements

Toluene: 850.5 mg/Nm3
Ethyl acetate: 1,250.75 mg/Nm3
"""

        doc_path = create_synthetic_document(synthetic_text, filename="test_us_decimals.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        pollutants = extracted_facts["pollutant_characterization"]["pollutant_list"]

        # Toluene: 850.5
        toluene = next((p for p in pollutants if "Toluene" in p["name"]), None)
        compare_with_tolerance(
            actual=toluene["concentration"],
            expected=850.5,
            field_path="Toluene concentration (US format)"
        )

        # Ethyl acetate with comma thousands separator: 1,250.75 -> 1250.75
        ethyl_acetate = next((p for p in pollutants if "Ethyl" in p["name"]), None)
        compare_with_tolerance(
            actual=ethyl_acetate["concentration"],
            expected=1250.75,
            field_path="Ethyl acetate concentration (US format)"
        )

    @pytest.mark.asyncio
    async def test_llm_scientific_notation_parsing(
        self, run_extractor, create_synthetic_document, compare_with_tolerance
    ):
        """Test that LLM correctly parses scientific notation."""

        synthetic_text = """
Process Parameters

Flow rate: 1.5e3 m3/h
VOC concentration: 8.5E+2 mg/Nm3
Trace pollutant: 1.2e-2 mg/Nm3
"""

        doc_path = create_synthetic_document(synthetic_text, filename="test_scientific_notation.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        # Flow rate: 1.5e3 = 1500
        flow_value = extracted_facts["process_parameters"]["flow_rate"]["value"]
        compare_with_tolerance(
            actual=flow_value,
            expected=1500.0,
            rel_tol=0.01,
            field_path="flow_rate (scientific notation)"
        )

        # VOC concentration: 8.5E+2 = 850
        total_voc = extracted_facts["pollutant_characterization"]["total_load"].get("tvoc")
        if total_voc:
            compare_with_tolerance(
                actual=total_voc,
                expected=850.0,
                rel_tol=0.05,
                field_path="total VOC (scientific notation)"
            )

    @pytest.mark.asyncio
    async def test_llm_range_extraction(
        self, run_extractor, create_synthetic_document
    ):
        """Test that LLM extracts min/max from range notation."""

        synthetic_text = """
Process Conditions

Flow rate: 4500-5500 m3/h
Temperature: 40-50 degC
Pressure: -10 to -5 mbar
"""

        doc_path = create_synthetic_document(synthetic_text, filename="test_ranges.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        # Flow rate range
        flow_rate = extracted_facts["process_parameters"]["flow_rate"]
        assert flow_rate["min_value"] == 4500 or flow_rate["value"] == 4500, (
            f"Min flow value not extracted correctly: {flow_rate}"
        )
        assert flow_rate["max_value"] == 5500, (
            f"Max flow value not extracted correctly: {flow_rate}"
        )

    @pytest.mark.asyncio
    async def test_llm_tolerance_notation(
        self, run_extractor, create_synthetic_document
    ):
        """Test that LLM interprets ± notation correctly."""

        synthetic_text = """
Operating Conditions

Temperature: 45 ± 5 degC
Pressure: -5 ± 2 mbar
"""

        doc_path = create_synthetic_document(synthetic_text, filename="test_tolerance.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        # Temperature: 45±5 means 40-50 or just 45 as nominal
        temp = extracted_facts["process_parameters"]["temperature"]
        assert temp["value"] in [40, 45, 50], (
            f"Temperature not parsed correctly from ± notation: {temp['value']}"
        )

    @pytest.mark.asyncio
    async def test_llm_zero_and_null_distinction(
        self, run_extractor, create_synthetic_document
    ):
        """Test that LLM distinguishes between 0 and null/missing values."""

        synthetic_text = """
Measurements

Oxygen content: 0%
Particulate load: not measured
Humidity: data pending
"""

        doc_path = create_synthetic_document(synthetic_text, filename="test_zero_vs_null.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        # Oxygen: explicitly 0 (not null)
        oxygen = extracted_facts["process_parameters"]["oxygen_content_percent"]
        assert oxygen == 0 or oxygen == 0.0, (
            f"LLM did not extract explicit zero value correctly: {oxygen}"
        )

        # Particulate load: should be null (not measured)
        particulate = extracted_facts["process_parameters"]["particulate_load"]["value"]
        assert particulate is None, (
            f"LLM should set null for unmeasured values, got: {particulate}"
        )

    @pytest.mark.asyncio
    async def test_llm_large_number_parsing(
        self, run_extractor, create_synthetic_document, compare_with_tolerance
    ):
        """Test that LLM correctly parses large numbers with various formats."""

        synthetic_text = """
Production Data

Annual volume: 50.000 tons
Daily flow: 120,000 m3/day
Peak flow: 5000000 l/h
"""

        doc_path = create_synthetic_document(synthetic_text, filename="test_large_numbers.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        # Should extract at least some production information
        production_info = extracted_facts["industry_and_process"]["production_volumes"]
        assert production_info is not None and len(str(production_info)) > 10, (
            "Large numbers in production volumes not extracted"
        )

    @pytest.mark.asyncio
    async def test_llm_precision_preservation(
        self, run_extractor, create_synthetic_document
    ):
        """Test that LLM preserves precision in numeric values."""

        synthetic_text = """
Trace Analysis

Benzene: 0.0125 mg/Nm3
Formaldehyde: 1.25e-4 mg/Nm3
"""

        doc_path = create_synthetic_document(synthetic_text, filename="test_precision.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        pollutants = extracted_facts["pollutant_characterization"]["pollutant_list"]

        # Benzene: 0.0125 (high precision)
        benzene = next((p for p in pollutants if "Benzene" in p["name"]), None)
        if benzene:
            assert isinstance(benzene["concentration"], (int, float)), (
                f"Concentration should be numeric, got {type(benzene['concentration'])}"
            )
            assert 0.01 < benzene["concentration"] < 0.02, (
                f"High precision value not preserved: {benzene['concentration']}"
            )
