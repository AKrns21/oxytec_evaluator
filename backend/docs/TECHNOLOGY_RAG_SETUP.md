# Technology Knowledge Base RAG Setup

This document describes the implementation of the Oxytec Technology Knowledge Base RAG system, which enables agents to search and retrieve information from the Oxytec product catalog (`docs/scope_oxytec_industry.json`).

## Overview

The Technology RAG system provides semantic search over Oxytec's technology documentation, including:
- Technology capabilities and specifications
- Application examples and case studies
- Removal efficiencies and performance data
- Design parameters (GHSV, flow rates, energy consumption)
- Industry-specific implementations

## Architecture

### Database Schema

Two new tables were added to store technology knowledge:

#### `technology_knowledge`
Stores high-level page data from the catalog:
- `id` (UUID): Primary key
- `page_number` (INTEGER): Catalog page number
- `rubric` (STRING): Section heading
- `title` (STRING): Page title
- `technology_type` (STRING): Technology classification
  - Values: `uv_ozone`, `scrubber`, `catalyst`, `heat_recovery`, `hybrid`, `general`
- `content` (JSONB): Full page data structure
- `pollutant_types` (JSONB ARRAY): Detected pollutants (e.g., `["VOC", "formaldehyde", "H2S"]`)
- `industries` (JSONB ARRAY): Detected industries (e.g., `["food_processing", "textile"]`)
- `products_mentioned` (JSONB ARRAY): Product names (e.g., `["CEA", "CFA", "CWA"]`)
- `created_at`, `updated_at` (TIMESTAMP)

#### `technology_embeddings`
Stores semantic chunks with vector embeddings:
- `id` (INTEGER): Primary key
- `technology_id` (UUID): Foreign key to `technology_knowledge`
- `chunk_type` (STRING): Chunk category
  - Values: `header`, `description`, `application_example`, `technical_data`, `function`, `advantages`, `process_step`, `table_data`
- `chunk_text` (TEXT): Chunk content
- `chunk_metadata` (JSONB): Additional metadata (pollutants, industries, products, etc.)
- `embedding` (VECTOR(1536)): OpenAI embedding vector
- `created_at` (TIMESTAMP)

### Services

#### `TechnologyRAGService` (`app/services/technology_rag_service.py`)

Main service for querying technology knowledge:

```python
async def search_knowledge(
    query: str,
    top_k: int = 5,
    technology_type: Optional[str] = None,
    pollutant_filter: Optional[str] = None,
    industry_filter: Optional[str] = None,
    chunk_type: Optional[str] = None,
) -> List[Dict[str, Any]]
```

Additional methods:
- `get_knowledge_by_page(page_number)`: Get full page data
- `get_technologies_by_pollutant(pollutant)`: Find all technologies for a pollutant
- `get_application_examples(industry, pollutant)`: Retrieve case studies

### Tool Integration

The `search_oxytec_knowledge` tool is now available to subagents via `app/agents/tools.py`:

```python
OXYTEC_KNOWLEDGE_TOOL = {
    "name": "search_oxytec_knowledge",
    "description": "Search Oxytec's internal knowledge base...",
    "input_schema": {
        "properties": {
            "query": str,
            "technology_type": Optional[str],
            "pollutant_filter": Optional[str],
            "industry_filter": Optional[str],
            "top_k": int (default: 5)
        }
    }
}
```

## Setup Instructions

### 1. Create Database Tables

Run the migration script to create the new tables:

```bash
cd backend
python scripts/migrate_add_technology_tables.py
```

This will create:
- `technology_knowledge` table
- `technology_embeddings` table
- Required indexes

To rollback (drop tables):
```bash
python scripts/migrate_add_technology_tables.py --rollback
```

### 2. Ingest Technology Knowledge

Parse the Oxytec catalog JSON and populate the vector store:

```bash
python scripts/ingest_technology_knowledge.py --source docs/scope_oxytec_industry.json --clear
```

Options:
- `--source`: Path to `scope_oxytec_industry.json` (default: `docs/scope_oxytec_industry.json`)
- `--clear`: Clear existing data before ingestion (recommended for first run)

This script will:
1. Parse each page from the JSON
2. Classify technology type based on keywords
3. Extract pollutants, industries, and product names
4. Create semantic chunks using smart chunking strategy
5. Generate embeddings for each chunk (OpenAI `text-embedding-ada-002`)
6. Store chunks with metadata in the database

