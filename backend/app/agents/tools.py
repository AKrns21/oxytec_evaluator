"""Tool definitions and execution for agents."""

from typing import Any, Dict, List
from app.services.rag_service import ProductRAGService
from app.services.technology_rag_service import TechnologyRAGService
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


OXYTEC_KNOWLEDGE_TOOL = {
    "name": "search_oxytec_knowledge",
    "description": """Search Oxytec's internal knowledge base for technology capabilities, application examples,
design guidelines, and case studies from the Oxytec catalog.

Use this tool to:
- Find which oxytec technologies (NTP, UV/ozone, scrubbers, hybrids) are suitable for specific pollutants or industries
- Retrieve performance data (removal efficiencies, energy consumption, maintenance requirements)
- Access application examples and case studies for similar situations
- Get design parameters (GHSV, temperature ranges, flow rates) for different technologies
- Check technology limitations and constraints

Available technology types:
- uv_ozone: UV/Ozon systems (CEA, CFA)
- scrubber: Wet scrubbers (CWA, CSA)
- catalyst: Catalytic reactors (KAT)
- heat_recovery: Heat recovery systems (AAH)
- hybrid: Multi-stage combinations

Available pollutant types:
- VOC, formaldehyde, H2S, ammonia, SO2, odor, fett, keime, particulates, teer

Available industries:
- food_processing, wastewater, chemical, textile, printing, agriculture, rendering

Query Strategy:
- Start broad: "UV ozone VOC removal food industry" before "UV ozone 1800 mg/m3 2-ethylhexanol"
- Use natural language: "formaldehyde removal efficiency textile coating"
- Combine pollutants and industries: "ammonia H2S livestock wastewater"
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language search query describing pollutant, industry, or technical parameter"
            },
            "technology_type": {
                "type": "string",
                "enum": ["uv_ozone", "scrubber", "catalyst", "heat_recovery", "hybrid"],
                "description": "Optional: Filter by specific technology type"
            },
            "pollutant_filter": {
                "type": "string",
                "description": "Optional: Filter by pollutant type (e.g., 'VOC', 'formaldehyde', 'H2S')"
            },
            "industry_filter": {
                "type": "string",
                "description": "Optional: Filter by industry (e.g., 'food_processing', 'wastewater')"
            },
            "top_k": {
                "type": "integer",
                "description": "Number of results to return (1-10, default: 5)",
                "default": 5,
                "minimum": 1,
                "maximum": 10
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


PUBCHEM_LOOKUP_TOOL = {
    "name": "pubchem_lookup",
    "description": """Look up authoritative chemical data from PubChem (NIH database). No API key required.

Use this tool for:
- CAS number validation and verification
- Physical properties (boiling point, melting point, vapor pressure, density, molecular weight)
- LEL/UEL explosive limits for ATEX/safety assessment
- Toxicity data (LD50, LC50, carcinogenicity via IARC, reproductive toxicity)
- GHS safety classification (pictograms, H-codes, signal words, P-codes)
- Regulatory status (REACH, FDA listings)
- Chemical synonyms and trade name matching

Available functions:
- get_compound_properties: Physical/chemical properties, identifiers
- get_ghs_classification: GHS hazard data, LEL/UEL, pictograms, H-codes
- get_compound_toxicity: LD50, LC50, carcinogenicity, reproductive toxicity
- get_compound_synonyms: Common names, trade names, IUPAC names
- search_by_formula: Find compounds by molecular formula

Priority: Use pubchem_lookup FIRST for any chemical data before web_search.
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "function": {
                "type": "string",
                "enum": [
                    "get_compound_properties",
                    "get_ghs_classification",
                    "get_compound_toxicity",
                    "get_compound_synonyms",
                    "search_by_formula"
                ],
                "description": "PubChem function to call"
            },
            "identifier": {
                "type": "string",
                "description": "CAS number, compound name, or CID (e.g., '100-42-5' for styrene)"
            },
            "namespace": {
                "type": "string",
                "enum": ["cid", "name", "cas"],
                "description": "Identifier type (default: 'name')",
                "default": "name"
            },
            "properties": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional: Specific properties to retrieve (for get_compound_properties)"
            }
        },
        "required": ["function", "identifier"]
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
        "oxytec_knowledge_search": OXYTEC_KNOWLEDGE_TOOL,
        "web_search": WEB_SEARCH_TOOL,
        "pubchem_lookup": PUBCHEM_LOOKUP_TOOL,
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
            elif tool_name == "search_oxytec_knowledge":
                return await self._search_oxytec_knowledge(tool_input)
            elif tool_name == "search_web":
                return await self._search_web(tool_input)
            elif tool_name == "pubchem_lookup":
                return await self._pubchem_lookup(tool_input)
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

    async def _search_oxytec_knowledge(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute oxytec knowledge base search."""

        query = tool_input.get("query")
        technology_type = tool_input.get("technology_type")
        pollutant_filter = tool_input.get("pollutant_filter")
        industry_filter = tool_input.get("industry_filter")
        top_k = tool_input.get("top_k", 5)

        # Create a new database session for this tool call
        async with AsyncSessionLocal() as db:
            tech_rag_service = TechnologyRAGService(db)
            results = await tech_rag_service.search_knowledge(
                query=query,
                top_k=top_k,
                technology_type=technology_type,
                pollutant_filter=pollutant_filter,
                industry_filter=industry_filter
            )

        # Format results for agent consumption
        formatted_results = []
        for result in results:
            formatted_results.append({
                "title": result["title"],
                "technology_type": result["technology_type"],
                "page_number": result["page_number"],
                "chunk_type": result["chunk_type"],
                "content": result["chunk_text"],
                "pollutants": result["pollutant_types"],
                "industries": result["industries"],
                "products": result["products_mentioned"],
                "relevance_score": round(result["similarity"], 3)
            })

        return {
            "query": query,
            "filters_applied": {
                "technology_type": technology_type,
                "pollutant": pollutant_filter,
                "industry": industry_filter
            },
            "results_count": len(formatted_results),
            "results": formatted_results,
            "message": f"Found {len(formatted_results)} relevant knowledge chunks from Oxytec catalog"
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

    async def _pubchem_lookup(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute PubChem MCP server lookup.

        Note: This is a placeholder implementation. Actual integration requires MCP server connection.
        For testing/development, returns mock data structure.

        In production, this would use the MCP protocol to communicate with the PubChem MCP server:
        https://github.com/modelcontextprotocol/servers/tree/main/src/pubchem
        """

        function = tool_input.get("function")
        identifier = tool_input.get("identifier")
        namespace = tool_input.get("namespace", "name")
        properties = tool_input.get("properties", [])

        logger.info("pubchem_lookup_executed",
                   function=function,
                   identifier=identifier,
                   namespace=namespace)

        # Placeholder implementation - returns mock data
        # TODO: Replace with actual MCP server integration

        if function == "get_compound_properties":
            return {
                "function": function,
                "identifier": identifier,
                "namespace": namespace,
                "message": "PubChem MCP integration not yet implemented. Mock data returned.",
                "data": {
                    "CID": "1234",
                    "MolecularFormula": "C8H8",
                    "MolecularWeight": "104.15 g/mol",
                    "IUPACName": "Example compound",
                    "BoilingPoint": "145°C",
                    "MeltingPoint": "-31°C",
                    "Density": "0.906 g/cm³",
                    "VaporPressure": "6.4 mmHg at 25°C"
                },
                "suggestion": f"Manual lookup: https://pubchem.ncbi.nlm.nih.gov/compound/{identifier}"
            }

        elif function == "get_ghs_classification":
            return {
                "function": function,
                "identifier": identifier,
                "namespace": namespace,
                "message": "PubChem MCP integration not yet implemented. Mock data returned.",
                "data": {
                    "GHSHazardStatements": ["H226: Flammable liquid and vapor", "H304: May be fatal if swallowed"],
                    "GHSPictograms": ["Flame", "Health Hazard"],
                    "SignalWord": "Danger",
                    "LEL": "1.1% (Lower Explosive Limit)",
                    "UEL": "6.1% (Upper Explosive Limit)"
                },
                "suggestion": f"Manual lookup: https://pubchem.ncbi.nlm.nih.gov/compound/{identifier}"
            }

        elif function == "get_compound_toxicity":
            return {
                "function": function,
                "identifier": identifier,
                "namespace": namespace,
                "message": "PubChem MCP integration not yet implemented. Mock data returned.",
                "data": {
                    "LD50_Oral_Rat": "5000 mg/kg",
                    "LC50_Inhalation_Rat": "24000 ppm (4 hours)",
                    "IARC_Classification": "Group 2B - Possibly carcinogenic to humans",
                    "ReproductiveToxicity": "Not classified"
                },
                "suggestion": f"Manual lookup: https://pubchem.ncbi.nlm.nih.gov/compound/{identifier}"
            }

        elif function == "get_compound_synonyms":
            return {
                "function": function,
                "identifier": identifier,
                "namespace": namespace,
                "message": "PubChem MCP integration not yet implemented. Mock data returned.",
                "data": {
                    "Synonyms": [
                        "Example Chemical",
                        "EC 202-123-4",
                        "Trade Name A",
                        "Trade Name B"
                    ],
                    "CASNumber": "100-42-5"
                },
                "suggestion": f"Manual lookup: https://pubchem.ncbi.nlm.nih.gov/compound/{identifier}"
            }

        elif function == "search_by_formula":
            return {
                "function": function,
                "identifier": identifier,
                "message": "PubChem MCP integration not yet implemented. Mock data returned.",
                "data": {
                    "Matches": [
                        {"CID": "1234", "Name": "Example Compound 1"},
                        {"CID": "5678", "Name": "Example Compound 2"}
                    ]
                },
                "suggestion": f"Manual lookup: https://pubchem.ncbi.nlm.nih.gov/"
            }

        else:
            return {
                "error": f"Unknown PubChem function: {function}",
                "available_functions": [
                    "get_compound_properties",
                    "get_ghs_classification",
                    "get_compound_toxicity",
                    "get_compound_synonyms",
                    "search_by_formula"
                ]
            }
