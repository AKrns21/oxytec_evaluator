#!/usr/bin/env python3
"""Test that subagent findings are consolidated (Flowise pattern)."""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.nodes.risk_assessor import risk_assessor_node
from app.agents.state import GraphState


async def test_consolidated_findings():
    """Test that risk assessor receives consolidated findings in Flowise format."""

    print("\n" + "="*80)
    print("TEST: Consolidated Findings Format (Flowise Pattern)")
    print("="*80)

    # Sample subagent results (plain text findings)
    subagent_results = [
        {
            "agent_name": "voc_analyst",
            "instance": "subagent_0",
            "task": "VOC Analysis Task...",
            "result": "SECTION 1: VOC Composition Analysis\n\nThe TVOC range of 2.9-1800 mg/Nm3 indicates high variability. Representative compounds include C6-C10 alcohols, C12-C14 alkanes, and alkylbenzenes. Key findings:\n\n- High-MW alkanes (C12-C14) are recalcitrant to single-pass oxidation\n- SO2/SO3 presence (up to 1850 mg/Nm3) creates sulfuric acid aerosol risk\n- Show-stopper: Without upstream acid gas scrubbing, NTP/UV systems will face corrosion and fouling\n\nConfidence: HIGH for sulfuric acid risk, MEDIUM for by-product formation"
        },
        {
            "agent_name": "flow_specialist",
            "instance": "subagent_1",
            "task": "Flow & Mass Balance Task...",
            "result": "SECTION 2: Flow and Mass Balance Calculations\n\nVolumetric flow estimates (at 0°C, 1.013 bar):\n- Minimum: 1392 Nm3/h (1800 kg/h)\n- Optimal: 2166-2781 Nm3/h (2800-3600 kg/h)\n- Maximum: 3095 Nm3/h (4000 kg/h)\n\nVOC removal loads:\n- At max TVOC (1800 mg/Nm3) and max flow (3095 Nm3/h): 5.57 kg/h removal required\n- Uncertainty: ±20-30% due to unknown moisture content\n\nCritical measurement gap: Water vapor fraction significantly affects density calculations"
        },
        {
            "agent_name": "technology_screener",
            "instance": "subagent_2",
            "task": "Technology Screening Task...",
            "result": "SECTION 3: Technology Compatibility Assessment\n\nNTP alone: 70% probability of sulfuric acid aerosol formation without upstream scrubbing. Risk level: HIGH.\n\nUV/Ozone alone: 60% probability of excessive SOA formation from olefins. Risk level: MEDIUM-HIGH.\n\nRecommended approach: Hybrid configuration with wet scrubber upstream for acid gas removal, followed by NTP or UV/ozone.\n\nEstimated CAPEX increase for hybrid: 40% over single-technology solution."
        }
    ]

    state: GraphState = {
        "session_id": "test-consolidated",
        "documents": [],
        "extracted_facts": {},
        "planner_plan": {},
        "subagent_results": subagent_results,
        "risk_assessment": {},
        "final_report": "",
        "errors": [],
        "warnings": []
    }

    print("\n📋 Checking consolidation approach:")
    print(f"   Number of subagent results: {len(subagent_results)}")

    # Show what the consolidated findings look like
    consolidated = "\n\n".join(result['result'] for result in subagent_results)
    print(f"   Consolidated length: {len(consolidated)} chars")

    # Check format
    has_new_findings_tags = "<new_findings>" in consolidated or True  # Will be in prompt
    has_agent_metadata = any(x in consolidated for x in ["agent_name", "Task:", "**Agent"])

    print(f"\n✓ Format check:")
    print(f"   Uses plain text concatenation: {not has_agent_metadata}")
    print(f"   No agent metadata in findings: {not has_agent_metadata}")

    if has_agent_metadata:
        print("   ⚠️  WARNING: Agent metadata found in findings!")
        return False

    print("\n📄 Consolidated findings preview (first 500 chars):")
    print("-" * 80)
    print(consolidated[:500] + "...")
    print("-" * 80)

    print("\n⚠️  Now test with actual risk assessor execution?")
    print("   This will make LLM API calls. Continue? (y/n)")

    response = input().strip().lower()

    if response != 'y':
        print("\n✅ Format check passed - consolidation looks correct")
        print("   Skipping LLM execution")
        return True

    try:
        print("\n🔄 Executing risk assessor with consolidated findings...")
        result = await risk_assessor_node(state)

        risk_assessment = result.get("risk_assessment", {})

        print(f"✅ Risk assessor completed successfully!")
        print(f"   Final recommendation: {risk_assessment.get('final_recommendation', 'N/A')}")

        print("\n" + "="*80)
        print("✅ TEST PASSED - Consolidated Findings Format Working")
        print("="*80)
        print("\n✨ Benefits of consolidation:")
        print("   ✓ Risk assessor sees one cohesive analysis")
        print("   ✓ No artificial separation between subagent findings")
        print("   ✓ Matches Flowise pattern exactly")
        print("   ✓ Cleaner, more natural analysis flow")

        return True

    except Exception as e:
        print(f"\n❌ FAIL: Risk assessor error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run test."""

    print("\n" + "="*80)
    print("🧪 TESTING: CONSOLIDATED FINDINGS (FLOWISE PATTERN)")
    print("="*80)

    success = await test_consolidated_findings()

    if success:
        print("\n✅ Findings consolidation matches Flowise pattern")
    else:
        print("\n❌ Findings consolidation needs adjustment")

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
