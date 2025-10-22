"""Layer 2 tests - LLM unit parsing quality."""

import pytest
from pathlib import Path


@pytest.mark.layer2
@pytest.mark.unit_parsing
class TestLLMUnitParsing:
    """Test LLM's ability to correctly interpret and normalize units (Layer 2)."""

    @pytest.mark.asyncio
    async def test_llm_superscript_normalization(
        self, run_extractor, create_synthetic_document, assert_unit_format_valid
    ):
        """Test that LLM normalizes superscript units to standard format."""

        # Synthetic document with known text content
        synthetic_text = """
VOC Measurement Report

Exhaust Air Parameters:
Flow rate: 5000 m³/h
Temperature: 45°C
Pressure: -5 mbar
"""

        # Create temporary document with this text
        doc_path = create_synthetic_document(synthetic_text, filename="test_superscript.txt")

        # Run extractor
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        # LLM should normalize to "m3/h" (not "m³/h" or "m^3/h")
        flow_unit = extracted_facts["process_parameters"]["flow_rate"]["unit"]
        assert flow_unit == "m3/h", (
            f"LLM did not normalize superscript unit correctly: '{flow_unit}'\n"
            f"Expected: 'm3/h' (without superscript or caret)"
        )

        # Validate unit format
        assert_unit_format_valid(flow_unit, "flow", "process_parameters.flow_rate.unit")

        # LLM should normalize to "degC" (not "°C")
        temp_unit = extracted_facts["process_parameters"]["temperature"]["unit"]
        assert temp_unit == "degC", (
            f"LLM did not normalize temperature unit correctly: '{temp_unit}'\n"
            f"Expected: 'degC' (not '°C' or 'C')"
        )

        # Validate temperature unit
        assert_unit_format_valid(temp_unit, "temperature", "process_parameters.temperature.unit")

    @pytest.mark.asyncio
    async def test_llm_concentration_unit_preservation(
        self, run_extractor, create_synthetic_document
    ):
        """Test that LLM preserves concentration units exactly as specified."""

        synthetic_text = """
Pollutant Measurements

Toluene: 850.5 mg/Nm3
Ethyl acetate: 420 mg/m3
Methanol: 150 ppm
"""

        doc_path = create_synthetic_document(synthetic_text, filename="test_concentration_units.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        pollutants = extracted_facts["pollutant_characterization"]["pollutant_list"]

        # Find Toluene - should have mg/Nm3
        toluene = next((p for p in pollutants if "Toluene" in p["name"]), None)
        assert toluene is not None, "Toluene not found in extracted pollutants"
        assert toluene["concentration_unit"] == "mg/Nm3", (
            f"Wrong concentration unit for Toluene: {toluene['concentration_unit']}"
        )

        # Find Ethyl acetate - should have mg/m3 (different from Toluene)
        ethyl_acetate = next((p for p in pollutants if "Ethyl" in p["name"]), None)
        assert ethyl_acetate is not None, "Ethyl acetate not found"
        assert ethyl_acetate["concentration_unit"] == "mg/m3", (
            f"Wrong concentration unit for Ethyl acetate: {ethyl_acetate['concentration_unit']}"
        )

        # Find Methanol - should have ppm
        methanol = next((p for p in pollutants if "Methanol" in p["name"]), None)
        assert methanol is not None, "Methanol not found"
        assert methanol["concentration_unit"] == "ppm", (
            f"Wrong concentration unit for Methanol: {methanol['concentration_unit']}"
        )

    @pytest.mark.asyncio
    async def test_llm_unit_case_sensitivity(
        self, run_extractor, create_synthetic_document
    ):
        """Test that LLM handles unit case sensitivity correctly."""

        synthetic_text = """
Process Parameters

Flow: 5000 Nm3/h
Alternative flow: 3000 nm3/h
Concentration: 850 mg/NM3
"""

        doc_path = create_synthetic_document(synthetic_text, filename="test_unit_case.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        # Should normalize to "Nm3/h" (capital N for normal cubic meters)
        flow_unit = extracted_facts["process_parameters"]["flow_rate"]["unit"]
        assert flow_unit in ["Nm3/h", "nm3/h"], (
            f"LLM did not preserve Nm3/h correctly: {flow_unit}"
        )

    @pytest.mark.asyncio
    async def test_llm_pressure_type_recognition(
        self, run_extractor, create_synthetic_document
    ):
        """Test that LLM recognizes pressure type (positive/negative)."""

        synthetic_text = """
Exhaust Air Conditions

Pressure: -5 mbar (negative pressure)
Temperature: 45 degC
"""

        doc_path = create_synthetic_document(synthetic_text, filename="test_pressure_type.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        pressure = extracted_facts["process_parameters"]["pressure"]

        assert pressure["value"] == -5 or pressure["value"] == 5, (
            f"Pressure value not extracted correctly: {pressure['value']}"
        )
        assert pressure["unit"] == "mbar", (
            f"Pressure unit not correct: {pressure['unit']}"
        )
        assert pressure["type"] in ["negative", "vacuum", None], (
            f"LLM did not recognize negative pressure type: {pressure['type']}"
        )

    @pytest.mark.asyncio
    async def test_llm_mixed_unit_formats(
        self, run_extractor, create_synthetic_document
    ):
        """Test LLM handling of mixed unit formats in same document."""

        synthetic_text = """
Measurement Data

Stream A:
- Flow: 5000 m³/h
- Temp: 45°C

Stream B:
- Flow: 3000 m3/h
- Temp: 40 degC
"""

        doc_path = create_synthetic_document(synthetic_text, filename="test_mixed_units.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        # LLM should normalize both to the same format
        flow_unit = extracted_facts["process_parameters"]["flow_rate"]["unit"]
        assert flow_unit == "m3/h", (
            f"LLM did not normalize mixed unit formats consistently: {flow_unit}"
        )

        temp_unit = extracted_facts["process_parameters"]["temperature"]["unit"]
        assert temp_unit == "degC", (
            f"LLM did not normalize temperature units consistently: {temp_unit}"
        )
