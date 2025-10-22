"""End-to-end diagnostic tests - Combined Layer 1 + Layer 2 evaluation with error attribution."""

import pytest
from pathlib import Path
from .utils.text_comparators import compare_extracted_text, calculate_parsing_quality_score
from .utils.comparators import deep_compare_extraction
from .utils.metrics import calculate_extraction_score, diagnose_error_sources


@pytest.mark.integration
class TestEndToEndDiagnostic:
    """
    Test full extraction pipeline and diagnose where errors occur.

    These tests run both Layer 1 (document parsing) and Layer 2 (LLM interpretation)
    and provide attribution for where errors originated.
    """

    @pytest.mark.asyncio
    async def test_full_pipeline_with_diagnosis_pdf(
        self,
        extract_text_only,
        run_extractor,
        test_documents_dir,
        load_expected_text,
        load_expected_json,
    ):
        """
        Test complete extraction pipeline on PDF and diagnose error sources.
        """
        doc_path = test_documents_dir / "pdf" / "case_001_standard.pdf"

        if not doc_path.exists():
            pytest.skip(f"Test document not found: {doc_path}")

        # STEP 1: Test Layer 1 (document parsing quality)
        extracted_text = await extract_text_only(doc_path)

        try:
            expected_text = load_expected_text("case_001_expected_text.txt")
            text_comparison = compare_extracted_text(extracted_text, expected_text)
            layer1_score = calculate_parsing_quality_score(text_comparison)
        except FileNotFoundError:
            pytest.skip("Ground truth text file not found for Layer 1 evaluation")

        # STEP 2: Test Layer 2 (LLM interpretation)
        extracted_facts = await run_extractor(doc_path)

        try:
            expected_data = load_expected_json("case_001_expected.json")
            json_comparison = deep_compare_extraction(
                extracted_facts,
                expected_data["expected_extraction"],
                critical_fields=expected_data.get("critical_fields", []),
                acceptable_variations=expected_data.get("acceptable_variations", {}),
            )
            layer2_score = calculate_extraction_score(
                json_comparison, critical_fields=expected_data.get("critical_fields", [])
            )
        except FileNotFoundError:
            pytest.skip("Ground truth JSON file not found for Layer 2 evaluation")

        # STEP 3: Diagnose error sources
        diagnosis = diagnose_error_sources(
            text_comparison, json_comparison, extracted_text, extracted_facts
        )

        # STEP 4: Generate diagnostic report
        print("\n" + "=" * 70)
        print("DIAGNOSTIC REPORT: case_001_standard.pdf")
        print("=" * 70)
        print(
            f"Layer 1 (Document Parsing) Quality: {layer1_score['overall_parsing_quality']:.2%}"
        )
        print(
            f"  - Text Similarity: {layer1_score['text_similarity']:.2%}"
        )
        print(f"  - Encoding Quality: {layer1_score['encoding_quality']:.2%}")
        print(f"  - Completeness: {layer1_score['completeness']:.2%}")
        print(
            f"\nLayer 2 (LLM Interpretation) Quality: {layer2_score['overall_accuracy']:.2%}"
        )
        print(
            f"  - Critical Field Accuracy: {layer2_score['critical_field_accuracy']:.2%}"
        )
        print(f"  - Unit Parsing: {layer2_score['unit_parsing_accuracy']:.2%}")
        print(f"  - Value Parsing: {layer2_score['value_parsing_accuracy']:.2%}")
        print(f"  - Structure Mapping: {layer2_score['structure_accuracy']:.2%}")
        print(f"\nError Attribution:")
        print(f"  - Document Parsing Errors: {diagnosis['parsing_errors']}")
        print(f"  - LLM Interpretation Errors: {diagnosis['llm_errors']}")
        print(f"  - Compound Errors: {diagnosis['compound_errors']}")

        if diagnosis['parsing_errors'] > diagnosis['llm_errors']:
            print(
                "\n🔧 RECOMMENDATION: Focus on improving DocumentService extraction quality"
            )
        elif diagnosis['llm_errors'] > 0:
            print("\n🔧 RECOMMENDATION: Focus on improving LLM prompt engineering")

        print("=" * 70 + "\n")

        # Assert quality thresholds (can be adjusted)
        assert layer1_score['overall_parsing_quality'] > 0.90, (
            f"Layer 1 quality too low: {layer1_score['overall_parsing_quality']:.2%}"
        )
        assert layer2_score['overall_accuracy'] > 0.85, (
            f"Layer 2 quality too low: {layer2_score['overall_accuracy']:.2%}"
        )

    @pytest.mark.asyncio
    async def test_full_pipeline_with_diagnosis_xlsx(
        self,
        extract_text_only,
        run_extractor,
        test_documents_dir,
        load_expected_text,
        load_expected_json,
    ):
        """
        Test complete extraction pipeline on Excel and diagnose error sources.
        """
        doc_path = test_documents_dir / "xlsx" / "case_001_measurement_table.xlsx"

        if not doc_path.exists():
            pytest.skip(f"Test document not found: {doc_path}")

        # STEP 1: Layer 1 evaluation
        extracted_text = await extract_text_only(
            doc_path,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        try:
            expected_text = load_expected_text(
                "case_001_measurement_table_expected_text.txt"
            )
            text_comparison = compare_extracted_text(extracted_text, expected_text)
            layer1_score = calculate_parsing_quality_score(text_comparison)
        except FileNotFoundError:
            pytest.skip("Ground truth text file not found for Layer 1 evaluation")

        # STEP 2: Layer 2 evaluation
        extracted_facts = await run_extractor(
            doc_path,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        try:
            expected_data = load_expected_json(
                "case_001_measurement_table_expected.json"
            )
            json_comparison = deep_compare_extraction(
                extracted_facts,
                expected_data["expected_extraction"],
                critical_fields=expected_data.get("critical_fields", []),
            )
            layer2_score = calculate_extraction_score(
                json_comparison, critical_fields=expected_data.get("critical_fields", [])
            )
        except FileNotFoundError:
            pytest.skip("Ground truth JSON file not found for Layer 2 evaluation")

        # STEP 3: Diagnose
        diagnosis = diagnose_error_sources(
            text_comparison, json_comparison, extracted_text, extracted_facts
        )

        # STEP 4: Report
        print("\n" + "=" * 70)
        print("DIAGNOSTIC REPORT: case_001_measurement_table.xlsx")
        print("=" * 70)
        print(
            f"Layer 1 (Excel Parsing) Quality: {layer1_score['overall_parsing_quality']:.2%}"
        )
        print(
            f"Layer 2 (LLM Interpretation) Quality: {layer2_score['overall_accuracy']:.2%}"
        )
        print(f"\nError Attribution:")
        print(f"  - Parsing Errors: {diagnosis['parsing_errors']}")
        print(f"  - LLM Errors: {diagnosis['llm_errors']}")
        print(f"  - Compound Errors: {diagnosis['compound_errors']}")
        print("=" * 70 + "\n")

        # Excel-specific checks
        if text_comparison.similarity_score < 0.85:
            print("⚠️  Excel table structure may not be preserved well")

    @pytest.mark.asyncio
    async def test_error_attribution_unit_parsing(
        self,
        extract_text_only,
        run_extractor,
        test_documents_dir,
    ):
        """
        Test error attribution for unit parsing issues.

        This test helps determine if unit errors come from document parsing or LLM interpretation.
        """
        doc_path = test_documents_dir / "pdf" / "case_unit_002_superscript.pdf"

        if not doc_path.exists():
            pytest.skip(f"Test document not found: {doc_path}")

        # Extract text
        extracted_text = await extract_text_only(doc_path)

        # Check if units are in the extracted text
        has_m3h = "m3/h" in extracted_text or "m³/h" in extracted_text or "m3h" in extracted_text

        # Run full extraction
        extracted_facts = await run_extractor(doc_path)

        flow_unit = extracted_facts["process_parameters"]["flow_rate"]["unit"]

        # Diagnose
        if has_m3h and flow_unit != "m3/h":
            print("\n❌ Layer 2 Error: Unit was in extracted text but LLM did not normalize it correctly")
            print(f"   Extracted text contains: {extracted_text[:200]}...")
            print(f"   LLM outputted: {flow_unit}")
        elif not has_m3h:
            print("\n❌ Layer 1 Error: Unit not correctly extracted from document")
            print(f"   Extracted text: {extracted_text[:200]}...")
        else:
            print("\n✅ Both layers working correctly for unit extraction")

    @pytest.mark.asyncio
    async def test_error_attribution_value_parsing(
        self,
        extract_text_only,
        run_extractor,
        test_documents_dir,
    ):
        """
        Test error attribution for numeric value parsing issues.
        """
        doc_path = test_documents_dir / "xlsx" / "case_value_001_decimal_comma.xlsx"

        if not doc_path.exists():
            pytest.skip(f"Test document not found: {doc_path}")

        # Extract text
        extracted_text = await extract_text_only(
            doc_path,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        # Check if the value "850" or "850,5" or "850.5" is in extracted text
        has_concentration = (
            "850" in extracted_text
            or "850,5" in extracted_text
            or "850.5" in extracted_text
        )

        # Run full extraction
        extracted_facts = await run_extractor(
            doc_path,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        pollutants = extracted_facts["pollutant_characterization"]["pollutant_list"]

        # Look for concentration value around 850
        found_concentration = any(
            p.get("concentration") and 840 < p["concentration"] < 860
            for p in pollutants
        )

        # Diagnose
        if has_concentration and not found_concentration:
            print("\n❌ Layer 2 Error: Value was in extracted text but LLM did not parse it correctly")
            print(f"   Extracted text contains concentration value")
            print(f"   LLM pollutants: {pollutants}")
        elif not has_concentration:
            print("\n❌ Layer 1 Error: Value not correctly extracted from Excel")
            print(f"   Extracted text: {extracted_text[:300]}...")
        else:
            print("\n✅ Both layers working correctly for value extraction")
