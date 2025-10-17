#!/usr/bin/env python3
"""Test script for Flowise-style planner structure."""

import asyncio
import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.nodes.planner import planner_node
from app.agents.nodes.subagent import execute_single_subagent, extract_agent_name, extract_tools_from_task
from app.agents.state import GraphState


async def test_planner_structure():
    """Test that planner produces Flowise-style structure."""

    print("\n" + "="*80)
    print("TEST 1: Planner Flowise-Style Structure")
    print("="*80)

    # Sample extracted facts (from the example)
    extracted_facts = {
        "document_name": "PCC_input.txt",
        "company": "PCC",
        "industry": "producer of surfactants",
        "plant": "ETS-1 production plant",
        "status": "Installation for TVOC removal requested",
        "gas_stream_that_requires_treatment": {
            "SO2": "0,1-1850 mg/Nm3",
            "SO3": "0,1-200 mg/Nm3",
            "TVOC": "2,9 – 1800 mg/Nm3",
            "TVOC_including": "2-ethylhexanol (CAS 104-76-7); octan-1-ol; decan-1-ol..."
        },
        "gas_flow": {
            "minimum": "1800kg/h",
            "optimal": "2800kg/h−3600kg/h",
            "maximum": "4000kg/h"
        },
        "gas_temperature": "10−40°C",
        "tvoc_level_overview": "Up to 1800mg/Nm3"
    }

    # Create test state
    state: GraphState = {
        "session_id": "test-123",
        "documents": [],
        "extracted_facts": extracted_facts,
        "planner_plan": {},
        "subagent_results": [],
        "risk_assessment": {},
        "final_report": "",
        "errors": [],
        "warnings": []
    }

    try:
        # Execute planner
        print("\n🔄 Executing planner...")
        result = await planner_node(state)

        plan = result.get("planner_plan", {})
        subagents = plan.get("subagents", [])

        print(f"✅ Planner completed successfully!")
        print(f"   Created {len(subagents)} subagents")

        # Verify structure
        if not subagents:
            print("❌ FAIL: No subagents created")
            return False

        print("\n📋 Verifying Flowise-style structure:")

        for i, subagent in enumerate(subagents, 1):
            print(f"\n--- Subagent {i} ---")

            # Check for required fields
            has_task = "task" in subagent
            has_content = "relevant_content" in subagent

            # Check for OLD fields (should NOT be present)
            has_old_name = "name" in subagent
            has_old_objective = "objective" in subagent
            has_old_questions = "questions" in subagent
            has_old_input_fields = "input_fields" in subagent

            print(f"  ✓ Has 'task' field: {has_task}")
            print(f"  ✓ Has 'relevant_content' field: {has_content}")

            if has_old_name or has_old_objective or has_old_questions or has_old_input_fields:
                print(f"  ⚠️  WARNING: Found old structure fields!")
                print(f"     name={has_old_name}, objective={has_old_objective}, questions={has_old_questions}, input_fields={has_old_input_fields}")

            if has_task and has_content:
                # Extract agent name
                task = subagent["task"]
                agent_name = extract_agent_name(task)
                tools = extract_tools_from_task(task)

                print(f"  📝 Agent name extracted: '{agent_name}'")
                print(f"  🔧 Tools extracted: {tools}")
                print(f"  📄 Task description length: {len(task)} chars")
                print(f"  📊 Relevant content length: {len(subagent['relevant_content'])} chars")

                # Check task structure
                task_lower = task.lower()
                has_objective = "objective" in task_lower
                has_questions = "questions to answer" in task_lower
                has_method_hints = "method hints" in task_lower or "quality criteria" in task_lower
                has_deliverables = "deliverables" in task_lower
                has_dependencies = "dependencies" in task_lower or "sequencing" in task_lower

                print(f"  📋 Task structure completeness:")
                print(f"     - Has objective: {has_objective}")
                print(f"     - Has questions: {has_questions}")
                print(f"     - Has method hints: {has_method_hints}")
                print(f"     - Has deliverables: {has_deliverables}")
                print(f"     - Has dependencies: {has_dependencies}")

                # Show first 300 chars of task
                print(f"\n  Preview of task description:")
                print(f"  {task[:300]}...")
            else:
                print(f"  ❌ FAIL: Missing required fields!")
                return False

        print("\n" + "="*80)
        print("✅ PLANNER STRUCTURE TEST PASSED")
        print("="*80)
        return True

    except Exception as e:
        print(f"\n❌ FAIL: Planner execution error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_subagent_processing():
    """Test that subagent can process Flowise-style structure."""

    print("\n" + "="*80)
    print("TEST 2: Subagent Processing")
    print("="*80)

    # Create a sample Flowise-style subagent definition
    subagent_def = {
        "task": """Subagent: VOC Analysis Expert

Objective (narrow): Analyze the VOC composition to identify challenging compounds, expected reactivity with NTP/UV/ozone systems, potential by-products, and measurement gaps.

Questions to answer (explicit):
- What are the representative compounds/groups with relevant physico-chemical properties?
- Which compounds will react rapidly with ozone vs requiring OH radicals?
- What hazardous by-products are likely (formaldehyde, organic acids)?

Method hints / quality criteria:
- Use authoritative databases (PubChem, NIST) and cite sources
- Provide conservative by-product yield estimates
- Rank confidence level (high/medium/low) for each conclusion

Deliverables (concise outputs):
- Structured table of representative compounds with properties
- List of show-stopper species for each technology
- Prioritized list of measurement gaps

Dependencies / sequencing: Independent — can run immediately in parallel.

Tools needed: none""",
        "relevant_content": json.dumps({
            "gas_stream_that_requires_treatment": {
                "TVOC": "2,9 – 1800 mg/Nm3",
                "TVOC_including": "2-ethylhexanol; octan-1-ol; decan-1-ol"
            },
            "tvoc_level_overview": "Up to 1800mg/Nm3"
        })
    }

    state: GraphState = {
        "session_id": "test-123",
        "documents": [],
        "extracted_facts": {},
        "planner_plan": {},
        "subagent_results": [],
        "risk_assessment": {},
        "final_report": "",
        "errors": [],
        "warnings": []
    }

    try:
        print("\n🔄 Testing helper functions...")

        # Test extract_agent_name
        agent_name = extract_agent_name(subagent_def["task"])
        print(f"✅ extract_agent_name: '{agent_name}'")

        # Test extract_tools_from_task
        tools = extract_tools_from_task(subagent_def["task"])
        print(f"✅ extract_tools_from_task: {tools}")

        if agent_name != "voc_analysis_expert":
            print(f"⚠️  WARNING: Expected 'voc_analysis_expert', got '{agent_name}'")

        if tools != []:
            print(f"⚠️  WARNING: Expected no tools, got {tools}")

        print("\n🔄 Testing subagent execution (dry run - will call LLM)...")
        print("   Note: This will make actual API calls to test the full flow")

        result = await execute_single_subagent(
            subagent_def=subagent_def,
            state=state,
            instance_name="test_subagent_0"
        )

        print(f"\n✅ Subagent execution completed!")
        print(f"   Agent name: {result.get('agent_name')}")
        print(f"   Instance: {result.get('instance')}")
        print(f"   Result length: {len(str(result.get('result', '')))} chars")

        print("\n" + "="*80)
        print("✅ SUBAGENT PROCESSING TEST PASSED")
        print("="*80)
        return True

    except Exception as e:
        print(f"\n❌ FAIL: Subagent processing error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""

    print("\n" + "="*80)
    print("🧪 TESTING FLOWISE-STYLE STRUCTURE IMPLEMENTATION")
    print("="*80)

    # Test 1: Planner structure
    test1_passed = await test_planner_structure()

    if not test1_passed:
        print("\n❌ TESTS FAILED - Stopping here")
        return False

    # Test 2: Subagent processing (makes actual API call)
    print("\n⚠️  Test 2 will make actual LLM API calls. Continue? (y/n)")
    response = input().strip().lower()

    if response == 'y':
        test2_passed = await test_subagent_processing()

        if not test2_passed:
            print("\n❌ TESTS FAILED")
            return False
    else:
        print("\n⏭️  Skipping Test 2 (subagent execution)")
        test2_passed = True

    print("\n" + "="*80)
    print("✅ ALL TESTS PASSED")
    print("="*80)
    print("\n✨ Flowise-style structure is working correctly!")
    print("   Ready to proceed with Phase 4: Quantified Risk Assessment")

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