**Expected output:**
```
📖 Loading technology knowledge from docs/scope_oxytec_industry.json
✅ Loaded 20 pages from catalog

📄 Processing page 229...
  ℹ️  Type: general, Pollutants: ['VOC', 'formaldehyde', 'H2S', 'ammonia'], Industries: []
  📦 Created 8 chunks
  ✅ Page 229 committed

...

🎉 Ingestion completed!
  📚 Pages processed: 20
  📦 Total chunks created: 156
  🔢 Average chunks per page: 7.8
```

### 3. Test the RAG System

Validate that semantic search is working correctly:

```bash
python scripts/test_technology_rag.py --verbose
```

This will run a suite of test queries covering:
- UV/ozone for formaldehyde in textiles
- Scrubbers for ammonia in wastewater
- VOC removal in food processing
- H2S treatment in biogas/slaughterhouse
- Technical specifications retrieval
- Hybrid system queries

**Expected output:**
```
================================================================================
  Testing Oxytec Technology RAG System
================================================================================

[1/6] Test: UV/ozone technology for formaldehyde in textiles
Query: "UV ozone formaldehyde removal textile industry"

  ✅ Found 3 results:

  📄 Page 250: Reduzierung von VOCs und Formaldehyd aus der Abluft der Textilindustrie
     Technology: hybrid
     Chunk Type: description
     Similarity: 0.876
     ...

  ✅ Validation passed

...

================================================================================
  Test Summary
================================================================================
Total queries: 6
Passed: 6 (100.0%)
Failed: 0 (0.0%)

🎉 All tests passed!
```

### 4. Verify Tool Integration

Check that the tool is available to subagents:

```python
from app.agents.tools import get_tools_for_subagent

tools = get_tools_for_subagent(["oxytec_knowledge_search"])
print(tools)  # Should include OXYTEC_KNOWLEDGE_TOOL
```

## Chunking Strategy

The ingestion script uses intelligent chunking to optimize retrieval:

### Chunk Types

1. **Header** (`header`): Rubric + title
   - Always created first for each page
   - Enables high-level technology matching
   - Example: "Abluftreinigung Industrie – UV/Ozon – CEA, CFA"

2. **Description** (`description`): Body text, left/right columns
   - Split into ~500 char segments with overlap
   - Preserves context while maintaining manageable size
   - Most common chunk type

3. **Application Example** (`application_example`): Case studies
   - Each real-world application separately
   - Detected by "anwendung" in title
   - Examples: Klärschlammtrocknung, Biogas, Schlachthof cases

4. **Technical Data** (`technical_data`): Product specifications
   - Tables from JSON formatted as text
   - Flow rates, dimensions, power consumption
   - Searchable by product names (CEA, CFA, etc.)

5. **Function** (`function`): "Funktion", "Einsatz" sections
   - How the technology works
   - Where it's used

6. **Process Steps** (`process_step`): Step-by-step processes
   - Multi-stage treatment sequences
   - Example: Wäscher → UV → Reaktion → KAT

### Metadata Enrichment

Each chunk is enhanced with:
- `pollutants`: Detected pollutant types from keywords
- `industries`: Detected industry sectors
- `products`: Product names mentioned (CEA, CFA, CWA, etc.)
- `technology_type`: Classified technology category
- `page_number`: Source page reference

This metadata enables **pre-filtering** before vector search, improving relevance and speed.

## Query Examples

### Basic Semantic Search
```python
results = await tech_rag.search_knowledge(
    query="formaldehyde removal efficiency",
    top_k=5
)
```

### With Technology Filter
```python
results = await tech_rag.search_knowledge(
    query="VOC removal",
    technology_type="uv_ozone",
    top_k=5
)
```

### With Pollutant + Industry Filter
```python
results = await tech_rag.search_knowledge(
    query="removal efficiency application example",
    pollutant_filter="ammonia",
    industry_filter="food_processing",
    top_k=5
)
```

### Get All Technologies for a Pollutant
```python
techs = await tech_rag.get_technologies_by_pollutant("H2S")
# Returns: [
#   {"technology_type": "scrubber", "title": "CWA...", ...},
#   {"technology_type": "uv_ozone", "title": "CEA...", ...}
# ]
```

