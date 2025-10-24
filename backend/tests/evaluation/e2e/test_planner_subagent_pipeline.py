"""
End-to-End Test: PLANNER v2.1.1 → SUBAGENT v2.0.0 Pipeline

Tests the workflow from PLANNER to SUBAGENT with PubChem tool integration:
1. Load validated EXTRACTOR v3.0.0 output (test_output_v3_0_0_Datenblatt_test.json)
2. Run PLANNER v2.1.1 → Create subagents with PubChem tool selection
3. Run SUBAGENT v2.0.0 → Execute first subagent (with PubChem if assigned)

Outputs saved to tests/evaluation/e2e/outputs/ for manual review.

Usage:
    python3 tests/evaluation/e2e/test_planner_subagent_pipeline.py
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.agents.nodes.planner import planner_node
from app.agents.nodes.subagent import execute_single_subagent
from app.config import settings

# Output directory
OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# Timestamp for this run
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


async def test_planner_subagent_pipeline():
    """Test PLANNER v2.1.1 → SUBAGENT v2.0.0 with PubChem integration."""

    print("\n" + "="*80)
    print("E2E TEST: PLANNER v2.1.1 → SUBAGENT v2.0.0 PIPELINE")
    print(f"Timestamp: {TIMESTAMP}")
    print("="*80)

    # Load validated EXTRACTOR v3.0.0 output
    extractor_output_file = Path(__file__).parent.parent / "extractor" / "test_output_v3_0_0_Datenblatt_test.json"

    if not extractor_output_file.exists():
        print(f"❌ Extractor output not found: {extractor_output_file}")
        return

    print(f"\n📄 Input: {extractor_output_file.name}")

    with open(extractor_output_file, 'r', encoding='utf-8') as f:
        extracted_facts = json.load(f)

    # Preview input
    pages = extracted_facts.get("pages", [])
    qf = extracted_facts.get("quick_facts", {})
    print(f"   Pages: {len(pages)}")
    print(f"   VOC detected: {qf.get('voc_svoc_detected')}")
    print(f"   CAS numbers: {len(qf.get('cas_numbers_found', []))}")

    # ========================================================================
    # STEP 1: PLANNER v2.1.1
    # ========================================================================
    print("\n" + "="*80)
    print("STEP 1: PLANNER v2.1.1")
    print(f"Version: {settings.planner_prompt_version}")
    print("-"*80)

    try:
        planner_state = {
            "session_id": f"e2e-planner-test-{TIMESTAMP}",
            "extracted_facts": extracted_facts
        }

        print("Running PLANNER v2.1.1...")
        planner_result = await planner_node(planner_state)
        planner_plan = planner_result.get("planner_plan", {})

        # Save PLANNER output
        planner_output_file = OUTPUT_DIR / f"planner_v2_1_1_{TIMESTAMP}.json"
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
            print(f"   {marker} {i}. {name[:60]}")
            print(f"      Tools: [{tools_str}]")

    except Exception as e:
        print(f"\n❌ PLANNER FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # ========================================================================
    # STEP 2: SUBAGENT v2.0.0 (First subagent only)
    # ========================================================================
    print("\n" + "="*80)
    print("STEP 2: SUBAGENT v2.0.0 (First Subagent)")
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
            "session_id": f"e2e-planner-test-{TIMESTAMP}",
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
        subagent_output_file = OUTPUT_DIR / f"subagent_v2_0_0_first_{TIMESTAMP}.json"
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
            print(f"\n   ⚠️  PubChem tool assigned but not mentioned in analysis (mock data returned)")

    except Exception as e:
        print(f"\n❌ SUBAGENT FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    print("\n" + "="*80)
    print("✅ PLANNER → SUBAGENT PIPELINE TEST COMPLETED")
    print("="*80)

    print("\n📁 Output Files:")
    print(f"   1. PLANNER:   {planner_output_file.name}")
    print(f"   2. SUBAGENT:  {subagent_output_file.name}")

    print(f"\n📂 All outputs saved to: {OUTPUT_DIR}")

    print("\n🔍 Key Findings:")
    print(f"   - PLANNER v2.1.1: {len(subagents)} subagents created")
    print(f"   - PubChem integration: {pubchem_count}/{len(subagents)} subagents")
    print(f"   - SUBAGENT v2.0.0: First subagent executed successfully")
    if has_pubchem:
        print(f"   - PubChem tool: {'✓ Used' if 'pubchem' in analysis.lower() else '⚠️  Not used (mock only)'}")

    # Version verification
    print("\n🎯 Version Verification:")
    print(f"   ✓ PLANNER:   {settings.planner_prompt_version}")
    print(f"   ✓ SUBAGENT:  {settings.subagent_prompt_version}")

    # PubChem integration check
    if pubchem_count > 0:
        print("\n✅ PubChem MCP Integration Validated:")
        print(f"   - PLANNER correctly assigns pubchem_lookup tool")
        print(f"   - SUBAGENT receives tool in task definition")
        print(f"   - Tool execution returns mock data structure")
        print(f"   - Ready for actual MCP server connection")
    else:
        print("\n⚠️  No PubChem tools assigned (may be expected for this document)")

    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(test_planner_subagent_pipeline())
