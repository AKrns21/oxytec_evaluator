"""
Test script to evaluate PDF files with the EXTRACTOR agent.

Usage:
    python tests/extractor_evaluation/test_pdf_files.py
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.document_service import DocumentService
from app.agents.nodes.extractor import extractor_node
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def test_pdf_file(file_path: Path):
    """Test a single PDF file and return results."""

    print(f"\n{'='*80}")
    print(f"TESTING: {file_path.name}")
    print('='*80)

    try:
        # === LAYER 1: Document Parsing ===
        print("\n📄 LAYER 1: Document Parsing")
        print("-"*80)

        doc_service = DocumentService()
        extracted_text = await doc_service.extract_text(
            str(file_path),
            "application/pdf"
        )

        print(f"✓ Extracted {len(extracted_text)} characters")
        print(f"\nFirst 500 characters:")
        print(extracted_text[:500])
        print("...")

        # Basic text analysis
        lines = extracted_text.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        print(f"\n📊 Text Statistics:")
        print(f"   - Total lines: {len(lines)}")
        print(f"   - Non-empty lines: {len(non_empty_lines)}")
        print(f"   - Average line length: {sum(len(line) for line in non_empty_lines) / len(non_empty_lines):.1f} chars")

        # Check for common patterns
        has_cas_numbers = "CAS" in extracted_text or "CAS-" in extracted_text
        has_percentages = "%" in extracted_text
        has_tables = "|" in extracted_text or "\t" in extracted_text

        print(f"\n🔍 Content Indicators:")
        print(f"   - Contains CAS numbers: {has_cas_numbers}")
        print(f"   - Contains percentages: {has_percentages}")
        print(f"   - Contains table structures: {has_tables}")

        # === LAYER 2: LLM Interpretation ===
        print("\n" + "="*80)
        print("🤖 LAYER 2: LLM Interpretation (EXTRACTOR)")
        print("-"*80)

        state = {
            "session_id": f"test-pdf-{file_path.stem}",
            "documents": [{
                "filename": file_path.name,
                "file_path": str(file_path),
                "mime_type": "application/pdf"
            }]
        }

        result = await extractor_node(state)

        if "extracted_facts" in result and result["extracted_facts"]:
            extracted_facts = result["extracted_facts"]
            print("✓ EXTRACTOR completed successfully")

            # Analyze extracted data
            print("\n📊 Extracted Data Summary:")
            print("-"*80)

            # Pollutants
            pollutants = extracted_facts.get("pollutant_characterization", {}).get("pollutant_list", [])
            print(f"\n🧪 Pollutants: {len(pollutants)}")
            for i, pollutant in enumerate(pollutants[:10], 1):  # Show first 10
                name = pollutant.get("name", "Unknown")
                cas = pollutant.get("cas_number", "N/A")
                conc = pollutant.get("concentration", "N/A")
                unit = pollutant.get("concentration_unit", "")
                print(f"   {i}. {name} (CAS: {cas}): {conc} {unit}")

            if len(pollutants) > 10:
                print(f"   ... and {len(pollutants) - 10} more")

            # Process parameters
            process_params = extracted_facts.get("process_parameters", {})
            print(f"\n⚙️  Process Parameters:")

            flow_rate = process_params.get("flow_rate", {})
            if flow_rate.get("value"):
                print(f"   - Flow rate: {flow_rate.get('value')} {flow_rate.get('unit', '')}")

            temperature = process_params.get("temperature", {})
            if temperature.get("value"):
                print(f"   - Temperature: {temperature.get('value')} {temperature.get('unit', '')}")

            pressure = process_params.get("pressure", {})
            if pressure.get("value"):
                print(f"   - Pressure: {pressure.get('value')} {pressure.get('unit', '')} ({pressure.get('type', '')})")

            humidity = process_params.get("humidity", {})
            if humidity.get("value"):
                print(f"   - Humidity: {humidity.get('value')} {humidity.get('unit', '')} ({humidity.get('type', '')})")

            # Industry and process
            industry = extracted_facts.get("industry_and_process", {})
            if industry.get("industry_sector"):
                print(f"\n🏭 Industry: {industry.get('industry_sector')}")
            if industry.get("specific_processes"):
                print(f"   Process: {industry.get('specific_processes')[:200]}")

            # Data quality issues
            data_quality_issues = extracted_facts.get("data_quality_issues", [])
            if data_quality_issues:
                print(f"\n⚠️  Data Quality Issues: {len(data_quality_issues)}")
                for i, issue in enumerate(data_quality_issues[:5], 1):
                    severity = issue.get("severity", "UNKNOWN")
                    description = issue.get("issue", "")
                    print(f"   {i}. [{severity}] {description}")

                if len(data_quality_issues) > 5:
                    print(f"   ... and {len(data_quality_issues) - 5} more")

            # Customer questions
            questions = extracted_facts.get("customer_specific_questions", [])
            if questions:
                print(f"\n❓ Customer Questions: {len(questions)}")
                for i, q in enumerate(questions[:3], 1):
                    print(f"   {i}. [{q.get('priority', 'N/A')}] {q.get('question_text', '')[:100]}...")

            return {
                "success": True,
                "filename": file_path.name,
                "text_length": len(extracted_text),
                "pollutant_count": len(pollutants),
                "has_process_params": bool(flow_rate.get("value") or temperature.get("value")),
                "data_quality_issues": len(data_quality_issues),
                "extracted_facts": extracted_facts
            }
        else:
            print("❌ EXTRACTOR failed or returned no data")
            errors = result.get("errors", [])
            if errors:
                print(f"Errors: {errors}")

            return {
                "success": False,
                "filename": file_path.name,
                "errors": errors
            }

    except Exception as e:
        print(f"❌ Error testing {file_path.name}: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            "success": False,
            "filename": file_path.name,
            "error": str(e)
        }


async def main():
    """Test all PDF files in the test_documents/pdf directory."""

    pdf_dir = Path(__file__).parent / "test_documents" / "pdf"

    if not pdf_dir.exists():
        print(f"❌ PDF directory not found: {pdf_dir}")
        return

    pdf_files = sorted(pdf_dir.glob("*.PDF")) + sorted(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"❌ No PDF files found in: {pdf_dir}")
        return

    print(f"\n{'='*80}")
    print(f"PDF EXTRACTOR EVALUATION - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*80}")
    print(f"\nFound {len(pdf_files)} PDF files to test:")
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"   {i}. {pdf_file.name}")

    # Test each file
    results = []
    for pdf_file in pdf_files:
        result = await test_pdf_file(pdf_file)
        results.append(result)

    # Summary
    print(f"\n\n{'='*80}")
    print("SUMMARY")
    print('='*80)

    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]

    print(f"\n✅ Successful: {len(successful)}/{len(results)}")
    print(f"❌ Failed: {len(failed)}/{len(results)}")

    if successful:
        print(f"\n📊 Statistics from successful extractions:")
        total_pollutants = sum(r.get("pollutant_count", 0) for r in successful)
        avg_pollutants = total_pollutants / len(successful) if successful else 0

        with_process_params = len([r for r in successful if r.get("has_process_params")])

        print(f"   - Average pollutants per document: {avg_pollutants:.1f}")
        print(f"   - Documents with process parameters: {with_process_params}/{len(successful)}")
        print(f"   - Total data quality issues flagged: {sum(r.get('data_quality_issues', 0) for r in successful)}")

    if failed:
        print(f"\n❌ Failed extractions:")
        for r in failed:
            print(f"   - {r['filename']}: {r.get('error', 'Unknown error')}")

    # Save results
    output_file = Path(__file__).parent / f"PDF_TEST_RESULTS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n💾 Detailed results saved to: {output_file.name}")


if __name__ == "__main__":
    asyncio.run(main())
