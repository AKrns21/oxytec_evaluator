"""
Integration tests for PubChem tool functionality.

Tests the PubChem MCP integration for chemical data retrieval:
- Tool definition validation
- Tool executor integration
- Mock data structure verification
- PLANNER tool selection (pubchem_lookup appears in tool arrays)

Note: These tests use mock data since actual MCP server connection is not implemented yet.
"""

import pytest
from app.agents.tools import (
    get_tools_for_subagent,
    ToolExecutor,
    PUBCHEM_LOOKUP_TOOL
)


class TestPubChemToolDefinition:
    """Test PubChem tool definition and schema."""

    def test_pubchem_tool_exists(self):
        """Test that PubChem tool is defined."""
        assert PUBCHEM_LOOKUP_TOOL is not None
        assert PUBCHEM_LOOKUP_TOOL["name"] == "pubchem_lookup"

    def test_pubchem_tool_schema(self):
        """Test PubChem tool has correct schema structure."""
        schema = PUBCHEM_LOOKUP_TOOL["input_schema"]

        assert schema["type"] == "object"
        assert "function" in schema["properties"]
        assert "identifier" in schema["properties"]
        assert "namespace" in schema["properties"]

        # Check function enum values
        function_enum = schema["properties"]["function"]["enum"]
        assert "get_compound_properties" in function_enum
        assert "get_ghs_classification" in function_enum
        assert "get_compound_toxicity" in function_enum
        assert "get_compound_synonyms" in function_enum
        assert "search_by_formula" in function_enum

    def test_pubchem_tool_description(self):
        """Test PubChem tool has comprehensive description."""
        description = PUBCHEM_LOOKUP_TOOL["description"]

        # Check key functionality is documented
        assert "CAS" in description
        assert "LEL/UEL" in description
        assert "toxicity" in description
        assert "GHS" in description
        assert "PubChem" in description


class TestGetToolsForSubagent:
    """Test tool selection including PubChem."""

    def test_get_pubchem_tool(self):
        """Test that pubchem_lookup can be retrieved."""
        tools = get_tools_for_subagent(["pubchem_lookup"])

        assert len(tools) == 1
        assert tools[0]["name"] == "pubchem_lookup"

    def test_get_multiple_tools_with_pubchem(self):
        """Test retrieving multiple tools including PubChem."""
        tools = get_tools_for_subagent([
            "pubchem_lookup",
            "oxytec_knowledge_search",
            "product_database"
        ])

        assert len(tools) == 3
        tool_names = [t["name"] for t in tools]
        assert "pubchem_lookup" in tool_names
        assert "search_oxytec_knowledge" in tool_names
        assert "search_product_database" in tool_names

    def test_pubchem_tool_priority(self):
        """Test that PubChem tool is first when requested first."""
        tools = get_tools_for_subagent([
            "pubchem_lookup",
            "web_search"
        ])

        assert len(tools) == 2
        assert tools[0]["name"] == "pubchem_lookup"
        assert tools[1]["name"] == "search_web"

    def test_unknown_tool_ignored(self):
        """Test that unknown tool names are ignored."""
        tools = get_tools_for_subagent([
            "pubchem_lookup",
            "unknown_tool",
            "web_search"
        ])

        assert len(tools) == 2
        tool_names = [t["name"] for t in tools]
        assert "pubchem_lookup" in tool_names
        assert "search_web" in tool_names


