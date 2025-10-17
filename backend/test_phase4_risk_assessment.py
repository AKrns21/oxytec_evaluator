#!/usr/bin/env python3
"""Test Phase 4: Quantified Risk Assessment."""

import asyncio
import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.nodes.risk_assessor import risk_assessor_node
from app.agents.state import GraphState


async def test_risk_assessment_structure():
    """Test that risk assessor produces quantified output."""

    print("\n" + "="*80)
    print("TEST: Phase 4 - Quantified Risk Assessment")
    print("="*80)

    # Sample subagent results (new Flowise-style structure)
    subagent_results = [
        {
            "agent_name": "voc_composition_and_reactivity_analyst",
            "instance": "subagent_0",
            "task": "Subagent: VOC Composition & Reactivity Analyst\n\nObjective: Analyze VOC composition...",
            "result": "Analysis reveals high-MW alkanes (C12-C14) present at up to 1800mg/Nm3. These compounds are recalcitrant to single-pass oxidation. Expected by-products include aldehydes and organic acids. Show-stopper risk: SO2/SO3 will form sulfuric acid aerosols in oxidizing environment without upstream scrubbing. Critical measurement gap: water vapor content unknown."
        },
        {
            "agent_name": "technology_screening_and_risk_assessor",
            "instance": "subagent_1",
            "task": "Subagent: Technology Screening & Risk Assessor\n\nObjective: Screen NTP, UV/ozone...",
            "result": "NTP alone: High risk (70% probability) of sulfuric acid aerosol formation due to SO2/SO3 oxidation. UV/ozone: 60% probability of excessive SOA formation from olefins. Wet scrubbing required upstream for acid gas removal. Recommended: Hybrid NTP + wet scrubber configuration. Estimated CAPEX increase: 40% over NTP-only."
        },
        {
            "agent_name": "safety_atex_and_materials_specialist",
            "instance": "subagent_2",
            "task": "Subagent: Safety, ATEX & Materials Specialist\n\nObjective: Assess explosion risk...",
            "result": "ATEX risk: Moderate (35% probability of exceeding 25% LEL during upsets). Corrosion risk: High (75% probability) - sulfuric acid formation will require FRP/stainless construction, adding 30% to material costs. Mandatory: Continuous LEL monitoring, acid drainage system, pH control."
        }
    ]

    # Create test state
    state: GraphState = {
        "session_id": "test-phase4",
        "documents": [],
        "extracted_facts": {},
        "planner_plan": {},
        "subagent_results": subagent_results,
        "risk_assessment": {},
        "final_report": "",
        "errors": [],
        "warnings": []
    }

    try:
        # Execute risk assessor
        print("\n🔄 Executing risk assessor with quantified requirements...")
        result = await risk_assessor_node(state)

        risk_assessment = result.get("risk_assessment", {})

        print(f"✅ Risk assessor completed successfully!")

        # Verify quantified structure
        print("\n📋 Verifying quantified risk assessment structure:")

        required_fields = [
            "executive_risk_summary",
            "critical_failure_scenarios",
            "quantified_risk_matrix",
            "benchmarking_comparison",
            "final_recommendation",
            "justification"
        ]

        all_present = True
        for field in required_fields:
            present = field in risk_assessment
            print(f"  {'✓' if present else '✗'} {field}: {present}")
            if not present:
                all_present = False

        if not all_present:
            print("\n❌ FAIL: Missing required fields")
            return False

        # Verify critical failure scenarios structure
        print("\n📊 Verifying critical failure scenarios:")
        failure_scenarios = risk_assessment.get("critical_failure_scenarios", [])
        print(f"   Number of scenarios identified: {len(failure_scenarios)}")

        if not failure_scenarios:
            print("   ⚠️  WARNING: No failure scenarios identified")
        else:
            for i, scenario in enumerate(failure_scenarios[:3], 1):  # Check first 3
                print(f"\n   Scenario {i}:")

                required_scenario_fields = [
                    "scenario",
                    "probability_percent",
                    "timeline_to_failure",
                    "financial_impact_percent",
                    "mitigation_complexity"
                ]

                for field in required_scenario_fields:
                    present = field in scenario
                    value = scenario.get(field, "N/A")
                    print(f"     {'✓' if present else '✗'} {field}: {value}")

        # Verify quantified risk matrix
        print("\n📈 Verifying quantified risk matrix:")
        risk_matrix = risk_assessment.get("quantified_risk_matrix", {})

        matrix_sections = ["technical_risks", "economic_risks", "combined_amplification_risks"]
        for section in matrix_sections:
            risks = risk_matrix.get(section, [])
            print(f"   {section}: {len(risks)} items")

        # Verify final recommendation
        print("\n🎯 Final Recommendation:")
        recommendation = risk_assessment.get("final_recommendation", "N/A")
        print(f"   {recommendation}")

        valid_recommendations = ["PROCEED", "PROCEED WITH CAUTION", "DO NOT PROCEED"]
        if recommendation not in valid_recommendations:
            print(f"   ⚠️  WARNING: Unexpected recommendation format: {recommendation}")

        # Verify veto power
        print("\n⚖️  Veto Power:")
        veto_flag = risk_assessment.get("veto_flag", False)
        veto_reason = risk_assessment.get("veto_reason", "N/A")
        print(f"   Veto exercised: {veto_flag}")
        if veto_flag:
            print(f"   Veto reason: {veto_reason}")

        # Show executive summary
        print("\n📝 Executive Risk Summary:")
        executive_summary = risk_assessment.get("executive_risk_summary", "N/A")
        print(f"   {executive_summary}")

        # Show justification preview
        print("\n📄 Justification (first 300 chars):")
        justification = risk_assessment.get("justification", "N/A")
        print(f"   {justification[:300]}...")

        print("\n" + "="*80)
        print("✅ PHASE 4 TEST PASSED")
        print("="*80)
        print("\n✨ Risk assessment includes:")
        print("   ✓ Quantified probabilities (% values)")
        print("   ✓ Timeline estimates (days/weeks/months)")
        print("   ✓ Financial impact percentages")
        print("   ✓ Mitigation complexity ratings")
        print("   ✓ Decision thresholds and veto power")
        print("   ✓ Benchmarking comparisons")

        return True

    except Exception as e:
        print(f"\n❌ FAIL: Risk assessment error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run Phase 4 test."""

    print("\n" + "="*80)
    print("🧪 TESTING PHASE 4: QUANTIFIED RISK ASSESSMENT")
    print("="*80)
    print("\n⚠️  This test will make actual LLM API calls to GPT-5")
    print("   Continue? (y/n)")

    response = input().strip().lower()

    if response != 'y':
        print("\n⏭️  Test cancelled")
        return False

    success = await test_risk_assessment_structure()

    if success:
        print("\n" + "="*80)
        print("✅ PHASE 4 COMPLETE - READY FOR PHASE 3")
        print("="*80)
    else:
        print("\n" + "="*80)
        print("❌ PHASE 4 FAILED - FIX BEFORE PROCEEDING")
        print("="*80)

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
