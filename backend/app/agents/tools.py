"""Tool definitions and execution for agents."""

from typing import Any, Dict, List
from app.services.rag_service import ProductRAGService
from app.db.session import AsyncSessionLocal
from app.utils.logger import get_logger

logger = get_logger(__name__)


# Tool definitions for Claude API
PRODUCT_DATABASE_TOOL = {
    "name": "search_product_database",
    "description": """Search the Oxytec product database for relevant equipment and components.

Use this tool to find specific products, technical specifications, or compare different solutions.
You can filter by product category.

Categories:
- ntp_reactor: Non-thermal plasma reactors
- uv_lamp: UV lamps and systems
- ozone_generator: Ozone generation equipment
- scrubber: Wet scrubbers and absorption systems
- control_system: PLC and control systems
- sensor: Monitoring sensors and analyzers
- auxiliary: Pumps, fans, and auxiliary equipment
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language query describing the product or specifications needed"
            },
            "category_filter": {
                "type": "string",
                "enum": [
                    "ntp_reactor",
                    "uv_lamp",
                    "ozone_generator",
                    "scrubber",
                    "control_system",
                    "sensor",
                    "auxiliary"
                ],
                "description": "Optional: Filter by product category"
            },
            "top_k": {
                "type": "integer",
                "description": "Number of results to return (default: 5)",
                "default": 5
            }
        },
        "required": ["query"]
    }
}


WEB_SEARCH_TOOL = {
    "name": "search_web",
    "description": """Search the web for technical information about plasma treatment, UV/ozone processes,
industry standards, or competitor information. Prioritizes oxytec.com content.

Use this for:
- Technical documentation not in the product database
- Industry standards and regulations
- Comparison with competitor technologies
- Latest research on VOC treatment methods
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "site_filter": {
                "type": "string",
                "description": "Optional: Limit to specific domain (e.g., 'oxytec.com')"
            }
        },
        "required": ["query"]
    }
}


def get_tools_for_subagent(tool_names: List[str]) -> List[Dict[str, Any]]:
    """
    Get tool definitions for a subagent.

    Args:
        tool_names: List of tool names requested (should be strings, but we handle dicts defensively)

    Returns:
        List of tool definition dicts for Claude API
    """

    available_tools = {
        "product_database": PRODUCT_DATABASE_TOOL,
        "web_search": WEB_SEARCH_TOOL,
    }

    tools = []
    for name in tool_names:
        # Defensive: If planner returns dicts instead of strings, extract the name
        if isinstance(name, dict):
            logger.warning("tool_name_is_dict", tool_def=name)
            # Try to extract name from dict
            name = name.get("name") or name.get("tool") or "unknown"

        # Ensure name is a string
        if not isinstance(name, str):
            logger.error("tool_name_invalid_type", tool_name=name, type=type(name).__name__)
            continue

        if name in available_tools:
            tools.append(available_tools[name])
        elif name != "none":
            logger.warning("unknown_tool_requested", tool_name=name)

    return tools


class ToolExecutor:
    """Executes tool calls from agents."""

    async def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """
        Execute a tool with given input.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Tool input parameters

        Returns:
            Tool execution result
        """

        logger.info("tool_execution_started", tool=tool_name)

        try:
            if tool_name == "search_product_database":
                return await self._search_product_database(tool_input)
            elif tool_name == "search_web":
                return await self._search_web(tool_input)
            else:
                logger.error("unknown_tool", tool_name=tool_name)
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            logger.error("tool_execution_failed", tool=tool_name, error=str(e))
            return {"error": str(e)}

    async def _search_product_database(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute product database search."""

        query = tool_input.get("query")
        category_filter = tool_input.get("category_filter")
        top_k = tool_input.get("top_k", 5)

        # Create a new database session for this tool call
        async with AsyncSessionLocal() as db:
            rag_service = ProductRAGService(db)
            results = await rag_service.search_products(
                query=query,
                top_k=top_k,
                category_filter=category_filter
            )

        return {
            "query": query,
            "results_count": len(results),
            "results": results
        }

    async def _search_web(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute web search."""

        query = tool_input.get("query")
        site_filter = tool_input.get("site_filter")

        # Implement web search
        # This could use Google Custom Search API, Brave Search API, or similar
        # For now, return a placeholder

        logger.info("web_search_executed", query=query, site=site_filter)

        return {
            "query": query,
            "site_filter": site_filter,
            "message": "Web search not yet implemented. Please use the product database tool or manual research.",
            "suggestion": f"Search manually: https://www.google.com/search?q={query}+site:{site_filter or 'oxytec.com'}"
        }