@pytest.mark.asyncio
class TestToolExecutorPubChem:
    """Test PubChem tool execution."""

    async def test_execute_pubchem_get_compound_properties(self):
        """Test executing get_compound_properties."""
        executor = ToolExecutor()

        result = await executor.execute(
            "pubchem_lookup",
            {
                "function": "get_compound_properties",
                "identifier": "100-42-5",
                "namespace": "cas"
            }
        )

        assert "function" in result
        assert result["function"] == "get_compound_properties"
        assert "identifier" in result
        assert "data" in result
        assert "MolecularFormula" in result["data"]
        assert "MolecularWeight" in result["data"]

    async def test_execute_pubchem_get_ghs_classification(self):
        """Test executing get_ghs_classification."""
        executor = ToolExecutor()

        result = await executor.execute(
            "pubchem_lookup",
            {
                "function": "get_ghs_classification",
                "identifier": "styrene",
                "namespace": "name"
            }
        )

        assert "function" in result
        assert result["function"] == "get_ghs_classification"
        assert "data" in result
        assert "LEL" in result["data"]
        assert "UEL" in result["data"]
        assert "GHSHazardStatements" in result["data"]

    async def test_execute_pubchem_get_compound_toxicity(self):
        """Test executing get_compound_toxicity."""
        executor = ToolExecutor()

        result = await executor.execute(
            "pubchem_lookup",
            {
                "function": "get_compound_toxicity",
                "identifier": "benzene",
                "namespace": "name"
            }
        )

        assert "function" in result
        assert result["function"] == "get_compound_toxicity"
        assert "data" in result
        assert "LD50_Oral_Rat" in result["data"] or "LC50_Inhalation_Rat" in result["data"]
        assert "IARC_Classification" in result["data"]

    async def test_execute_pubchem_get_compound_synonyms(self):
        """Test executing get_compound_synonyms."""
        executor = ToolExecutor()

        result = await executor.execute(
            "pubchem_lookup",
            {
                "function": "get_compound_synonyms",
                "identifier": "100-42-5",
                "namespace": "cas"
            }
        )

        assert "function" in result
        assert result["function"] == "get_compound_synonyms"
        assert "data" in result
        assert "Synonyms" in result["data"]
        assert isinstance(result["data"]["Synonyms"], list)

    async def test_execute_pubchem_search_by_formula(self):
        """Test executing search_by_formula."""
        executor = ToolExecutor()

        result = await executor.execute(
            "pubchem_lookup",
            {
                "function": "search_by_formula",
                "identifier": "C8H8"
            }
        )

        assert "function" in result
        assert result["function"] == "search_by_formula"
        assert "data" in result
        assert "Matches" in result["data"]
        assert isinstance(result["data"]["Matches"], list)

    async def test_execute_pubchem_unknown_function(self):
        """Test executing unknown function returns error."""
        executor = ToolExecutor()

        result = await executor.execute(
            "pubchem_lookup",
            {
                "function": "unknown_function",
                "identifier": "test"
            }
        )

        assert "error" in result
        assert "available_functions" in result

    async def test_execute_pubchem_with_default_namespace(self):
        """Test PubChem with default namespace."""
        executor = ToolExecutor()

        result = await executor.execute(
            "pubchem_lookup",
            {
                "function": "get_compound_properties",
                "identifier": "styrene"
                # namespace defaults to "name"
            }
        )

        assert "function" in result
        assert "identifier" in result
        assert "namespace" in result
        assert result["namespace"] == "name"


class TestPubChemMockDataStructure:
    """Test that mock data structure is correct for downstream agents."""

    @pytest.mark.asyncio
    async def test_compound_properties_structure(self):
        """Test compound properties returns expected fields."""
        executor = ToolExecutor()

        result = await executor.execute(
            "pubchem_lookup",
            {
                "function": "get_compound_properties",
                "identifier": "100-42-5",
                "namespace": "cas"
            }
        )

        data = result["data"]
        expected_fields = [
            "MolecularFormula",
            "MolecularWeight",
            "IUPACName",
            "BoilingPoint",
            "MeltingPoint",
            "Density",
            "VaporPressure"
        ]

        for field in expected_fields:
            assert field in data, f"Expected field {field} not found in compound properties"

    @pytest.mark.asyncio
    async def test_ghs_classification_structure(self):
        """Test GHS classification returns LEL/UEL for ATEX assessment."""
        executor = ToolExecutor()

        result = await executor.execute(
            "pubchem_lookup",
            {
                "function": "get_ghs_classification",
                "identifier": "styrene"
            }
        )

        data = result["data"]

        # Critical for ATEX assessment
        assert "LEL" in data
        assert "UEL" in data

        # GHS safety data
        assert "GHSHazardStatements" in data
        assert "GHSPictograms" in data
        assert "SignalWord" in data

    @pytest.mark.asyncio
    async def test_toxicity_structure(self):
        """Test toxicity data returns IARC classification."""
        executor = ToolExecutor()

        result = await executor.execute(
            "pubchem_lookup",
            {
                "function": "get_compound_toxicity",
                "identifier": "benzene"
            }
        )

        data = result["data"]

        # Critical for risk assessment
        assert "IARC_Classification" in data
        assert "ReproductiveToxicity" in data

        # At least one LD50/LC50 value
        has_toxicity_value = (
            "LD50_Oral_Rat" in data or
            "LC50_Inhalation_Rat" in data
        )
        assert has_toxicity_value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
