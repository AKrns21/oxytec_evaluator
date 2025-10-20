"""
Phase 3 Validation: Full Agent Workflow with RAG Integration

Tests the complete multi-agent workflow including:
1. Document extraction (simulated)
2. Planner agent creating subagents
3. Subagents using RAG to query Oxytec technology knowledge
4. Risk assessor synthesizing findings
5. Writer generating feasibility report

Test Case: Ammonia Scrubber for Livestock/Poultry Facility
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.agents.graph import create_agent_graph
from app.agents.state import GraphState
from app.utils.logger import get_logger

logger = get_logger(__name__)


# Simulated extraction for ammonia scrubber test case
AMMONIA_SCRUBBER_FACTS = {
    "customer_name": "Geflügelfarm Schmidt GmbH",
    "project_name": "Abluftbehandlung Geflügelstall",
    "location": "Cloppenburg, Deutschland",
    "industry": "Geflügelhaltung / Livestock",
    "pollutants": [
        {
            "name": "Ammoniak (NH3)",
            "concentration": "50-80 ppm",
            "flow_rate": "15,000 m³/h",
            "removal_efficiency_required": "90%"
        },
        {
            "name": "Geruchsstoffe",
            "concentration": "hochkonzentriert",
            "removal_efficiency_required": "95%"
        },
        {
            "name": "Bioaerosole",
            "concentration": "erhöht",
            "removal_efficiency_required": "nicht spezifiziert"
        }
    ],
    "process_conditions": {
        "temperature": "20-25°C",
        "humidity": "70-80%",
        "airflow_rate": "15,000 m³/h",
        "operating_hours": "24/7 kontinuierlich"
    },
    "constraints": {
        "space_limitations": "Begrenzter Platz für Installation",
        "budget": "€150,000-€200,000",
        "timeline": "Installation innerhalb 4 Monate",
        "regulatory": "Einhaltung TA Luft Grenzwerte für Ammoniak"
    },
    "customer_priorities": [
        "Hohe Ammoniakabscheidung (>90%)",
        "Geruchsreduktion für Anwohner",
        "Niedrige Betriebskosten",
        "Wartungsarm"
    ]
}


async def run_phase3_validation():
    """Run Phase 3 validation with ammonia scrubber test case."""

    print("=" * 80, flush=True)
    print("Phase 3 Validation: Full Agent Workflow Test", flush=True)
    print("Test Case: Ammonia Scrubber for Livestock Facility", flush=True)
    print("=" * 80, flush=True)

    # Create workflow graph
    print("\n[1/6] Creating workflow graph...", flush=True)
    try:
        workflow = create_agent_graph()
        print("✅ Workflow graph created", flush=True)
    except Exception as e:
        print(f"❌ Failed to create workflow: {e}", flush=True)
        return False

    # Initialize state with extracted facts
    print("\n[2/6] Initializing state with extracted facts...", flush=True)
    initial_state: GraphState = {
        "session_id": "phase3_validation",
        "documents": [],  # Empty since we're starting with pre-extracted facts
        "user_input": {},
        "extracted_facts": AMMONIA_SCRUBBER_FACTS,
        "planner_plan": {},  # Will be populated by planner
        "subagent_results": [],
        "risk_assessment": None,
        "final_report": None,
        "errors": [],
        "warnings": [],
    }
    print("✅ State initialized", flush=True)
    print(f"  Customer: {AMMONIA_SCRUBBER_FACTS['customer_name']}", flush=True)
    print(f"  Industry: {AMMONIA_SCRUBBER_FACTS['industry']}", flush=True)
    print(f"  Main Pollutant: {AMMONIA_SCRUBBER_FACTS['pollutants'][0]['name']}", flush=True)
    print(f"  Flow Rate: {AMMONIA_SCRUBBER_FACTS['process_conditions']['airflow_rate']}", flush=True)

    # Run workflow
    print("\n[3/6] Starting agent workflow...", flush=True)
    print("This will take 1-2 minutes...\n", flush=True)

    try:
        # Execute workflow
        final_state = await workflow.ainvoke(initial_state)

        # Debug: Print final state keys
        print(f"\n[DEBUG] Final state keys: {list(final_state.keys())}", flush=True)
        print(f"[DEBUG] Planner plan: {final_state.get('planner_plan', {})}", flush=True)
        print(f"[DEBUG] Subagent results: {len(final_state.get('subagent_results', []))}", flush=True)

        # Analyze results
        print("\n[4/6] Analyzing workflow results...", flush=True)

        # Check planner output
        planner_plan = final_state.get("planner_plan", {})
        subagent_defs = planner_plan.get("subagents", []) if isinstance(planner_plan, dict) else []
        if subagent_defs and len(subagent_defs) > 0:
            num_subagents = len(subagent_defs)
            print(f"✅ Planner created {num_subagents} subagents", flush=True)
            for i, subagent in enumerate(subagent_defs, 1):
                print(f"  {i}. {subagent.get('name', 'Unknown')}: {subagent.get('task_description', '')[:60]}...", flush=True)
        else:
            print("❌ No subagents created", flush=True)
            return False

        # Check subagent results
        print("\n[5/6] Checking subagent results...", flush=True)
        subagent_results = final_state.get("subagent_results", [])
        if subagent_results and len(subagent_results) > 0:
            num_results = len(subagent_results)
            print(f"✅ Received {num_results} subagent results", flush=True)

            # Check for RAG usage
            rag_usage_count = 0
            for result in subagent_results:
                # Check if result mentions Oxytec products or technologies
                result_text = result.get("findings", "").lower()
                if any(prod in result_text for prod in ["cwa", "csa", "cea", "oxytec"]):
                    rag_usage_count += 1

            print(f"  {rag_usage_count}/{num_results} subagents used Oxytec knowledge (RAG)", flush=True)
        else:
            print("❌ No subagent results", flush=True)
            return False

        # Check risk assessment
        risk_assessment = final_state.get("risk_assessment")
        if risk_assessment:
            print(f"✅ Risk assessment completed", flush=True)
            if isinstance(risk_assessment, dict):
                print(f"  Feasibility: {risk_assessment.get('overall_feasibility', 'Unknown')}", flush=True)
                print(f"  Confidence: {risk_assessment.get('confidence_score', 'N/A')}", flush=True)
        else:
            print("❌ No risk assessment", flush=True)
            return False

        # Check final report
        print("\n[6/6] Validating final report...", flush=True)
        final_report = final_state.get("final_report")
        if final_report:
            report = final_report
            report_length = len(report)
            print(f"✅ Final report generated ({report_length:,} characters)", flush=True)

            # Check for key sections
            required_sections = [
                "zusammenfassung",
                "technologie",
                "wirtschaftlich",
                "risiko",
                "empfehlung"
            ]
            found_sections = sum(1 for section in required_sections if section in report.lower())
            print(f"  Sections found: {found_sections}/{len(required_sections)}", flush=True)

            # Check for Oxytec product mentions
            products = ["CWA", "CSA", "CEA"]
            found_products = [p for p in products if p in report]
            if found_products:
                print(f"  Oxytec products mentioned: {', '.join(found_products)}", flush=True)

            # Save report to file
            report_path = Path("/tmp/phase3_validation_report.txt")
            report_path.write_text(report, encoding="utf-8")
            print(f"  Report saved to: {report_path}", flush=True)
        else:
            print("❌ No final report generated", flush=True)
            return False

        # Check for errors
        if final_state.get("errors"):
            print(f"\n⚠️  Errors encountered: {len(final_state['errors'])}", flush=True)
            for error in final_state["errors"][:3]:
                print(f"  - {error}", flush=True)

        # Check for warnings
        if final_state.get("warnings"):
            print(f"\n⚠️  Warnings: {len(final_state['warnings'])}", flush=True)
            for warning in final_state["warnings"][:3]:
                print(f"  - {warning}", flush=True)

        print("\n" + "=" * 80, flush=True)
        print("✅ Phase 3 Validation PASSED", flush=True)
        print("=" * 80, flush=True)

        return True

    except Exception as e:
        print(f"\n❌ Workflow execution failed: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_phase3_validation())
    sys.exit(0 if success else 1)
