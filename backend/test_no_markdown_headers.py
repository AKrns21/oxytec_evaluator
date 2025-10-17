#!/usr/bin/env python3
"""Test that subagents don't use markdown headers."""

import asyncio
import sys
import json
import re
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.nodes.subagent import execute_single_subagent
from app.agents.state import GraphState


async def test_no_markdown_headers():
    """Test that subagent output doesn't contain markdown headers."""

    print("\n" + "="*80)
    print("TEST: No Markdown Headers in Subagent Output")
    print("="*80)

    # Create a realistic subagent definition
    subagent_def = {
        "task": """Subagent: Flow & Mass Balance Specialist

Objective (narrow): Convert provided mass flow (kg/h) to volumetric flow (Nm3/h) and calculate VOC removal loads.

Questions to answer (explicit):
- What are the Nm3/h flow rates for minimum, optimal, and maximum mass flows?
- What are the mass removal loads in g/h for each scenario?

Method hints / quality criteria:
- Use standard conditions (0°C, 1.013 bar)
- Show calculations step-by-step
- Provide uncertainty bounds

Deliverables (concise outputs):
- Table of Nm3/h estimates
- Table of VOC removal loads

Dependencies / sequencing: Independent

Tools needed: none""",
        "relevant_content": json.dumps({
            "gas_flow": {
                "minimum": "1800kg/h",
                "optimal": "2800kg/h−3600kg/h",
                "maximum": "4000kg/h"
            },
            "tvoc_level_overview": "Up to 1800mg/Nm3"
        }, indent=2)
    }

    state: GraphState = {
        "session_id": "test-markdown",
        "documents": [],
        "extracted_facts": {},
        "planner_plan": {},
        "subagent_results": [],
        "risk_assessment": {},
        "final_report": "",
        "errors": [],
        "warnings": []
    }

    print("\n⚠️  This test will make actual LLM API calls")
    print("   Continue? (y/n)")

    response = input().strip().lower()

    if response != 'y':
        print("\n⏭️  Test cancelled")
        return False

    try:
        print("\n🔄 Executing subagent...")
        result = await execute_single_subagent(
            subagent_def=subagent_def,
            state=state,
            instance_name="test_markdown_check"
        )

        print(f"✅ Subagent execution completed!")

        result_text = str(result.get('result', ''))
        print(f"   Result length: {len(result_text)} chars")

        # Check for markdown headers
        print("\n🔍 Checking for markdown headers...")

        markdown_header_patterns = [
            (r'^#{1,6}\s+', 'ATX headers (# ##)'),
            (r'^\S.*\n={3,}', 'Setext headers (underlined with =)'),
            (r'^\S.*\n-{3,}', 'Setext headers (underlined with -)')
        ]

        issues_found = []

        for pattern, description in markdown_header_patterns:
            matches = re.findall(pattern, result_text, re.MULTILINE)
            if matches:
                issues_found.append({
                    'type': description,
                    'count': len(matches),
                    'examples': matches[:3]  # Show first 3 examples
                })

        if issues_found:
            print("   ❌ FAIL: Found markdown headers!")
            for issue in issues_found:
                print(f"      - {issue['type']}: {issue['count']} occurrences")
                for example in issue['examples']:
                    print(f"        Example: {repr(example[:50])}")

            print("\n📄 Result preview (first 800 chars):")
            print("-" * 80)
            print(result_text[:800])
            print("-" * 80)

            return False
        else:
            print("   ✅ PASS: No markdown headers found!")

            # Check for good formatting instead
            good_patterns = {
                'section_labels': bool(re.search(r'(SECTION|Part|Analysis|Summary)[\s\d:]+', result_text, re.IGNORECASE)),
                'bullet_points': bool(re.search(r'^\s*[\-\*•]\s+', result_text, re.MULTILINE)),
                'numbered_lists': bool(re.search(r'^\s*\d+\.\s+', result_text, re.MULTILINE)),
                'tables': bool(re.search(r'\|.*\|', result_text))
            }

            print("\n📋 Good formatting indicators:")
            for indicator, present in good_patterns.items():
                print(f"   {'✓' if present else '○'} {indicator.replace('_', ' ').title()}: {present}")

            print("\n📄 Result preview (first 800 chars):")
            print("-" * 80)
            print(result_text[:800])
            print("-" * 80)

            print("\n" + "="*80)
            print("✅ TEST PASSED - Clean formatting without markdown headers")
            print("="*80)
            return True

    except Exception as e:
        print(f"\n❌ FAIL: Subagent execution error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run test."""

    print("\n" + "="*80)
    print("🧪 TESTING: MARKDOWN HEADER REMOVAL")
    print("="*80)

    success = await test_no_markdown_headers()

    if success:
        print("\n✨ Subagent outputs will now be clean and parseable by risk assessor")
    else:
        print("\n⚠️  Subagent still using markdown headers - may need prompt adjustment")

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
