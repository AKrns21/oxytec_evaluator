"""
Helper script to create ground truth files from existing Excel test documents.

Usage:
    cd backend
    python tests/extractor_evaluation/create_ground_truth_from_xlsx.py
"""

import asyncio
import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.document_service import DocumentService
from app.agents.nodes.extractor import extractor_node


async def create_ground_truth_for_file(file_path: Path, output_name: str):
    """
    Create ground truth text and JSON files for a given Excel document.

    Args:
        file_path: Path to Excel file
        output_name: Base name for output files (e.g., "case_001")
    """
    print(f"\n{'='*70}")
    print(f"Processing: {file_path.name}")
    print(f"{'='*70}")

    # Step 1: Extract text (Layer 1)
    print("\n[Layer 1] Extracting text from Excel...")
    doc_service = DocumentService()
    extracted_text = await doc_service.extract_text(
        str(file_path),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    print(f"✓ Extracted {len(extracted_text)} characters")
    print(f"\nFirst 500 characters:")
    print("-" * 70)
    print(extracted_text[:500])
    print("-" * 70)

    # Save extracted text as ground truth
    text_output_path = Path(__file__).parent / "test_documents" / "ground_truth" / "text" / f"{output_name}_expected_text.txt"
    text_output_path.write_text(extracted_text, encoding='utf-8')
    print(f"\n✓ Saved ground truth text to: {text_output_path.name}")

    # Step 2: Run extractor (Layer 2)
    print("\n[Layer 2] Running EXTRACTOR agent...")
    state = {
        "session_id": "ground-truth-generation",
        "documents": [{
            "filename": file_path.name,
            "file_path": str(file_path),
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }]
    }

    result = await extractor_node(state)
    extracted_facts = result.get("extracted_facts", {})

    print(f"✓ EXTRACTOR completed")

    # Display key fields
    print(f"\n📊 Key Extracted Data:")
    print("-" * 70)

    # Pollutants
    pollutants = extracted_facts.get("pollutant_characterization", {}).get("pollutant_list", [])
    print(f"Pollutants found: {len(pollutants)}")
    for i, p in enumerate(pollutants[:3], 1):
        print(f"  {i}. {p.get('name', 'N/A')}: {p.get('concentration', 'N/A')} {p.get('concentration_unit', '')}")

    # Flow rate
    flow_rate = extracted_facts.get("process_parameters", {}).get("flow_rate", {})
    if flow_rate.get("value"):
        print(f"Flow rate: {flow_rate.get('value')} {flow_rate.get('unit', '')}")

    # Temperature
    temp = extracted_facts.get("process_parameters", {}).get("temperature", {})
    if temp.get("value"):
        print(f"Temperature: {temp.get('value')} {temp.get('unit', '')}")

    print("-" * 70)

    # Create ground truth JSON structure
    ground_truth = {
        "test_case_id": output_name,
        "description": f"Ground truth generated from {file_path.name}",
        "difficulty": "medium",
        "format": "xlsx",
        "focus_areas": ["pollutant_extraction", "value_parsing"],
        "expected_extraction": extracted_facts,
        "critical_fields": [
            # Add critical fields based on what was extracted
        ],
        "acceptable_variations": {}
    }

    # Automatically identify critical fields (fields with actual data)
    critical_fields = []

    # Add pollutant fields
    for i in range(len(pollutants)):
        if pollutants[i].get("name"):
            critical_fields.append(f"pollutant_characterization.pollutant_list[{i}].name")
        if pollutants[i].get("concentration") is not None:
            critical_fields.append(f"pollutant_characterization.pollutant_list[{i}].concentration")
            critical_fields.append(f"pollutant_characterization.pollutant_list[{i}].concentration_unit")

    # Add flow rate if present
    if flow_rate.get("value"):
        critical_fields.extend([
            "process_parameters.flow_rate.value",
            "process_parameters.flow_rate.unit"
        ])

    # Add temperature if present
    if temp.get("value"):
        critical_fields.extend([
            "process_parameters.temperature.value",
            "process_parameters.temperature.unit"
        ])

    ground_truth["critical_fields"] = critical_fields

    # Save ground truth JSON
    json_output_path = Path(__file__).parent / "test_documents" / "ground_truth" / "json" / f"{output_name}_expected.json"
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(ground_truth, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Saved ground truth JSON to: {json_output_path.name}")
    print(f"  - Critical fields: {len(critical_fields)}")

    print(f"\n{'='*70}")
    print(f"✓ Ground truth files created for {output_name}")
    print(f"{'='*70}\n")

    return extracted_text, extracted_facts


async def main():
    """Generate ground truth files for all Excel test documents."""

    print("\n" + "="*70)
    print("GROUND TRUTH GENERATOR FOR EXCEL TEST DOCUMENTS")
    print("="*70)

    test_docs_dir = Path(__file__).parent / "test_documents" / "xlsx"

    # Find all Excel files
    xlsx_files = list(test_docs_dir.glob("*.xlsx"))

    if not xlsx_files:
        print("\n❌ No Excel files found in test_documents/xlsx/")
        return

    print(f"\nFound {len(xlsx_files)} Excel file(s):")
    for f in xlsx_files:
        print(f"  - {f.name}")

    # Process each file
    for idx, file_path in enumerate(xlsx_files, 1):
        output_name = f"case_{idx:03d}_{file_path.stem}"

        try:
            await create_ground_truth_for_file(file_path, output_name)
        except Exception as e:
            print(f"\n❌ Error processing {file_path.name}: {e}")
            import traceback
            traceback.print_exc()
            continue

    print("\n" + "="*70)
    print("✓ GROUND TRUTH GENERATION COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("1. Review the generated files in test_documents/ground_truth/")
    print("2. Edit the JSON files to:")
    print("   - Add meaningful descriptions")
    print("   - Adjust difficulty level (easy/medium/hard)")
    print("   - Add acceptable_variations if needed")
    print("3. Run the evaluation tests:")
    print("   pytest tests/extractor_evaluation/ -v")
    print()


if __name__ == "__main__":
    asyncio.run(main())
