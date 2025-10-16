"""WRITER agent node - generates final feasibility report."""

from typing import Any
from app.agents.state import GraphState
from app.services.llm_service import LLMService
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def writer_node(state: GraphState) -> dict[str, Any]:
    """
    WRITER node: Generate comprehensive feasibility study report.

    This is the final agent that synthesizes all findings into a
    professional, well-structured feasibility report.

    Args:
        state: Current graph state with all previous results

    Returns:
        Updated state with final_report
    """

    session_id = state["session_id"]
    extracted_facts = state["extracted_facts"]
    subagent_results = state["subagent_results"]
    risk_assessment = state["risk_assessment"]
    user_input = state["user_input"]

    logger.info("writer_started", session_id=session_id)

    try:
        llm_service = LLMService()

        # Format subagent results by priority
        high_priority = [r for r in subagent_results if r.get("priority") == "high"]
        medium_priority = [r for r in subagent_results if r.get("priority") == "medium"]
        low_priority = [r for r in subagent_results if r.get("priority") == "low"]

        def format_results(results: list) -> str:
            return "\n\n".join(
                f"### {result['agent_name'].replace('_', ' ').title()}\n"
                f"**Objective:** {result['objective']}\n\n"
                f"{result['result']}"
                for result in results
            )

        results_text = ""
        if high_priority:
            results_text += "## High Priority Analysis\n\n" + format_results(high_priority)
        if medium_priority:
            results_text += "\n\n## Additional Analysis\n\n" + format_results(medium_priority)
        if low_priority:
            results_text += "\n\n## Supporting Analysis\n\n" + format_results(low_priority)

        # Create report writing prompt
        writer_prompt = f"""You are an expert technical writer creating a professional feasibility study report for Oxytec.

**Customer Information:**
```json
{user_input}
```

**Technical Analysis:**
```json
{extracted_facts}
```

**Detailed Findings:**
{results_text}

**Risk Assessment:**
```json
{risk_assessment}
```

Create a comprehensive feasibility study report with the following structure:

# Executive Summary
- Brief overview of the project
- Key findings (2-3 paragraphs)
- Recommendation (GO / NO-GO / CONDITIONAL)

# 1. Project Overview
- Customer requirements
- Application context
- Current situation

# 2. Technical Analysis
## 2.1 VOC Characterization
- VOC composition and concentrations
- Specific challenges

## 2.2 Proposed Solution
- Recommended Oxytec technology/products
- System configuration
- Key specifications

## 2.3 Performance Expectations
- Expected removal efficiency
- Operating parameters
- Energy consumption

# 3. Engineering Considerations
- Process integration
- Space requirements
- Utilities required
- Installation complexity

# 4. Commercial Aspects
- Cost estimation (CAPEX/OPEX)
- ROI and payback period
- Comparison with alternatives

# 5. Risk Assessment
- Technical risks and mitigation
- Commercial risks and mitigation
- Overall risk evaluation

# 6. Implementation Plan
- Timeline
- Key milestones
- Critical success factors

# 7. Conclusion and Recommendation
- Clear GO / NO-GO / CONDITIONAL recommendation
- Next steps
- Required information (if any)

# 8. Appendices
- Detailed calculations
- Product specifications
- References

**Formatting Requirements:**
- Use professional, technical language
- Include specific numbers and data
- Use markdown formatting
- Be comprehensive but concise
- Support claims with data from the analysis
- German or English as appropriate based on customer language

Generate the complete report now.
"""

        # Execute report generation with longer context model
        final_report = await llm_service.execute_long_form(
            prompt=writer_prompt,
            system_prompt="You are an expert technical writer specializing in feasibility studies for industrial air treatment systems."
        )

        logger.info(
            "writer_completed",
            session_id=session_id,
            report_length=len(final_report)
        )

        return {
            "final_report": final_report
        }

    except Exception as e:
        logger.error(
            "writer_failed",
            session_id=session_id,
            error=str(e)
        )
        return {
            "final_report": f"# Report Generation Failed\n\nError: {str(e)}",
            "errors": [f"Report generation failed: {str(e)}"]
        }
