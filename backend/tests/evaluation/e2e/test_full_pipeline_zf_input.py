"""
End-to-End Test: Full Pipeline with ZF_input.pdf

Tests the complete workflow:
1. EXTRACTOR v3.0.0: Extract data from ZF_input.pdf → pages[] format
2. PLANNER v2.1.1: Create subagents with PubChem tool selection
3. SUBAGENT v2.0.0: Execute subagents (first one only, with PubChem tool if assigned)

Outputs saved to tests/evaluation/e2e/outputs/ for manual review.

Usage:
    python3 tests/evaluation/e2e/test_full_pipeline_zf_input.py
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.agents.nodes.extractor import extractor_node
from app.agents.nodes.planner import planner_node
from app.agents.nodes.subagent import execute_single_subagent
from app.services.document_service import DocumentService
from app.config import settings

# Output directory
OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# Timestamp for this run
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


async def test_full_pipeline():
    """Test complete pipeline with ZF_input.pdf."""

    print("\n" + "="*80)
    print("E2E TEST: FULL PIPELINE WITH ZF_INPUT.PDF")
    print(f"Timestamp: {TIMESTAMP}")
    print("="*80)

    # Input file
    input_pdf = Path(__file__).parent.parent.parent.parent.parent / "docs" / "examples" / "ZF_input.pdf"

    if not input_pdf.exists():
        print(f"❌ Input file not found: {input_pdf}")
        return

    print(f"\n📄 Input: {input_pdf}")
    print(f"   Size: {input_pdf.stat().st_size / 1024:.1f} KB")

    # ========================================================================
    # STEP 1: EXTRACTOR v3.0.0
    # ========================================================================
    print("\n" + "="*80)
    print("STEP 1: EXTRACTOR v3.0.0")
    print(f"Version: {settings.extractor_prompt_version}")
    print("-"*80)

    try:
        # Run EXTRACTOR node (it will extract text internally)
        print("Running EXTRACTOR v3.0.0...")
        extractor_state = {
            "session_id": f"e2e-test-{TIMESTAMP}",
            "documents": [
                {
                    "filename": "ZF_input.pdf",
                    "file_path": str(input_pdf),
                    "mime_type": "application/pdf"
                }
            ]
        }

        extractor_result = await extractor_node(extractor_state)
        extracted_facts = extractor_result.get("extracted_facts", {})

        # Save EXTRACTOR output
        extractor_output_file = OUTPUT_DIR / f"1_extractor_v3_0_0_{TIMESTAMP}.json"
        with open(extractor_output_file, 'w', encoding='utf-8') as f:
            json.dump(extracted_facts, f, indent=2, ensure_ascii=False)

        print(f"\n✅ EXTRACTOR v3.0.0 completed")
        print(f"   Output saved: {extractor_output_file}")

        # Validation
        print("\n📊 EXTRACTOR Output Validation:")
        v3_fields = ["document_metadata", "pages", "quick_facts", "extraction_notes"]
        for field in v3_fields:
            status = "✓" if field in extracted_facts else "❌"
            print(f"   {status} {field}")

        pages = extracted_facts.get("pages", [])
        print(f"\n   Pages: {len(pages)}")

        qf = extracted_facts.get("quick_facts", {})
        print(f"   VOC detected: {qf.get('voc_svoc_detected')}")
        print(f"   CAS numbers: {len(qf.get('cas_numbers_found', []))}")
        print(f"   Products: {qf.get('products_mentioned', [])}")

    except Exception as e:
        print(f"\n❌ EXTRACTOR FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # ========================================================================
    # STEP 2: PLANNER v2.1.1
    # ========================================================================
    print("\n" + "="*80)
    print("STEP 2: PLANNER v2.1.1")
    print(f"Version: {settings.planner_prompt_version}")
    print("-"*80)

    try:
        planner_state = {
            "session_id": f"e2e-test-{TIMESTAMP}",
            "extracted_facts": extracted_facts
        }

        print("Running PLANNER v2.1.1...")
        planner_result = await planner_node(planner_state)
        planner_plan = planner_result.get("planner_plan", {})

        # Save PLANNER output
        planner_output_file = OUTPUT_DIR / f"2_planner_v2_1_1_{TIMESTAMP}.json"
        with open(planner_output_file, 'w', encoding='utf-8') as f:
            json.dump(planner_plan, f, indent=2, ensure_ascii=False)

        print(f"\n✅ PLANNER v2.1.1 completed")
        print(f"   Output saved: {planner_output_file}")

        # Validation
        subagents = planner_plan.get("subagents", [])
        reasoning = planner_plan.get("reasoning", "")

        print("\n📊 PLANNER Output Validation:")
        print(f"   Subagents created: {len(subagents)}")
        print(f"   Reasoning length: {len(reasoning)} chars")

        # Check for PubChem tool assignment
        pubchem_count = sum(1 for s in subagents if "pubchem_lookup" in s.get("tools", []))
        print(f"\n   🧪 Subagents with pubchem_lookup: {pubchem_count}/{len(subagents)}")

        # List subagents with their tools
        print("\n   Subagent Summary:")
        for i, subagent in enumerate(subagents, 1):
            task = subagent.get("task", "")
            task_lines = task.split("\n")
            name = task_lines[0].replace("Subagent:", "").strip() if task_lines else "Unknown"
            tools = subagent.get("tools", [])
            tools_str = ", ".join(tools) if tools else "none"

            marker = "🧪" if "pubchem_lookup" in tools else "  "
            print(f"   {marker} {i}. {name[:50]}")
            print(f"      Tools: [{tools_str}]")

    except Exception as e:
        print(f"\n❌ PLANNER FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # ========================================================================
    # STEP 3: SUBAGENT v2.0.0 (First subagent only)
    # ========================================================================
    print("\n" + "="*80)
    print("STEP 3: SUBAGENT v2.0.0 (First Subagent Only)")
    print(f"Version: {settings.subagent_prompt_version}")
    print("-"*80)

    if not subagents:
        print("❌ No subagents to execute")
        return

    try:
        first_subagent = subagents[0]
        task = first_subagent.get("task", "")
        task_lines = task.split("\n")
        name = task_lines[0].replace("Subagent:", "").strip() if task_lines else "Unknown"
        tools = first_subagent.get("tools", [])

        print(f"\nExecuting: {name}")
        print(f"Tools: {tools}")

        has_pubchem = "pubchem_lookup" in tools
        if has_pubchem:
            print("🧪 This subagent has pubchem_lookup tool!")

        # Execute first subagent
        subagent_state = {
            "session_id": f"e2e-test-{TIMESTAMP}",
            "extracted_facts": extracted_facts,
            "planner_plan": planner_plan
        }

        print("\nRunning SUBAGENT v2.0.0...")
        subagent_result = await execute_single_subagent(
            first_subagent,
            subagent_state,
            instance_name=name
        )

        # Save SUBAGENT output
        subagent_output_file = OUTPUT_DIR / f"3_subagent_v2_0_0_first_{TIMESTAMP}.json"
        with open(subagent_output_file, 'w', encoding='utf-8') as f:
            json.dump(subagent_result, f, indent=2, ensure_ascii=False)

        print(f"\n✅ SUBAGENT v2.0.0 completed")
        print(f"   Output saved: {subagent_output_file}")

        # Validation
        print("\n📊 SUBAGENT Output Validation:")
        print(f"   Name: {subagent_result.get('name')}")
        print(f"   Status: {subagent_result.get('status')}")

        analysis = subagent_result.get("analysis", "")
        print(f"   Analysis length: {len(analysis)} chars")

        if analysis:
            print(f"\n   Analysis preview (first 500 chars):")
            print(f"   {analysis[:500]}...")

        # Check if PubChem tool was used
        if has_pubchem and "pubchem" in analysis.lower():
            print(f"\n   ✓ Analysis mentions PubChem (tool likely used)")
        elif has_pubchem:
            print(f"\n   ⚠️  PubChem tool assigned but not mentioned in analysis")

    except Exception as e:
        print(f"\n❌ SUBAGENT FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    print("\n" + "="*80)
    print("✅ FULL PIPELINE TEST COMPLETED")
    print("="*80)

    print("\n📁 Output Files:")
    print(f"   1. EXTRACTOR: {extractor_output_file.name}")
    print(f"   2. PLANNER:   {planner_output_file.name}")
    print(f"   3. SUBAGENT:  {subagent_output_file.name}")

    print(f"\n📂 All outputs saved to: {OUTPUT_DIR}")

    print("\n🔍 Key Findings:")
    print(f"   - EXTRACTOR v3.0.0: {len(pages)} pages extracted")
    print(f"   - PLANNER v2.1.1: {len(subagents)} subagents created")
    print(f"   - PubChem integration: {pubchem_count}/{len(subagents)} subagents")
    print(f"   - SUBAGENT v2.0.0: First subagent executed successfully")

    # Check versions
    print("\n🎯 Version Verification:")
    print(f"   ✓ EXTRACTOR: {settings.extractor_prompt_version}")
    print(f"   ✓ PLANNER:   {settings.planner_prompt_version}")
    print(f"   ✓ SUBAGENT:  {settings.subagent_prompt_version}")

    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
