"""
Test PLANNER v2.1.0 with EXTRACTOR v3.0.0 output.

Usage:
    python3 tests/evaluation/planner/test_planner_v2_1_0.py

Tests v2.1.0 content-first integration:
- pages[] parsing
- interpretation_hint filtering
- content_categories filtering
- quick_facts usage
- Subagent content filtering
"""

import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.agents.nodes.planner import planner_node
from app.config import settings

async def test_planner_v2_1_0():
    """Test PLANNER v2.1.0 with validated EXTRACTOR v3.0.0 output."""

    # Load validated v3.0.0 extraction
    extraction_file = Path(__file__).parent.parent / "extractor" / "test_output_v3_0_0_Datenblatt_test.json"

    if not extraction_file.exists():
        print(f"❌ Extraction file not found: {extraction_file}")
        return

    with open(extraction_file, 'r', encoding='utf-8') as f:
        extracted_facts = json.load(f)

    print("\n" + "="*80)
    print("TESTING PLANNER v2.1.0 WITH EXTRACTOR v3.0.0 OUTPUT")
    print(f"Planner Version: {settings.planner_prompt_version}")
    print(f"Extraction File: test_output_v3_0_0_Datenblatt_test.json")
    print("="*80)

    # === INPUT VALIDATION ===
    print("\n📋 INPUT VALIDATION (v3.0.0 Schema)")
    print("-"*80)

    # Check v3.0.0 structure
    v3_fields = ["document_metadata", "pages", "quick_facts", "extraction_notes"]
    for field in v3_fields:
        if field in extracted_facts:
            print(f"✓ {field}: present")
        else:
            print(f"❌ {field}: MISSING")

    # Preview quick_facts
    qf = extracted_facts.get("quick_facts", {})
    print(f"\n⚡ quick_facts summary:")
    print(f"   - voc_svoc_detected: {qf.get('voc_svoc_detected')}")
    print(f"   - cas_numbers_found: {len(qf.get('cas_numbers_found', []))} CAS numbers")
    print(f"   - products_mentioned: {qf.get('products_mentioned', [])}")
    print(f"   - measurement_units_detected: {qf.get('measurement_units_detected', [])}")

    # Preview pages structure
    pages = extracted_facts.get("pages", [])
    print(f"\n📄 pages[] structure:")
    print(f"   - Total pages: {len(pages)}")

    # Count interpretation_hints
    hint_counts = {}
    for page in pages:
        for table in page.get("tables", []):
            hint = table.get("interpretation_hint", "none")
            hint_counts[hint] = hint_counts.get(hint, 0) + 1

    if hint_counts:
        print(f"\n   interpretation_hints distribution:")
        for hint, count in sorted(hint_counts.items()):
            print(f"      - {hint}: {count} tables")

    # Count content_categories
    category_counts = {}
    for page in pages:
        for cat in page.get("content_categories", []):
            category_counts[cat] = category_counts.get(cat, 0) + 1

    if category_counts:
        print(f"\n   content_categories distribution:")
        for cat, count in sorted(category_counts.items()):
            print(f"      - {cat}: {count} pages")

    # === PLANNER EXECUTION ===
    print("\n" + "="*80)
    print("🤖 PLANNER v2.1.0 EXECUTION")
    print("-"*80)

    state = {
        "session_id": "test-planner-v2.1.0",
        "extracted_facts": extracted_facts
    }

    try:
        result = await planner_node(state)
        planner_plan = result.get("planner_plan", {})

        print("✓ PLANNER v2.1.0 completed successfully")

        # === OUTPUT VALIDATION ===
        print("\n" + "="*80)
        print("📊 PLANNER OUTPUT VALIDATION")
        print("-"*80)

        subagents = planner_plan.get("subagents", [])
        reasoning = planner_plan.get("reasoning", "")

        print(f"\n📋 Basic Structure:")
        print(f"   - Number of subagents: {len(subagents)}")
        print(f"   - Reasoning length: {len(reasoning)} chars")

        if len(subagents) < 3 or len(subagents) > 10:
            print(f"   ⚠️  Subagent count outside expected range (3-10)")

        # === SUBAGENT ANALYSIS ===
        print("\n" + "="*80)
        print("🔍 SUBAGENT ANALYSIS")
        print("-"*80)

        for i, subagent in enumerate(subagents, 1):
            print(f"\n{i}. Subagent Analysis")
            print("   " + "-"*76)

            # Extract subagent name from task
            task = subagent.get("task", "")
            task_lines = task.split("\n")
            subagent_name = task_lines[0].replace("Subagent:", "").strip() if task_lines else "Unknown"

            print(f"   Name: {subagent_name}")
            print(f"   Task length: {len(task)} chars")

            # Check for v3.0.0 awareness
            v3_indicators = [
                "interpretation_hint",
                "content_categories",
                "quick_facts",
                "pages[",
                "filtered",
                "from EXTRACTOR v3.0.0"
            ]

            found_indicators = [ind for ind in v3_indicators if ind in task]
            if found_indicators:
                print(f"   ✓ v3.0.0 aware: {', '.join(found_indicators)}")
            else:
                print(f"   ⚠️  No v3.0.0 structure references found")

            # Tools
            tools = subagent.get("tools", [])
            print(f"   Tools: {tools if tools else 'none'}")

            # Relevant content
            relevant_content_str = subagent.get("relevant_content", "{}")
            try:
                relevant_content = json.loads(relevant_content_str)
                print(f"   relevant_content keys: {list(relevant_content.keys())}")

                # Check if using v2.0.0 schema fields (BAD)
                v2_fields = [
                    "pollutant_characterization",
                    "process_parameters",
                    "current_abatement_systems",
                    "industry_and_process"
                ]

                v2_found = [f for f in v2_fields if f in relevant_content]
                if v2_found:
                    print(f"   ❌ CONTAINS v2.0.0 SCHEMA FIELDS: {v2_found}")
                else:
                    print(f"   ✓ No v2.0.0 schema fields (good)")

                # Check for v3.0.0 filtered content patterns
                v3_patterns = [
                    "voc_tables",
                    "composition_tables",
                    "process_parameters",  # OK if it's filtered data, not schema field
                    "properties_tables",
                    "safety_pages",
                    "filtered",
                    "cas_numbers",
                    "pollutant_summary"
                ]

                v3_found = [p for p in v3_patterns if p in relevant_content]
                if v3_found:
                    print(f"   ✓ v3.0.0 filtered content: {', '.join(v3_found)}")

                # Show sample content size
                total_size = len(json.dumps(relevant_content))
                print(f"   Content size: {total_size} chars")

            except json.JSONDecodeError:
                print(f"   ⚠️  relevant_content is not valid JSON")
                print(f"   Preview: {relevant_content_str[:100]}...")

        # === TECHNOLOGY SCREENING CHECK ===
        print("\n" + "="*80)
        print("🔍 CRITICAL MANDATES CHECK")
        print("-"*80)

        # Check for Technology Screening subagent (REQUIRED)
        tech_screening_found = False
        for subagent in subagents:
            task = subagent.get("task", "").lower()
            if "technology screening" in task or "technology comparison" in task:
                tech_screening_found = True
                tools = subagent.get("tools", [])
                has_rag = "oxytec_knowledge_search" in tools
                print(f"\n✓ Technology Screening subagent found")
                print(f"   Tools: {tools}")
                if has_rag:
                    print(f"   ✓ Uses oxytec_knowledge_search (REQUIRED)")
                else:
                    print(f"   ❌ MISSING oxytec_knowledge_search tool (REQUIRED)")
                break

        if not tech_screening_found:
            print(f"\n❌ Technology Screening subagent NOT FOUND (REQUIRED)")

        # Check for Customer Question Response (if applicable)
        customer_q_found = False
        for subagent in subagents:
            task = subagent.get("task", "").lower()
            if "customer question" in task or "customer-specific" in task:
                customer_q_found = True
                print(f"\n✓ Customer Question Response subagent found")
                break

        if not customer_q_found:
            print(f"\n⚠️  No Customer Question Response subagent (OK if no questions in document)")

        # === SUCCESS CRITERIA ===
        print("\n" + "="*80)
        print("✅ SUCCESS CRITERIA")
        print("-"*80)

        criteria = []

        # 1. Valid number of subagents
        if 3 <= len(subagents) <= 10:
            criteria.append(("✅", f"{len(subagents)} subagents created (within 3-10 range)"))
        else:
            criteria.append(("❌", f"{len(subagents)} subagents (outside 3-10 range)"))

        # 2. Technology Screening present
        if tech_screening_found:
            criteria.append(("✅", "Technology Screening subagent present (REQUIRED)"))
        else:
            criteria.append(("❌", "Technology Screening subagent MISSING (REQUIRED)"))

        # 3. v3.0.0 structure awareness
        v3_aware_count = sum(
            1 for subagent in subagents
            if any(ind in subagent.get("task", "") for ind in ["pages[", "interpretation_hint", "quick_facts", "content_categories"])
        )
        if v3_aware_count >= len(subagents) * 0.5:
            criteria.append(("✅", f"{v3_aware_count}/{len(subagents)} subagents reference v3.0.0 structure"))
        else:
            criteria.append(("⚠️ ", f"Only {v3_aware_count}/{len(subagents)} subagents reference v3.0.0 structure"))

        # 4. No v2.0.0 schema fields in relevant_content
        v2_violations = 0
        for subagent in subagents:
            try:
                rel_content = json.loads(subagent.get("relevant_content", "{}"))
                v2_fields = ["pollutant_characterization", "process_parameters", "industry_and_process"]
                if any(f in rel_content for f in v2_fields):
                    v2_violations += 1
            except:
                pass

        if v2_violations == 0:
            criteria.append(("✅", "No v2.0.0 schema fields in relevant_content"))
        else:
            criteria.append(("❌", f"{v2_violations} subagents using v2.0.0 schema fields"))

        # 5. All tasks have content
        empty_tasks = sum(1 for s in subagents if len(s.get("task", "")) < 100)
        if empty_tasks == 0:
            criteria.append(("✅", "All tasks have substantial content (>100 chars)"))
        else:
            criteria.append(("❌", f"{empty_tasks} tasks have insufficient content"))

        print()
        for status, message in criteria:
            print(f"{status} {message}")

        # === SAVE OUTPUT ===
        output_file = Path(__file__).parent / "test_output_planner_v2_1_0_Datenblatt_test.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(planner_plan, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Plan saved to: {output_file}")

        # === DETAILED TASK PREVIEW ===
        print("\n" + "="*80)
        print("📝 SUBAGENT TASK PREVIEWS (First 500 chars)")
        print("-"*80)

        for i, subagent in enumerate(subagents, 1):
            task = subagent.get("task", "")
            task_preview = task[:500] + "..." if len(task) > 500 else task
            print(f"\n{i}. {task_preview}")
            print()

        # Final verdict
        passed = all(status == "✅" for status, _ in criteria)
        print("="*80)
        if passed:
            print("🎉 ALL CRITERIA PASSED - PLANNER v2.1.0 is working correctly!")
        else:
            print("⚠️  SOME CRITERIA FAILED - Review output above")
        print("="*80)

    except Exception as e:
        print(f"\n❌ PLANNER FAILED:")
        print(f"   Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return


if __name__ == "__main__":
    asyncio.run(test_planner_v2_1_0())
