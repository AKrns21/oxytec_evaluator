#!/usr/bin/env python3
"""Test JSON parsing logic"""

import json

def test_json_parsing():
    """Test the JSON parsing logic we're using in llm_service.py"""

    test_cases = [
        # Case 1: Pure JSON (no markdown)
        {
            "input": '{"test": "value", "number": 123}',
            "expected_valid": True,
            "description": "Pure JSON"
        },
        # Case 2: JSON wrapped in ```json
        {
            "input": '```json\n{"test": "value", "number": 123}\n```',
            "expected_valid": True,
            "description": "JSON with markdown code block"
        },
        # Case 3: JSON wrapped in ``` (no language)
        {
            "input": '```\n{"test": "value", "number": 123}\n```',
            "expected_valid": True,
            "description": "JSON with generic code block"
        },
        # Case 4: JSON with whitespace
        {
            "input": '  \n  {"test": "value"}  \n  ',
            "expected_valid": True,
            "description": "JSON with whitespace"
        },
    ]

    passed = 0
    failed = 0

    for test_case in test_cases:
        content = test_case["input"]

        # Apply our parsing logic
        content = content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]  # Remove ```json
        elif content.startswith("```"):
            content = content[3:]  # Remove ```

        if content.endswith("```"):
            content = content[:-3]  # Remove trailing ```

        content = content.strip()

        # Try to parse
        try:
            result = json.loads(content)
            if test_case["expected_valid"]:
                print(f"✅ PASS: {test_case['description']}")
                print(f"   Parsed: {result}")
                passed += 1
            else:
                print(f"❌ FAIL: {test_case['description']} - Expected to fail but succeeded")
                failed += 1
        except json.JSONDecodeError as e:
            if not test_case["expected_valid"]:
                print(f"✅ PASS: {test_case['description']} - Failed as expected")
                passed += 1
            else:
                print(f"❌ FAIL: {test_case['description']}")
                print(f"   Error: {e}")
                print(f"   Content: {repr(content[:100])}")
                failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*50}")

    return failed == 0

if __name__ == "__main__":
    success = test_json_parsing()
    exit(0 if success else 1)
