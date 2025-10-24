"""
Test EXTRACTOR v3.0.0 with a PDF file.

Usage:
    python3 tests/evaluation/extractor/test_v3_pdf.py Datenblatt_test.pdf

Tests v3.0.0 content-first architecture:
- pages[] structure preservation
- interpretation_hints assignment
- quick_facts extraction
- extraction_notes for uncertainties
"""

import asyncio
import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.services.document_service import DocumentService
from app.agents.nodes.extractor import extractor_node
from app.config import settings


async def test_pdf_file(filename: str):
    """Test a single PDF file with EXTRACTOR v3.0.0."""

    test_docs_dir = Path(__file__).parent / "test_documents" / "pdf"
    file_path = test_docs_dir / filename

    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return

    print("\n" + "="*80)
    print(f"TESTING EXTRACTOR v3.0.0 WITH: {filename}")
    print(f"Prompt Version: {settings.extractor_prompt_version}")
    print("="*80)

    # === LAYER 1: Document Parsing ===
    print("\n📄 LAYER 1: Document Parsing")
    print("-"*80)

    doc_service = DocumentService()
    extracted_text = await doc_service.extract_text(
        str(file_path),
        "application/pdf"
    )

    print(f"✓ Extracted {len(extracted_text)} characters")

    # Count pages
    page_markers = extracted_text.count("--- Page")
    print(f"✓ Detected {page_markers} page markers")

    # Check for encoding issues
    if "Â" in extracted_text or "Ã" in extracted_text:
        print(f"⚠️  Encoding issues detected (Â, Ã characters)")
    else:
        print(f"✓ No encoding issues detected")

    print(f"\nFirst 500 characters:")
    print(extracted_text[:500])
    print("...")

    # === LAYER 2: LLM Interpretation ===
    print("\n" + "="*80)
    print("🤖 LAYER 2: EXTRACTOR v3.0.0 Interpretation")
    print("-"*80)

    state = {
        "session_id": "test-v3-pdf",
        "documents": [{
            "filename": filename,
            "file_path": str(file_path),
            "mime_type": "application/pdf"
        }]
    }

    try:
        result = await extractor_node(state)
        extracted_facts = result.get("extracted_facts", {})

        print("✓ EXTRACTOR v3.0.0 completed successfully")

        # === V3.0.0 OUTPUT VALIDATION ===
        print("\n📊 v3.0.0 Schema Validation:")
        print("-"*80)

        # Check top-level structure
        required_fields = ["document_metadata", "pages", "quick_facts", "extraction_notes"]
        for field in required_fields:
            if field in extracted_facts:
                print(f"✓ {field}: present")
            else:
                print(f"❌ {field}: MISSING")

        # Document metadata
        print("\n📋 document_metadata:")
        doc_meta = extracted_facts.get("document_metadata", {})
        print(f"   - document_type: {doc_meta.get('document_type')}")
        print(f"   - language: {doc_meta.get('language')}")
        print(f"   - total_pages: {doc_meta.get('total_pages')}")
        print(f"   - extraction_method: {doc_meta.get('extraction_method')}")
        print(f"   - has_tables: {doc_meta.get('has_tables')}")

        # Pages structure
        pages = extracted_facts.get("pages", [])
        print(f"\n📄 pages[]: {len(pages)} pages extracted")

        if pages:
            # Check first page structure
            first_page = pages[0]
            print(f"\n   Page 1 structure:")
            print(f"      - headers: {len(first_page.get('headers', []))} items")
            print(f"      - body_text: {len(first_page.get('body_text', ''))} chars")
            print(f"      - tables: {len(first_page.get('tables', []))} tables")
            print(f"      - key_value_pairs: {len(first_page.get('key_value_pairs', []))} pairs")
            print(f"      - content_categories: {first_page.get('content_categories', [])}")

            # Sample headers
            if first_page.get('headers'):
                print(f"\n   Sample headers (page 1):")
                for header in first_page['headers'][:3]:
                    print(f"      - {header[:100]}")

            # Sample body_text
            if first_page.get('body_text'):
                print(f"\n   Sample body_text (first 200 chars):")
                print(f"      {first_page['body_text'][:200]}...")

            # Count tables across all pages
            total_tables = sum(len(page.get('tables', [])) for page in pages)
            print(f"\n   Total tables across all pages: {total_tables}")

            # Check interpretation_hints
            if total_tables > 0:
                hints_found = set()
                for page in pages:
                    for table in page.get('tables', []):
                        hint = table.get('interpretation_hint')
                        if hint:
                            hints_found.add(hint)

                print(f"\n   interpretation_hints found:")
                for hint in sorted(hints_found):
                    count = sum(
                        1 for page in pages
                        for table in page.get('tables', [])
                        if table.get('interpretation_hint') == hint
                    )
                    print(f"      - {hint}: {count} tables")

        # quick_facts
        print(f"\n⚡ quick_facts:")
        qf = extracted_facts.get("quick_facts", {})
        print(f"   - products_mentioned: {qf.get('products_mentioned', [])}")
        print(f"   - cas_numbers_found: {len(qf.get('cas_numbers_found', []))} CAS numbers")
        if qf.get('cas_numbers_found'):
            print(f"      {qf['cas_numbers_found'][:5]} ...")
        print(f"   - measurement_units_detected: {qf.get('measurement_units_detected', [])}")
        print(f"   - voc_svoc_detected: {qf.get('voc_svoc_detected')}")
        print(f"   - companies_mentioned: {qf.get('companies_mentioned', [])}")
        print(f"   - locations_mentioned: {qf.get('locations_mentioned', [])}")

        # extraction_notes
        notes = extracted_facts.get("extraction_notes", [])
        print(f"\n📝 extraction_notes: {len(notes)} notes")
        if notes:
            print(f"   Sample notes:")
            for i, note in enumerate(notes[:3], 1):
                print(f"      {i}. [{note.get('status')}] {note.get('field')}")
                print(f"         {note.get('note')}")

        # === V2.0.0 FIELDS CHECK (Should be ABSENT) ===
        print("\n" + "="*80)
        print("🔍 v2.0.0 Fields Check (should be ABSENT in v3.0.0):")
        print("-"*80)

        v2_fields = [
            "pollutant_characterization",
            "process_parameters",
            "current_abatement_systems",
            "industry_and_process",
            "requirements_and_constraints",
            "site_conditions",
            "customer_knowledge_and_expectations",
            "customer_specific_questions",
            "timeline_and_project_phase",
            "data_quality_issues"
        ]

        v2_found = []
        for field in v2_fields:
            if field in extracted_facts:
                v2_found.append(field)
                print(f"⚠️  {field}: PRESENT (should be removed in v3.0.0)")

        if not v2_found:
            print("✓ No v2.0.0 fields found (correct for v3.0.0)")

        # === JSON OUTPUT ===
        print("\n" + "="*80)
        print("💾 Full JSON Output:")
        print("-"*80)
        print(json.dumps(extracted_facts, indent=2, ensure_ascii=False))

        # Save to JSON file
        output_file = Path(__file__).parent / f"test_output_v3_0_0_{filename.replace('.pdf', '.json')}"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(extracted_facts, f, indent=2, ensure_ascii=False)
        print(f"\n✓ JSON saved to: {output_file}")

        # === SUCCESS CRITERIA ===
        print("\n" + "="*80)
        print("✅ SUCCESS CRITERIA:")
        print("-"*80)

        criteria = []

        # 1. pages[] structure present
        if pages and len(pages) > 0:
            criteria.append(("✅", "pages[] structure present"))
        else:
            criteria.append(("❌", "pages[] structure MISSING"))

        # 2. All page content preserved
        has_content = any(
            page.get('headers') or page.get('body_text') or page.get('tables')
            for page in pages
        )
        if has_content:
            criteria.append(("✅", "Page content preserved"))
        else:
            criteria.append(("❌", "Page content MISSING"))

        # 3. interpretation_hints assigned
        hints_assigned = any(
            table.get('interpretation_hint')
            for page in pages
            for table in page.get('tables', [])
        )
        if hints_assigned or total_tables == 0:
            criteria.append(("✅", "interpretation_hints assigned (or no tables)"))
        else:
            criteria.append(("⚠️ ", "interpretation_hints NOT assigned to tables"))

        # 4. quick_facts populated
        if qf.get('cas_numbers_found') or qf.get('products_mentioned'):
            criteria.append(("✅", "quick_facts populated"))
        else:
            criteria.append(("⚠️ ", "quick_facts sparse"))

        # 5. No v2.0.0 fields
        if not v2_found:
            criteria.append(("✅", "No v2.0.0 schema fields (clean migration)"))
        else:
            criteria.append(("❌", f"v2.0.0 fields present: {v2_found}"))

        print()
        for status, message in criteria:
            print(f"{status} {message}")

        # Final verdict
        passed = all(status == "✅" for status, _ in criteria)
        print("\n" + "="*80)
        if passed:
            print("🎉 ALL CRITERIA PASSED - v3.0.0 is working correctly!")
        else:
            print("⚠️  SOME CRITERIA FAILED - Review output above")
        print("="*80)

    except Exception as e:
        print(f"\n❌ EXTRACTOR FAILED:")
        print(f"   Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 tests/evaluation/extractor/test_v3_pdf.py <filename.pdf>")
        print("\nExample:")
        print("  python3 tests/evaluation/extractor/test_v3_pdf.py Datenblatt_test.pdf")
        sys.exit(1)

    filename = sys.argv[1]
    asyncio.run(test_pdf_file(filename))
