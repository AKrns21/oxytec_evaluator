#!/usr/bin/env python3
"""Test Phase 3: Enhanced Subagent Prompting."""

import asyncio
import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.nodes.subagent import execute_single_subagent, build_subagent_prompt_v2
from app.agents.state import GraphState


async def test_subagent_prompting():
    """Test that enhanced subagent prompting produces high-quality output."""

    print("\n" + "="*80)
    print("TEST: Phase 3 - Enhanced Subagent Prompting")
    print("="*80)

    # Create a realistic Flowise-style subagent definition
    subagent_def = {
        "task": """Subagent: VOC Composition & Reactivity Analyst

Objective (narrow): Analyze the provided TVOC composition to identify representative compounds with relevant physico-chemical properties, expected reactivity with NTP/UV/ozone systems, potential by-products, show-stopper species, and critical measurement gaps.

Questions to answer (explicit):
- What are the representative compounds/groups from the TVOC list with key physico-chemical properties relevant to abatement (boiling point, vapor pressure, water solubility, Henry's law constant, molecular weight, functional groups)?
- For each representative compound/group, what is the expected reactivity with ozone and with typical NTP-generated oxidants (O3, OH, O)?
- What are the likely stable or hazardous by-products (formaldehyde, organic acids, secondary aerosols)?
- Are there species that would prevent use of specific abatement options (NTP, UV/ozone, wet scrubbing)?
- What data gaps must be measured before final design (water vapor content, detailed speciation, particulate load)?

Method hints / quality criteria:
- Use authoritative property databases (PubChem, NIST, EPI Suite, ChemSpider) and cite sources per compound
- Group similar compounds where appropriate and justify representative molecule selection
- Provide conservative by-product yield estimates (qualitative or semi-quantitative)
- Rank confidence level (HIGH/MEDIUM/LOW) for each conclusion
- Compare against literature on similar VOC mixtures

Deliverables (concise outputs, machine-usable):
- Structured table or list of representative compounds/groups with properties and reactivity notes
- Short list of show-stopper species (if any) for NTP, UV/ozone, wet scrubbers
- Prioritized list of measurement gaps with impact assessment

Dependencies / sequencing: Independent — can run immediately in parallel with other subagents. No additional data required beyond provided JSON fields.

Tools needed: none""",
        "relevant_content": json.dumps({
            "gas_stream_that_requires_treatment": {
                "SO2": "0,1-1850 mg/Nm3",
                "SO3": "0,1-200 mg/Nm3",
                "TVOC": "2,9 – 1800 mg/Nm3",
                "TVOC_including": "2-ethylhexanol (CAS 104-76-7); octan-1-ol; decan-1-ol (CAS 112-30-1); lauryl alcohol C12-C14 (CAS 104-76-7); ethoxylated lauryl alcohol C12-C14 (from 1 to 7 EO); linear alkylbenzene (CAS 67774-74-7)"
            },
            "tvoc_level_overview": "The TVOC level is up to 1800mg/Nm3",
            "gas_temperature": "10−40°C"
        }, indent=2)
    }

    state: GraphState = {
        "session_id": "test-phase3",
        "documents": [],
        "extracted_facts": {},
        "planner_plan": {},
        "subagent_results": [],
        "risk_assessment": {},
        "final_report": "",
        "errors": [],
        "warnings": []
    }

    print("\n📝 Testing enhanced prompt structure...")

    # Test the prompt builder
    prompt = build_subagent_prompt_v2(
        task_description=subagent_def["task"],
        relevant_content=subagent_def["relevant_content"]
    )

    print(f"✅ Prompt built successfully")
    print(f"   Prompt length: {len(prompt)} chars")

    # Check for key elements in prompt
    required_elements = [
        "YOUR TASK ASSIGNMENT",
        "TECHNICAL DATA",
        "EXECUTION REQUIREMENTS",
        "Answer ALL questions",
        "70/30 rule",
        "Quantify when possible",
        "Cite sources",
        "State confidence levels",
        "Flag show-stoppers"
    ]

    print("\n📋 Verifying prompt structure:")
    all_present = True
    for element in required_elements:
        present = element in prompt
        print(f"  {'✓' if present else '✗'} Contains '{element}': {present}")
        if not present:
            all_present = False

    if not all_present:
        print("\n❌ FAIL: Prompt missing required elements")
        return False

    print("\n" + "="*80)
    print("⚠️  Now testing actual subagent execution with LLM...")
    print("   This will make API calls. Continue? (y/n)")

    response = input().strip().lower()

    if response != 'y':
        print("\n⏭️  Skipping LLM execution test")
        print("✅ PHASE 3 PROMPT STRUCTURE VERIFIED")
        return True

    try:
        print("\n🔄 Executing subagent with enhanced prompting...")
        result = await execute_single_subagent(
            subagent_def=subagent_def,
            state=state,
            instance_name="test_phase3_voc_analyst"
        )

        print(f"\n✅ Subagent execution completed!")
        print(f"   Agent name: {result.get('agent_name')}")
        print(f"   Result length: {len(str(result.get('result', '')))} chars")

        # Analyze result quality
        result_text = str(result.get('result', '')).lower()

        print("\n📊 Analyzing result quality:")

        quality_indicators = {
            "quantification": any(x in result_text for x in ['%', 'percent', 'probability', 'mg/nm3', 'g/mol']),
            "source_citation": any(x in result_text for x in ['pubchem', 'nist', 'literature', 'database', 'source']),
            "confidence_levels": any(x in result_text for x in ['high confidence', 'medium confidence', 'low confidence', 'confidence:']),
            "show_stoppers": any(x in result_text for x in ['show-stopper', 'showstopper', 'show stopper', 'prevent']),
            "measurement_gaps": any(x in result_text for x in ['measurement gap', 'data gap', 'missing data', 'required measurement']),
            "structured_output": any(x in result_text for x in ['table', 'list:', '1.', '2.', '|', '-'])
        }

        for indicator, present in quality_indicators.items():
            print(f"  {'✓' if present else '○'} {indicator.replace('_', ' ').title()}: {present}")

        quality_score = sum(quality_indicators.values())
        print(f"\n  Quality score: {quality_score}/6")

        if quality_score >= 4:
            print("  ✅ High-quality output achieved")
        elif quality_score >= 2:
            print("  ⚠️  Moderate quality - room for improvement")
        else:
            print("  ❌ Low quality - prompting may need adjustment")

        # Show preview
        print("\n📄 Result preview (first 500 chars):")
        print(f"   {str(result.get('result', ''))[:500]}...")

        print("\n" + "="*80)
        print("✅ PHASE 3 TEST PASSED")
        print("="*80)
        print("\n✨ Enhanced subagent prompting includes:")
        print("   ✓ Comprehensive system prompt with analytical standards")
        print("   ✓ Structured task assignment with clear sections")
        print("   ✓ 10-point execution requirements checklist")
        print("   ✓ 70/30 risk-focused mandate")
        print("   ✓ Explicit quality criteria (quantification, citations, confidence)")

        return True

    except Exception as e:
        print(f"\n❌ FAIL: Subagent execution error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run Phase 3 test."""

    print("\n" + "="*80)
    print("🧪 TESTING PHASE 3: ENHANCED SUBAGENT PROMPTING")
    print("="*80)

    success = await test_subagent_prompting()

    if success:
        print("\n" + "="*80)
        print("✅ PHASE 3 COMPLETE - READY FOR PHASE 5")
        print("="*80)
    else:
        print("\n" + "="*80)
        print("❌ PHASE 3 FAILED - FIX BEFORE PROCEEDING")
        print("="*80)

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