### Get Application Examples
```python
examples = await tech_rag.get_application_examples(
    industry="wastewater",
    pollutant="VOC"
)
```

## Agent Usage

Agents can now use the `search_oxytec_knowledge` tool:

```python
# In planner.py - assign tool to subagent
subagent = {
    "task": """
    Subagent: Technology Screening Specialist

    Objective: Determine which oxytec technologies are suitable for the pollutants.

    Questions to answer:
    - Query oxytec knowledge base: Which technologies have been applied to similar pollutants?
    - What are typical removal efficiencies for each technology?
    ...

    Tools needed: oxytec_knowledge_search
    """,
    "relevant_content": {...}
}
```

When the subagent executes, it can call:
```json
{
  "tool": "search_oxytec_knowledge",
  "input": {
    "query": "UV ozone VOC removal efficiency food industry",
    "pollutant_filter": "VOC",
    "industry_filter": "food_processing",
    "top_k": 5
  }
}
```

## Performance Considerations

### Vector Search Performance
- pgvector uses HNSW index for fast approximate nearest neighbor search
- Typical query time: 50-200ms (depending on filters and top_k)
- Metadata filtering happens in SQL before vector comparison (very fast)

### Embedding Generation
- Ingestion: ~156 embeddings × 0.5s = ~78 seconds total
- Query time: 1 embedding × 0.5s = 0.5 seconds per query
- Embeddings are cached in database (no regeneration needed)

### Scaling
Current setup (~20 pages, ~156 chunks) is small. For larger catalogs:
- Add HNSW index: `CREATE INDEX ON technology_embeddings USING hnsw (embedding vector_cosine_ops)`
- Adjust chunking parameters (max_length, overlap)
- Consider batch embedding generation

## Troubleshooting

### No Results Returned
1. Check data was ingested: `SELECT COUNT(*) FROM technology_embeddings;`
2. Verify embeddings exist: `SELECT COUNT(*) FROM technology_embeddings WHERE embedding IS NOT NULL;`
3. Test query embedding generation: Ensure `OPENAI_API_KEY` is set
4. Check filters aren't too restrictive

### Low Similarity Scores
- Similarity < 0.6: Query may be too specific or use different terminology
- Try broader queries: "UV ozone VOC" instead of "UV ozone remove 1800 mg/m3 2-ethylhexanol"
- Check chunking strategy captures the right context

### Missing Expected Results
1. Verify page was ingested: `SELECT * FROM technology_knowledge WHERE page_number = 232;`
2. Check metadata classification: Look at `pollutant_types`, `industries`, `technology_type`
3. Review chunks: `SELECT chunk_text FROM technology_embeddings WHERE technology_id = '...';`
4. Adjust keyword detection in ingestion script if needed

## Next Steps

After completing Phase 1, you can:

1. **Update Agent Prompts** (Phase 2)
   - Add oxytec_knowledge_search tool to PLANNER prompt examples
   - Update SUBAGENT system prompt with query strategy guidance
   - Refine EXTRACTOR, RISK_ASSESSOR, WRITER prompts per `docs/prompt_update_v1.md`

2. **Test with Real Cases** (Phase 3)
   - Run full workflow with non-PCC inquiry
   - Verify agents use the tool effectively
   - Check that retrieved knowledge appears in final report

3. **Monitor & Optimize**
   - Track which queries return good results
   - Identify gaps in knowledge base coverage
   - Refine chunking strategy based on usage patterns

## Files Created

```
backend/
├── app/
│   ├── models/
│   │   └── database.py                  # Added TechnologyKnowledge, TechnologyEmbedding
│   ├── services/
│   │   └── technology_rag_service.py    # New: RAG service for technology KB
│   └── agents/
│       └── tools.py                     # Added OXYTEC_KNOWLEDGE_TOOL
├── scripts/
│   ├── migrate_add_technology_tables.py # Migration script
│   ├── ingest_technology_knowledge.py   # Ingestion script
│   └── test_technology_rag.py           # Test suite
└── docs/
    └── TECHNOLOGY_RAG_SETUP.md          # This file
```

## References

- Original requirements: `docs/prompt_update_v1.md`
- Source data: `docs/scope_oxytec_industry.json`
- Product RAG example: `app/services/rag_service.py`
- Embedding service: `app/services/embedding_service.py`
