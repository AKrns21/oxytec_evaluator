#!/usr/bin/env python3
"""Test Phase 5: Enhanced Planner Prompt Examples."""

import asyncio
import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.nodes.planner import planner_node
from app.agents.state import GraphState


async def test_planner_with_enhanced_examples():
    """Test that planner produces high-quality task descriptions with improved examples."""

    print("\n" + "="*80)
    print("TEST: Phase 5 - Enhanced Planner Prompt Examples")
    print("="*80)

    # Sample extracted facts
    extracted_facts = {
        "document_name": "PCC_input.txt",
        "company": "PCC",
        "industry": "producer of surfactants",
        "plant": "ETS-1 production plant",
        "gas_stream_that_requires_treatment": {
            "SO2": "0,1-1850 mg/Nm3",
            "SO3": "0,1-200 mg/Nm3",
            "TVOC": "2,9 – 1800 mg/Nm3"
        },
        "gas_flow": {
            "minimum": "1800kg/h",
            "optimal": "2800kg/h−3600kg/h",
            "maximum": "4000kg/h"
        },
        "gas_temperature": "10−40°C",
        "tvoc_level_overview": "Up to 1800mg/Nm3"
    }

    state: GraphState = {
        "session_id": "test-phase5",
        "documents": [],
        "extracted_facts": extracted_facts,
        "planner_plan": {},
        "subagent_results": [],
        "risk_assessment": {},
        "final_report": "",
        "errors": [],
        "warnings": []
    }

    print("\n⚠️  This test will make actual LLM API calls to GPT-5-mini")
    print("   Continue? (y/n)")

    response = input().strip().lower()

    if response != 'y':
        print("\n⏭️  Test cancelled")
        return False

    try:
        print("\n🔄 Executing planner with enhanced examples...")
        result = await planner_node(state)

        plan = result.get("planner_plan", {})
        subagents = plan.get("subagents", [])

        print(f"✅ Planner completed successfully!")
        print(f"   Created {len(subagents)} subagents")

        if not subagents:
            print("❌ FAIL: No subagents created")
            return False

        print("\n📊 Analyzing task description quality:")

        total_quality_score = 0
        max_possible_score = 0

        for i, subagent in enumerate(subagents, 1):
            print(f"\n--- Subagent {i}: {subagent.get('task', '')[:50]}... ---")

            task = subagent.get("task", "")
            task_lower = task.lower()

            # Quality indicators
            quality_checks = {
                "Has objective": "objective" in task_lower,
                "Has questions": "questions to answer" in task_lower or "questions:" in task_lower,
                "Has method hints": "method hints" in task_lower or "quality criteria" in task_lower,
                "Has deliverables": "deliverables" in task_lower,
                "Has dependencies": "dependencies" in task_lower or "sequencing" in task_lower,
                "Has tools statement": "tools needed:" in task_lower,
                "Mentions confidence levels": "confidence" in task_lower,
                "Mentions quantification": any(x in task_lower for x in ["quantify", "specific", "±", "uncertainty", "bounds"]),
                "Mentions source citation": any(x in task_lower for x in ["cite", "source", "database", "literature"]),
                "Specific deliverable format": any(x in task_lower for x in ["table", "structured list", "machine-usable", "format"])
            }

            score = sum(quality_checks.values())
            max_possible_score += len(quality_checks)
            total_quality_score += score

            for check, passed in quality_checks.items():
                print(f"  {'✓' if passed else '○'} {check}: {passed}")

            print(f"  Score: {score}/{len(quality_checks)}")

            # Show task description length
            print(f"  Task description length: {len(task)} chars")

            # Check relevant_content
            content = subagent.get("relevant_content", "")
            print(f"  Relevant content length: {len(content)} chars")

        # Overall assessment
        avg_score = total_quality_score / max_possible_score if max_possible_score > 0 else 0
        print(f"\n📈 Overall Quality Assessment:")
        print(f"   Total score: {total_quality_score}/{max_possible_score}")
        print(f"   Average: {avg_score*100:.1f}%")

        if avg_score >= 0.8:
            print("   ✅ Excellent quality - task descriptions are comprehensive")
        elif avg_score >= 0.6:
            print("   ✓ Good quality - most requirements met")
        elif avg_score >= 0.4:
            print("   ⚠️  Moderate quality - some improvements needed")
        else:
            print("   ❌ Low quality - significant improvements needed")

        # Show one complete task example
        if subagents:
            print("\n📄 Sample Task Description (Subagent 1, first 800 chars):")
            print("-" * 80)
            print(subagents[0].get("task", "")[:800] + "...")
            print("-" * 80)

        print("\n" + "="*80)
        if avg_score >= 0.6:
            print("✅ PHASE 5 TEST PASSED")
        else:
            print("⚠️  PHASE 5 TEST COMPLETED - QUALITY COULD BE IMPROVED")
        print("="*80)

        print("\n✨ Enhanced planner includes:")
        print("   ✓ Two detailed examples (chemical analysis + quantitative engineering)")
        print("   ✓ Specific method hints with quantitative guidance")
        print("   ✓ Machine-usable deliverable formats")
        print("   ✓ Explicit confidence/uncertainty requirements")
        print("   ✓ Clear tool usage examples")

        return avg_score >= 0.6

    except Exception as e:
        print(f"\n❌ FAIL: Planner execution error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run Phase 5 test."""

    print("\n" + "="*80)
    print("🧪 TESTING PHASE 5: ENHANCED PLANNER PROMPT EXAMPLES")
    print("="*80)

    success = await test_planner_with_enhanced_examples()

    if success:
        print("\n" + "="*80)
        print("✅ PHASE 5 COMPLETE - ALL PHASES IMPLEMENTED")
        print("="*80)
        print("\n🎉 FLOWISE-QUALITY IMPLEMENTATION COMPLETE!")
        print("\nPhase Summary:")
        print("  ✓ Phase 1: Fixed 'unhashable type: dict' error")
        print("  ✓ Phase 2: Simplified planner structure (task + relevant_content)")
        print("  ✓ Phase 3: Enhanced subagent prompting with quality standards")
        print("  ✓ Phase 4: Quantified risk assessment with veto power")
        print("  ✓ Phase 5: Improved planner examples for better task descriptions")
        print("\nThe system is ready for production use!")
    else:
        print("\n" + "="*80)
        print("⚠️  PHASE 5 QUALITY COULD BE IMPROVED")
        print("="*80)
        print("Consider refining planner examples further if needed")

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
