#!/usr/bin/env python3
"""
Verification script for subagent execution fix.

This script tests the validation changes without running the full workflow.
Run this after applying the fixes to verify schema compatibility.

Usage:
    python scripts/verify_subagent_fix.py
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.validation import (
    validate_planner_output,
    validate_subagent_result,
    SubagentDefinition,
    PlannerOutput
)
from pydantic import ValidationError


def test_planner_output_with_reasoning():
    """Test that planner output with 'reasoning' field validates."""
    print("TEST 1: Planner output with 'reasoning' field")

    test_output = {
        "subagents": [
            {
                "task": "Subagent: VOC Analysis Expert\n\nObjective: Analyze VOC composition...",
                "relevant_content": '{"voc_compounds": ["toluene", "xylene"]}'
            },
            {
                "task": "Subagent: Flow Specialist\n\nObjective: Calculate flow rates...",
                "relevant_content": '{"flow_rate": 1000}'
            },
            {
                "task": "Subagent: Technology Selector\n\nObjective: Select appropriate technology...",
                "relevant_content": '{"constraints": ["ATEX Zone 2"]}'
            }
        ],
        "reasoning": "Created 3 subagents for parallel analysis of chemistry, engineering, and technology selection."
    }

    try:
        validated = validate_planner_output(test_output)
        print(f"✓ PASS - Validated successfully")
        print(f"  - Subagents: {len(validated.subagents)}")
        print(f"  - Reasoning: {validated.reasoning[:50]}..." if validated.reasoning else "  - Reasoning: None")
        return True
    except ValidationError as e:
        print(f"✗ FAIL - Validation error:")
        print(f"  {str(e)}")
        return False


def test_planner_output_with_rationale():
    """Test backward compatibility: output with 'rationale' still validates."""
    print("\nTEST 2: Planner output with 'rationale' field (backward compatibility)")

    test_output = {
        "subagents": [
            {
                "task": "Subagent: VOC Analysis Expert\n\nObjective: Analyze VOC composition...",
                "relevant_content": '{"voc_compounds": ["toluene"]}'
            },
            {
                "task": "Subagent: Flow Specialist\n\nObjective: Calculate flow rates...",
                "relevant_content": '{"flow_rate": 1000}'
            },
            {
                "task": "Subagent: Technology Selector\n\nObjective: Select appropriate technology...",
                "relevant_content": '{"constraints": []}'
            }
        ],
        "rationale": "Legacy field name for reasoning"
    }

    try:
        validated = validate_planner_output(test_output)
        print(f"✓ PASS - Backward compatibility maintained")
        print(f"  - Subagents: {len(validated.subagents)}")
        return True
    except ValidationError as e:
        print(f"✗ FAIL - Validation error:")
        print(f"  {str(e)}")
        return False


def test_long_task_description():
    """Test that long task descriptions (up to 8000 chars) validate."""
    print("\nTEST 3: Long task description (8000 characters)")

    long_task = (
        "Subagent: Comprehensive VOC Analysis Expert\n\n"
        + "Objective: " + ("Analyze VOC composition in detail. " * 50) + "\n\n"
        + "Questions:\n" + "\n".join(f"- Question {i}: " + ("What is the impact? " * 10) for i in range(20)) + "\n\n"
        + "Method hints:\n" + ("Use authoritative sources. " * 100) + "\n\n"
        + "Deliverables:\n" + ("Provide detailed tables. " * 50)
    )

    print(f"  Task length: {len(long_task)} characters")

    test_output = {
        "subagents": [
            {
                "task": long_task,
                "relevant_content": '{"voc_compounds": ["toluene"]}'
            },
            {
                "task": "Subagent: Flow Specialist\n\nObjective: Calculate flow rates...",
                "relevant_content": '{"flow_rate": 1000}'
            },
            {
                "task": "Subagent: Technology Selector\n\nObjective: Select technology...",
                "relevant_content": '{"constraints": []}'
            }
        ],
        "reasoning": "Testing long task description support"
    }

    try:
        validated = validate_planner_output(test_output)
        print(f"✓ PASS - Long tasks validated successfully")
        print(f"  - Longest task: {len(validated.subagents[0].task)} chars")
        return True
    except ValidationError as e:
        print(f"✗ FAIL - Validation error:")
        print(f"  {str(e)}")
        return False


def test_too_few_subagents():
    """Test that <3 subagents fails validation (as expected)."""
    print("\nTEST 4: Too few subagents (should fail)")

    test_output = {
        "subagents": [
            {
                "task": "Subagent: VOC Analysis\n\nObjective: Analyze...",
                "relevant_content": '{"voc": ["toluene"]}'
            },
            {
                "task": "Subagent: Flow Analysis\n\nObjective: Calculate...",
                "relevant_content": '{"flow": 1000}'
            }
        ],
        "reasoning": "Only 2 subagents - should fail min_length=3 constraint"
    }

    try:
        validated = validate_planner_output(test_output)
        print(f"✗ FAIL - Should have rejected <3 subagents!")
        return False
    except ValidationError as e:
        print(f"✓ PASS - Correctly rejected (expected)")
        print(f"  - Error: {str(e)[:100]}...")
        return True


def test_missing_required_fields():
    """Test that subagents without required fields fail validation."""
    print("\nTEST 5: Missing required fields (should fail)")

    test_output = {
        "subagents": [
            {
                "task": "Subagent: VOC Analysis\n\nObjective: Analyze...",
                # Missing 'relevant_content'!
            },
            {
                "task": "Subagent: Flow Analysis\n\nObjective: Calculate...",
                "relevant_content": '{"flow": 1000}'
            },
            {
                "task": "Subagent: Technology Selection\n\nObjective: Select...",
                "relevant_content": '{"constraints": []}'
            }
        ],
        "reasoning": "First subagent missing relevant_content"
    }

    try:
        validated = validate_planner_output(test_output)
        print(f"✗ FAIL - Should have rejected missing field!")
        return False
    except ValidationError as e:
        print(f"✓ PASS - Correctly rejected (expected)")
        print(f"  - Error: {str(e)[:100]}...")
        return True


def test_subagent_result_validation():
    """Test that subagent results validate correctly."""
    print("\nTEST 6: Subagent result validation")

    test_result = {
        "agent_name": "voc_analysis_expert",
        "instance": "subagent_0_voc_analysis_expert",
        "task": "Analyze VOC composition and reactivity...",
        "result": "SECTION 1: VOC Analysis\n\nIdentified 5 key VOC compounds...",
        "duration_seconds": 15.3,
        "tokens_used": 1250
    }

    try:
        validated = validate_subagent_result(test_result)
        print(f"✓ PASS - Subagent result validated")
        print(f"  - Agent: {validated.agent_name}")
        print(f"  - Duration: {validated.duration_seconds}s")
        print(f"  - Tokens: {validated.tokens_used}")
        return True
    except ValidationError as e:
        print(f"✗ FAIL - Validation error:")
        print(f"  {str(e)}")
        return False


def main():
    """Run all validation tests."""
    print("=" * 70)
    print("SUBAGENT EXECUTION FIX - VALIDATION TEST SUITE")
    print("=" * 70)
    print()

    tests = [
        test_planner_output_with_reasoning,
        test_planner_output_with_rationale,
        test_long_task_description,
        test_too_few_subagents,
        test_missing_required_fields,
        test_subagent_result_validation,
    ]

    results = []
    for test_func in tests:
        results.append(test_func())

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("✓ ALL TESTS PASSED - Schema validation working correctly")
        return 0
    else:
        print(f"✗ {total - passed} TEST(S) FAILED - Review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
