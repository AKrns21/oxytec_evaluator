"""
Test script for Technology RAG system.

This script validates that the technology knowledge base RAG is working correctly
by running representative queries and displaying results.

Usage:
    python scripts/test_technology_rag.py
    python scripts/test_technology_rag.py --verbose
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.session import AsyncSessionLocal
from app.services.technology_rag_service import TechnologyRAGService
from app.utils.logger import get_logger

logger = get_logger(__name__)


# Test queries covering different use cases
TEST_QUERIES = [
    {
        "query": "UV ozone formaldehyde removal textile industry",
        "description": "Test: UV/ozone technology for formaldehyde in textiles",
        "expected_tech": "uv_ozone",
        "expected_pollutant": "formaldehyde",
        "expected_industry": "textile"
    },
    {
        "query": "scrubber ammonia removal livestock wastewater",
        "description": "Test: Scrubber for ammonia in agriculture/wastewater",
        "expected_tech": "scrubber",
        "expected_pollutant": "ammonia",
        "expected_industry": "wastewater"
    },
    {
        "query": "VOC removal food processing fryer odor",
        "description": "Test: VOC and odor treatment in food industry",
        "expected_pollutant": "VOC",
        "expected_industry": "food_processing"
    },
    {
        "query": "H2S removal efficiency biogas slaughterhouse",
        "description": "Test: H2S treatment in food processing/biogas",
        "expected_pollutant": "H2S",
        "expected_industry": "food_processing"
    },
    {
        "query": "CEA CFA technical specifications flow rate capacity",
        "description": "Test: Technical data retrieval for specific products",
        "expected_products": ["CEA", "CFA"]
    },
    {
        "query": "multi-stage hybrid system combination wäscher UV ozone",
        "description": "Test: Hybrid/combination systems",
        "expected_tech": "hybrid"
    },
]


def print_header(text: str):
    """Print formatted header."""
    print(f"\n{'=' * 80}")
    print(f"  {text}")
    print(f"{'=' * 80}\n")


def print_result(result: Dict[str, Any], verbose: bool = False):
    """Print a single search result."""
    print(f"  📄 Page {result['page_number']}: {result['title']}")
    print(f"     Technology: {result['technology_type']}")
    print(f"     Chunk Type: {result['chunk_type']}")
    print(f"     Similarity: {result['similarity']:.3f}")

    if result.get('pollutant_types'):
        print(f"     Pollutants: {', '.join(result['pollutant_types'])}")
    if result.get('industries'):
        print(f"     Industries: {', '.join(result['industries'])}")
    if result.get('products_mentioned'):
        print(f"     Products: {', '.join(result['products_mentioned'])}")

    if verbose and result.get('chunk_text'):
        preview = result['chunk_text'][:200].replace('\n', ' ')
        print(f"     Preview: {preview}...")

    print()


def validate_result(result: Dict[str, Any], expected: Dict[str, Any]) -> List[str]:
    """Validate a result against expected values."""
    issues = []

    # Check technology type
    if expected.get('expected_tech'):
        if result['technology_type'] != expected['expected_tech']:
            issues.append(
                f"Expected technology '{expected['expected_tech']}', "
                f"got '{result['technology_type']}'"
            )

    # Check pollutants
    if expected.get('expected_pollutant'):
        pollutants = result.get('pollutant_types', [])
        if expected['expected_pollutant'] not in pollutants:
            issues.append(
                f"Expected pollutant '{expected['expected_pollutant']}' "
                f"not in result pollutants: {pollutants}"
            )

    # Check industries
    if expected.get('expected_industry'):
        industries = result.get('industries', [])
        if expected['expected_industry'] not in industries:
            issues.append(
                f"Expected industry '{expected['expected_industry']}' "
                f"not in result industries: {industries}"
            )

    # Check products
    if expected.get('expected_products'):
        products = result.get('products_mentioned', [])
        for expected_product in expected['expected_products']:
            if expected_product not in products:
                issues.append(
                    f"Expected product '{expected_product}' "
                    f"not in result products: {products}"
                )

    return issues


async def run_tests(verbose: bool = False):
    """Run all test queries and report results."""

    print_header("Testing Oxytec Technology RAG System")

    async with AsyncSessionLocal() as db:
        tech_rag = TechnologyRAGService(db)

        total_queries = len(TEST_QUERIES)
        passed = 0
        failed = 0

        for i, test_case in enumerate(TEST_QUERIES, 1):
            print(f"\n[{i}/{total_queries}] {test_case['description']}")
            print(f"Query: \"{test_case['query']}\"")
            print()

            try:
                # Execute search
                results = await tech_rag.search_knowledge(
                    query=test_case['query'],
                    top_k=3  # Limit to top 3 for readability
                )

                if not results:
                    print("  ❌ No results found!")
                    failed += 1
                    continue

                print(f"  ✅ Found {len(results)} results:")
                print()

                # Display results
                for result in results:
                    print_result(result, verbose=verbose)

                # Validate top result
                top_result = results[0]
                issues = validate_result(top_result, test_case)

                if issues:
                    print("  ⚠️  Validation issues:")
                    for issue in issues:
                        print(f"     - {issue}")
                    failed += 1
                else:
                    print("  ✅ Validation passed")
                    passed += 1

            except Exception as e:
                print(f"  ❌ Error: {e}")
                logger.error("test_query_failed", query=test_case['query'], error=str(e))
                failed += 1

        # Summary
        print_header("Test Summary")
        print(f"Total queries: {total_queries}")
        print(f"Passed: {passed} ({passed/total_queries*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total_queries*100:.1f}%)")

        if passed == total_queries:
            print("\n🎉 All tests passed!")
            return True
        else:
            print(f"\n⚠️  {failed} test(s) failed")
            return False


async def test_filters():
    """Test metadata filtering capabilities."""

    print_header("Testing Metadata Filters")

    async with AsyncSessionLocal() as db:
        tech_rag = TechnologyRAGService(db)

        # Test 1: Technology type filter
        print("\n1. Filter by technology_type='uv_ozone'")
        results = await tech_rag.search_knowledge(
            query="VOC removal",
            technology_type="uv_ozone",
            top_k=3
        )
        print(f"   Found {len(results)} UV/ozone results")
        for r in results:
            print(f"   - {r['title']} (type: {r['technology_type']})")

        # Test 2: Pollutant filter
        print("\n2. Filter by pollutant='formaldehyde'")
        results = await tech_rag.search_knowledge(
            query="removal efficiency",
            pollutant_filter="formaldehyde",
            top_k=3
        )
        print(f"   Found {len(results)} formaldehyde results")
        for r in results:
            print(f"   - {r['title']} (pollutants: {r['pollutant_types']})")

        # Test 3: Industry filter
        print("\n3. Filter by industry='food_processing'")
        results = await tech_rag.search_knowledge(
            query="application example",
            industry_filter="food_processing",
            top_k=3
        )
        print(f"   Found {len(results)} food processing results")
        for r in results:
            print(f"   - {r['title']} (industries: {r['industries']})")

        print("\n✅ Filter tests completed")


async def test_special_queries():
    """Test special query methods."""

    print_header("Testing Special Query Methods")

    async with AsyncSessionLocal() as db:
        tech_rag = TechnologyRAGService(db)

        # Test 1: Get technologies by pollutant
        print("\n1. Get all technologies for pollutant='VOC'")
        techs = await tech_rag.get_technologies_by_pollutant("VOC")
        print(f"   Found {len(techs)} technologies")
        for tech in techs[:5]:  # Show first 5
            print(f"   - {tech['technology_type']}: {tech['title']}")

        # Test 2: Get application examples
        print("\n2. Get application examples for food_processing")
        examples = await tech_rag.get_application_examples(industry="food_processing")
        print(f"   Found {len(examples)} examples")
        for ex in examples[:3]:  # Show first 3
            print(f"   - Page {ex['page_number']}: {ex['title']}")

        print("\n✅ Special query tests completed")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Technology RAG system")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output including text previews"
    )
    parser.add_argument(
        "--filters-only",
        action="store_true",
        help="Only test metadata filters"
    )
    parser.add_argument(
        "--special-only",
        action="store_true",
        help="Only test special query methods"
    )

    args = parser.parse_args()

    if args.filters_only:
        asyncio.run(test_filters())
    elif args.special_only:
        asyncio.run(test_special_queries())
    else:
        # Run main tests
        success = asyncio.run(run_tests(verbose=args.verbose))

        # Also run additional tests if main tests passed
        if success and not args.verbose:
            asyncio.run(test_filters())
            asyncio.run(test_special_queries())

        sys.exit(0 if success else 1)
