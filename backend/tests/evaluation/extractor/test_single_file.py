"""
Quick test script to evaluate a single Excel file and show diagnostic results.

Usage:
    python tests/extractor_evaluation/test_single_file.py <filename>

Example:
    python tests/extractor_evaluation/test_single_file.py 20250926_Messdaten_condensed.xlsx
"""

import asyncio
import sys
import json
from pathlib import Path
from utils.text_comparators import (
    compare_extracted_text,
    calculate_parsing_quality_score,
    extract_units,
    extract_numeric_values,
    check_table_preservation
)
from utils.comparators import deep_compare_extraction
from utils.metrics import calculate_extraction_score, diagnose_error_sources

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.document_service import DocumentService
from app.agents.nodes.extractor import extractor_node


async def test_file(filename: str):
    """Test a single Excel file and show diagnostic report."""

    test_docs_dir = Path(__file__).parent / "test_documents" / "xlsx"
    file_path = test_docs_dir / filename

    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return

    print("\n" + "="*70)
    print(f"TESTING: {filename}")
    print("="*70)

    # === LAYER 1: Document Parsing ===
    print("\n📄 LAYER 1: Document Parsing Quality")
    print("-"*70)

    doc_service = DocumentService()
    extracted_text = await doc_service.extract_text(
        str(file_path),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    print(f"✓ Extracted {len(extracted_text)} characters")
    print(f"\nFirst 500 characters:")
    print(extracted_text[:500])
    print("...")

    # Check for encoding issues
    from utils.text_comparators import detect_encoding_issues
    encoding_issues = detect_encoding_issues(extracted_text)

    if encoding_issues:
        print(f"\n⚠️  Encoding Issues Detected:")
        for issue in encoding_issues:
            print(f"   - {issue}")
    else:
        print("\n✓ No encoding issues detected")

    # Extract units
    units = extract_units(extracted_text)
    print(f"\n📏 Units found: {units[:10]}")

    # Extract numeric values
    numeric_values = extract_numeric_values(extracted_text)
    print(f"\n🔢 Numeric values found: {len(numeric_values)}")
    if numeric_values:
        print(f"   Sample values:")
        for val, unit, context in numeric_values[:5]:
            print(f"   - {val} {unit} (context: ...{context[:50]}...)")

    # Check table structure
    table_check = check_table_preservation(extracted_text)
    print(f"\n📊 Table structure:")
    print(f"   - Has table markers: {table_check['has_table_markers']}")
    print(f"   - Potential tables: {table_check['potential_tables']}")
    print(f"   - Separators: {table_check['column_separators']}")

    # === LAYER 2: LLM Interpretation ===
    print("\n" + "="*70)
    print("🤖 LAYER 2: LLM Interpretation Quality")
    print("-"*70)

    state = {
        "session_id": "test-single-file",
        "documents": [{
            "filename": filename,
            "file_path": str(file_path),
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }]
    }

    result = await extractor_node(state)
    extracted_facts = result.get("extracted_facts", {})

    print("✓ EXTRACTOR completed")

    # Show key extracted data
    print("\n📊 Extracted Data Summary:")
    print("-"*70)

    # Pollutants
    pollutants = extracted_facts.get("pollutant_characterization", {}).get("pollutant_list", [])
    print(f"\n🧪 Pollutants: {len(pollutants)}")
    for i, p in enumerate(pollutants[:5], 1):
        name = p.get('name', 'N/A')
        conc = p.get('concentration', 'N/A')
        unit = p.get('concentration_unit', '')
        cas = p.get('cas_number', '')
        print(f"   {i}. {name} ({cas}): {conc} {unit}")

    if len(pollutants) > 5:
        print(f"   ... and {len(pollutants) - 5} more")

    # Process parameters
    print(f"\n⚙️  Process Parameters:")
    process_params = extracted_facts.get("process_parameters", {})

    flow_rate = process_params.get("flow_rate", {})
    if flow_rate.get("value"):
        print(f"   - Flow rate: {flow_rate.get('value')} {flow_rate.get('unit', '')}")

    temp = process_params.get("temperature", {})
    if temp.get("value"):
        print(f"   - Temperature: {temp.get('value')} {temp.get('unit', '')}")

    pressure = process_params.get("pressure", {})
    if pressure.get("value"):
        print(f"   - Pressure: {pressure.get('value')} {pressure.get('unit', '')} ({pressure.get('type', '')})")

    humidity = process_params.get("humidity", {})
    if humidity.get("value"):
        print(f"   - Humidity: {humidity.get('value')} {humidity.get('unit', '')} ({humidity.get('type', '')})")

    # Industry
    industry = extracted_facts.get("industry_and_process", {})
    if industry.get("industry_sector"):
        print(f"\n🏭 Industry: {industry.get('industry_sector')}")
        if industry.get("specific_processes"):
            print(f"   Process: {industry.get('specific_processes')}")

    # Customer questions
    questions = extracted_facts.get("customer_specific_questions", [])
    if questions:
        print(f"\n❓ Customer Questions: {len(questions)}")
        for i, q in enumerate(questions[:3], 1):
            print(f"   {i}. [{q.get('priority')}] {q.get('question_text', 'N/A')[:100]}")

    # Data quality issues
    quality_issues = extracted_facts.get("data_quality_issues", [])
    if quality_issues:
        print(f"\n⚠️  Data Quality Issues: {len(quality_issues)}")
        for i, issue in enumerate(quality_issues[:3], 1):
            print(f"   {i}. [{issue.get('severity')}] {issue.get('issue', 'N/A')}")

    # === COMPARISON WITH GROUND TRUTH (if exists) ===
    print("\n" + "="*70)
    print("📋 COMPARISON WITH GROUND TRUTH")
    print("-"*70)

    # Try to find ground truth files
    base_name = filename.replace('.xlsx', '')
    ground_truth_dir = Path(__file__).parent / "test_documents" / "ground_truth"

    # Find matching ground truth files
    text_files = list((ground_truth_dir / "text").glob(f"*{base_name}*"))
    json_files = list((ground_truth_dir / "json").glob(f"*{base_name}*"))

    if text_files:
        print(f"\n✓ Found ground truth text file: {text_files[0].name}")
        expected_text = text_files[0].read_text(encoding='utf-8')

        text_comparison = compare_extracted_text(extracted_text, expected_text)
        layer1_score = calculate_parsing_quality_score(text_comparison)

        print(f"\nLayer 1 Quality Scores:")
        print(f"  - Text Similarity: {layer1_score['text_similarity']:.2%}")
        print(f"  - Encoding Quality: {layer1_score['encoding_quality']:.2%}")
        print(f"  - Completeness: {layer1_score['completeness']:.2%}")
        print(f"  - Overall: {layer1_score['overall_parsing_quality']:.2%}")

        if text_comparison.similarity_score < 0.90:
            print(f"\n⚠️  Text similarity is low. Differences:")
            print(text_comparison.diff_summary[:500])
    else:
        print(f"\n⚠️  No ground truth text file found")
        print(f"   Run: python tests/extractor_evaluation/create_ground_truth_from_xlsx.py")

    if json_files:
        print(f"\n✓ Found ground truth JSON file: {json_files[0].name}")

        with open(json_files[0], 'r', encoding='utf-8') as f:
            expected_data = json.load(f)

        json_comparison = deep_compare_extraction(
            extracted_facts,
            expected_data["expected_extraction"],
            critical_fields=expected_data.get("critical_fields", [])
        )

        layer2_score = calculate_extraction_score(
            json_comparison,
            critical_fields=expected_data.get("critical_fields", [])
        )

        print(f"\nLayer 2 Quality Scores:")
        print(f"  - Overall Accuracy: {layer2_score['overall_accuracy']:.2%}")
        print(f"  - Critical Fields: {layer2_score['critical_field_accuracy']:.2%}")
        print(f"  - Unit Parsing: {layer2_score['unit_parsing_accuracy']:.2%}")
        print(f"  - Value Parsing: {layer2_score['value_parsing_accuracy']:.2%}")
        print(f"  - Structure: {layer2_score['structure_accuracy']:.2%}")

        # Show errors
        if layer2_score['error_breakdown']['unit_errors'] > 0:
            print(f"\n⚠️  Unit Errors: {layer2_score['error_breakdown']['unit_errors']}")
            for err in layer2_score['detailed_errors']['unit_errors'][:3]:
                print(f"   - {err['field']}: expected '{err['expected']}', got '{err['actual']}'")

        if layer2_score['error_breakdown']['value_errors'] > 0:
            print(f"\n⚠️  Value Errors: {layer2_score['error_breakdown']['value_errors']}")
            for err in layer2_score['detailed_errors']['value_errors'][:3]:
                print(f"   - {err['field']}: expected {err['expected']}, got {err['actual']}")

        # Diagnose error sources
        if text_files:
            diagnosis = diagnose_error_sources(
                text_comparison,
                json_comparison,
                extracted_text,
                extracted_facts
            )

            print(f"\n🔍 Error Attribution:")
            print(f"  - Document Parsing Errors: {diagnosis['parsing_errors']}")
            print(f"  - LLM Interpretation Errors: {diagnosis['llm_errors']}")
            print(f"  - Compound Errors: {diagnosis['compound_errors']}")

            if diagnosis['llm_errors'] > diagnosis['parsing_errors']:
                print(f"\n🔧 RECOMMENDATION: Focus on improving LLM prompt engineering")
                print(f"   → Review prompts in: app/agents/nodes/extractor.py")
            elif diagnosis['parsing_errors'] > diagnosis['llm_errors']:
                print(f"\n🔧 RECOMMENDATION: Focus on improving DocumentService Excel extraction")
                print(f"   → Review extraction in: app/services/document_service.py")
    else:
        print(f"\n⚠️  No ground truth JSON file found")
        print(f"   Run: python tests/extractor_evaluation/create_ground_truth_from_xlsx.py")

    print("\n" + "="*70)
    print("✓ TEST COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_single_file.py <filename>")
        print("\nAvailable files:")
        test_docs_dir = Path(__file__).parent / "test_documents" / "xlsx"
        for f in test_docs_dir.glob("*.xlsx"):
            print(f"  - {f.name}")
        sys.exit(1)

    filename = sys.argv[1]
    asyncio.run(test_file(filename))
