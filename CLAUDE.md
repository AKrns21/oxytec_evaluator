# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Oxytec Multi-Agent Feasibility Platform** - an automated system that analyzes customer inquiries for VOC (Volatile Organic Compound) treatment systems and generates comprehensive feasibility studies. The platform uses a dynamic multi-agent architecture powered by Claude and LangGraph.

**Key Innovation**: Unlike traditional sequential workflows, the PLANNER agent autonomously decides how many specialized subagents to create (3-8) based on inquiry complexity, and these subagents execute in parallel for dramatic speed improvements.

## Development Standards

### Python Command Requirements

**CRITICAL**: Always use `python3` (not `python`) and activate the virtual environment for all backend operations:

```bash
# ALWAYS do this first
cd backend
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Then use python3 for all commands
python3 -m pytest tests/ -v        # ✅ CORRECT
python -m pytest tests/ -v         # ❌ WRONG - may use system Python

python3 manage.py migrate          # ✅ CORRECT
python manage.py migrate           # ❌ WRONG

python3 scripts/ingest_data.py     # ✅ CORRECT
python scripts/ingest_data.py      # ❌ WRONG
```

**Why**: `python` may point to Python 2.x or system Python 3.x, while `python3` ensures Python 3.x. The virtual environment ensures correct dependencies.

## Development Commands

### Environment Setup

```bash
# Backend setup
cd backend
python3.11 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install uv && uv pip install -r pyproject.toml

# Configure environment
cp .env.example .env
# Edit .env with:
#   - ANTHROPIC_API_KEY (for Claude models)
#   - OPENAI_API_KEY (for GPT models and embeddings)
#   - DATABASE_URL (Supabase connection string)
# Optional: Add LANGCHAIN_API_KEY for LangSmith tracing (see backend/docs/LANGSMITH_SETUP.md)

# Note: Database is hosted on Supabase - no local setup needed
# Product and technology data already loaded in Supabase

# Frontend setup
cd frontend
npm install
# Frontend will connect to backend at http://localhost:8000
```

### Running the Application

```bash
# Backend development server (auto-reload)
cd backend
uvicorn app.main:app --reload --port 8000

# Frontend development server
cd frontend
npm run dev

# Run everything with Docker
docker-compose up

# API documentation: http://localhost:8000/docs
# Frontend application: http://localhost:3000
```

### Testing

**IMPORTANT**: Always activate the virtual environment and use `python3` (not `python`) for all commands:

```bash
cd backend
source .venv/bin/activate           # REQUIRED: Activate virtual environment first
                                    # Windows: .venv\Scripts\activate

# Run all tests
python3 -m pytest tests/ -v

# Run tests by category
python3 -m pytest tests/unit/ -v                    # Unit tests only
python3 -m pytest tests/integration/ -v             # Integration tests only
python3 -m pytest tests/e2e/ -v                     # End-to-end tests only

# Run extractor evaluation
python3 -m pytest tests/evaluation/extractor/layer2_llm_interpretation/ -v
python3 tests/evaluation/extractor/test_single_file.py <filename.xlsx>

# Run tests matching pattern
python3 -m pytest tests/ -k "test_planner" -v

# Run with coverage
python3 -m pytest tests/ --cov=app --cov-report=html

# Run specific test file
python3 -m pytest tests/unit/test_llm_service.py -v
```

See `backend/tests/README.md` for complete testing documentation.

### Code Quality

```bash
cd backend
black app/              # Format code
ruff check app/         # Lint
mypy app/              # Type checking
```

### Database Operations

The application uses **Supabase** as the database backend with pgvector for semantic search.

**Schema includes:**
- `sessions`, `documents`, `session_logs`, `agent_outputs` (session management)
- `products`, `product_embeddings` (product catalog RAG)
- `technology_knowledge`, `technology_embeddings` (technology knowledge RAG)

All schema changes should be made directly in Supabase or via the SQLAlchemy models in `app/models/database.py`. The `init_db()` function in `app/db/session.py` creates tables automatically on startup if they don't exist.

## Architecture Overview

### Multi-Agent Workflow

The system implements a **5-stage agent pipeline** with dynamic parallel execution:

```
Upload → EXTRACTOR → PLANNER → SUBAGENTS (parallel) → RISK ASSESSOR → WRITER → Report
         (10s)       (5s)       (15-30s)              (5-10s)          (10-15s)
```

1. **EXTRACTOR** (`app/agents/nodes/extractor.py`): Extracts structured facts from uploaded documents (PDF, Word, Excel) using **OpenAI GPT-5** (temperature: 0.2) with JSON mode for reliable structured output
2. **PLANNER** (`app/agents/nodes/planner.py`): Analyzes extracted facts and dynamically creates 3-8 specialized subagent definitions using **OpenAI GPT-mini** (temperature: 0.9) with JSON mode for creative planning
3. **SUBAGENTS** (`app/agents/nodes/subagent.py`): Execute in parallel via `asyncio.gather()`, each investigating specific aspects (VOC analysis, product selection, energy calculations, etc.) using **OpenAI GPT-nano** (temperature: 0.4) for efficient text analysis
4. **RISK ASSESSOR** (`app/agents/nodes/risk_assessor.py`): Synthesizes all findings and evaluates technical/commercial risks using **OpenAI GPT-5** (temperature: 0.4) with JSON mode for structured risk data
5. **WRITER** (`app/agents/nodes/writer.py`): Generates final comprehensive feasibility report in German using **Claude Sonnet 4.5** (temperature: 0.4) for high-quality long-form writing

**Model Selection Strategy:**
- **OpenAI GPT-5**: Used for EXTRACTOR (precise data extraction) and RISK ASSESSOR (critical analysis) - most capable model for accuracy-critical tasks
- **OpenAI GPT-5-mini**: Used for PLANNER to encourage creative subagent planning strategies
- **OpenAI GPT-5-nano**: Used for SUBAGENTS - cost-efficient model for parallel analysis tasks
- **Claude Sonnet 4.5**: Used for WRITER - superior German language generation and report synthesis
- **GPT-5 Note**: GPT-5 models don't support temperature parameter. Instead, temperature values are automatically mapped to `reasoning_effort`:
  - Temperature 0.0-0.3 → reasoning_effort: "minimal"
  - Temperature 0.4-0.7 → reasoning_effort: "low"
  - Temperature 0.8-1.0 → reasoning_effort: "medium"

### LangGraph State Management

The workflow state (`app/agents/state.py`) uses TypedDict with annotated reducers:
- `subagent_results`: Uses `add` reducer to accumulate results from parallel agents
- `errors` and `warnings`: Also use `add` reducer for aggregation
- All state mutations are immutable - nodes return dicts that update state

**Note**: The graph uses PostgreSQL checkpointing for state persistence. The import path for `PostgresSaver` may vary:
```python
try:
    from langgraph.checkpoint.postgres import PostgresSaver
except ImportError:
    from langgraph_checkpoint.postgres import PostgresSaver
```
If checkpointing fails, the graph will compile without it and log a warning.

### Parallel Execution Pattern

Key implementation in `app/agents/nodes/subagent.py`:

```python
# Create tasks for all subagents
tasks = [execute_single_subagent(subagent_def, state, instance_name)
         for subagent_def in subagent_definitions]

# Execute all in parallel
results = await asyncio.gather(*tasks, return_exceptions=True)
```

This is the core innovation - subagents don't wait for each other, dramatically reducing total execution time.

### Tool System

Subagents can use tools defined in `app/agents/tools.py`:
- **Product Database Tool**: Semantic search over Oxytec catalog using pgvector cosine similarity
- **Web Search Tool**: Placeholder for external search (needs API integration)

Tools are provided to Claude via the Anthropic SDK's tool calling API. The `ToolExecutor` class handles tool invocation during agent execution.

### RAG Implementation

**Product RAG** (`app/services/rag_service.py`):
1. User query → OpenAI embedding (1536 dimensions)
2. Supabase pgvector cosine similarity search: `embedding <=> query_embedding`
3. Returns top-k products with similarity scores
4. Chunks are pre-generated to ensure relevant context

**Technology Knowledge RAG** (`app/services/technology_rag_service.py`):
1. Similar embedding-based search over Oxytec technology catalog
2. Supports filtering by technology type, pollutant, industry, and chunk type
3. Currently contains 21 technology knowledge entries with 95 embeddings

Product data is chunked into:
- Header (name + category)
- Description chunks (max 500 chars)
- Technical specifications

## Database Schema (Supabase)

All tables hosted on **Supabase PostgreSQL with pgvector extension**.

Key tables in `app/models/database.py`:

**Session Management:**
- **sessions**: Main session tracking (status: pending/processing/completed/failed)
- **session_logs**: Detailed logs for debugging each agent execution
- **agent_outputs**: Stores output from each agent node with token usage and duration
- **documents**: Uploaded files with extracted content cached in JSONB

**RAG Tables:**
- **products**: Oxytec product catalog
- **product_embeddings**: Vector embeddings for product search (pgvector)
- **technology_knowledge**: Oxytec technology catalog knowledge base
- **technology_embeddings**: Vector embeddings for technology search (pgvector)

All use async SQLAlchemy 2.0 with proper type hints via `Mapped[]`.
Database connection is managed via `app/db/session.py` with connection pooling (20 connections).

## API Endpoints

Routes in `app/api/routes/`:

- `POST /api/sessions/create`: Upload files, create session, start agent workflow in background
- `GET /api/sessions/{id}`: Get session status and final results
- `GET /api/sessions/{id}/stream`: SSE endpoint for real-time progress updates
- `GET /api/sessions/{id}/debug`: Detailed logs and agent outputs for debugging

Background task execution uses FastAPI's `BackgroundTasks` to avoid blocking the upload response.

## Service Layer

- **LLMService** (`app/services/llm_service.py`): Wraps Anthropic API
  - `execute_structured()`: For JSON responses with parsing
  - `execute_long_form()`: For report generation (higher token limit)
  - `execute_with_tools()`: For tool-calling agents with iteration loop

- **DocumentService** (`app/services/document_service.py`): Extracts text from PDF/DOCX/Excel/CSV

- **EmbeddingService** (`app/services/embedding_service.py`): OpenAI embedding generation

- **ProductRAGService** (`app/services/rag_service.py`): Semantic product search

## Working with Agents

### Adding a New Agent Node

1. Create file in `app/agents/nodes/` (e.g., `compliance_checker.py`)
2. Define async function with signature: `async def node_name(state: GraphState) -> dict[str, Any]`
3. Return dict with state updates (partial state, not full state)
4. Add node to workflow in `app/agents/graph.py`:
   ```python
   workflow.add_node("compliance_checker", compliance_checker_node)
   workflow.add_edge("previous_node", "compliance_checker")
   ```

### Modifying Agent Prompts

Agent prompts are inline in node files (not separate template files). To modify behavior:
- Find the node file (e.g., `app/agents/nodes/planner.py`)
- Locate the prompt string (usually in a multi-line f-string)
- Edit prompt directly - changes take effect on next reload

### Adding Tools

1. Define tool schema in `app/agents/tools.py` following Anthropic's format
2. Add tool name to `get_tools_for_subagent()` mapping
3. Implement execution in `ToolExecutor.execute()`
4. Tool will be available to subagents by name

## Configuration

Environment variables in `app/config.py` (loaded from `.env`):

Critical settings:
- `ANTHROPIC_API_KEY`: Required for Writer agent (German report generation)
- `OPENAI_API_KEY`: Required for Extractor, Planner, Subagents, Risk Assessor, and embeddings/RAG
- `DATABASE_URL`: Supabase PostgreSQL connection string (format: `postgresql+asyncpg://user:pass@host.supabase.co:5432/postgres`)

**Agent-specific model configuration:**
- `EXTRACTOR_MODEL`: Model for data extraction (default: gpt-5)
- `EXTRACTOR_TEMPERATURE`: Temperature for extraction (default: 0.2)
- `PLANNER_MODEL`: Model for subagent planning (default: gpt-mini)
- `PLANNER_TEMPERATURE`: Temperature for planning (default: 0.9 - encourages creative strategies)
- `SUBAGENT_MODEL`: Model for parallel analysis (default: gpt-nano)
- `SUBAGENT_TEMPERATURE`: Temperature for subagents (default: 0.4)
- `RISK_ASSESSOR_MODEL`: Model for risk evaluation (default: gpt-5)
- `RISK_ASSESSOR_TEMPERATURE`: Temperature for risk assessment (default: 0.4)
- `WRITER_MODEL`: Model for report writing (default: claude-sonnet-4-5)
- `WRITER_TEMPERATURE`: Temperature for writing (default: 0.4)

## Logging and Debugging

Structured logging with structlog (`app/utils/logger.py`):
```python
logger.info("event_name", key1=value1, key2=value2)
```

For debugging agent execution:
1. Check session logs: `GET /api/sessions/{id}/debug`
2. Examine agent outputs in database: `agent_outputs` table
3. Review LangGraph checkpoints (stored in PostgreSQL if enabled)
4. **Use LangSmith tracing**: Enable comprehensive tracing with LangSmith for visual debugging, timing analysis, and token tracking. See `backend/docs/LANGSMITH_SETUP.md` for setup instructions.

## Common Patterns

### Adding a New Endpoint

1. Create route file in `app/api/routes/`
2. Define router: `router = APIRouter()`
3. Add route with `@router.get()` or `@router.post()`
4. Include router in `app/main.py`:
   ```python
   app.include_router(new_router, prefix="/api", tags=["tag"])
   ```

### Database Queries

Use async context manager pattern:
```python
async with AsyncSessionLocal() as db:
    stmt = select(Model).where(Model.field == value)
    result = await db.execute(stmt)
    records = result.scalars().all()
```

### Calling LLM Service

```python
llm_service = LLMService()

# For structured output
result = await llm_service.execute_structured(
    prompt="...",
    response_format="json"  # or "text"
)

# For tool-calling agents
result = await llm_service.execute_with_tools(
    prompt="...",
    tools=[tool_definition],
    max_iterations=5
)
```

## Frontend Architecture

The application includes a fully functional Next.js 14 frontend with TypeScript.

### Technology Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: TailwindCSS + shadcn/ui components
- **State Management**: React hooks (useState, useEffect)
- **API Integration**: Fetch API with SSE (Server-Sent Events) for real-time updates

### Key Components

Located in `frontend/components/`:

- **FileUpload.tsx**: Drag-and-drop file upload with multi-file support
- **ResultsViewer.tsx**: Display final feasibility reports with formatted sections
- **AgentVisualization.tsx**: Visual representation of agent execution flow
- **UI Components**: Button, Card, Input, Label, Progress, Tabs (shadcn/ui)

### Custom Hooks

- **useSSE.ts** (`frontend/hooks/`): Server-Sent Events hook for streaming session updates
  - Connects to `/api/sessions/{id}/stream`
  - Handles real-time agent progress updates
  - Auto-reconnection on connection loss

### Pages

- **/** (`app/page.tsx`): Main upload page with file selection and session creation
- **/session/[id]** (`app/session/[id]/page.tsx`): Session status and results viewer with live updates

### Running Frontend

```bash
cd frontend
npm install
npm run dev  # Starts on http://localhost:3000

# Or with Docker
docker-compose up frontend
```

### Frontend Environment Variables

- `NEXT_PUBLIC_API_URL`: Backend API URL (default: http://localhost:8000)

## Known Issues and Limitations

- Web search tool is placeholder - needs external API integration
- No authentication/authorization system
- Single-tenant design (no user management)
- SSE implementation uses polling (consider Redis pub/sub for production scale)
- LangGraph checkpoint import may vary between versions (see import fallback in `app/agents/graph.py`)

## Performance Considerations

- Typical processing time: 40-70 seconds per feasibility study
- Parallel subagent execution is CPU-bound on LLM API calls, not I/O
- Supabase connection pool sized for concurrent agent operations (20 connections)
- Document extraction is cached in `documents.extracted_content` JSONB field
- Consider using Haiku model for simple extraction tasks to reduce costs
- RAG searches use pgvector cosine similarity for fast semantic retrieval

## Testing Philosophy

When writing tests:
- Mock LLM responses using fixtures for deterministic testing
- Test agent nodes independently before integration tests
- Use `pytest-asyncio` for async test functions
- Database tests should use transaction rollback for isolation
- Test the full graph with `graph.ainvoke()` for integration tests

## File Organization

### Code Organization

- Agent logic: `app/agents/` - All LangGraph workflow code
- API layer: `app/api/routes/` - FastAPI endpoints only, no business logic
- Services: `app/services/` - Reusable business logic (LLM, RAG, documents)
- Models: `app/models/` - Database models (database.py) and API schemas (schemas.py)
- DB: `app/db/` - Session management and migrations
- Utils: `app/utils/` - Logger, helpers, utilities

Keep API routes thin - delegate to services. Agents should call services, not database directly.

### Documentation Organization

**Project-level documentation** (`docs/`):
- `docs/architecture/` - System architecture, design decisions, UI/UX flows
- `docs/development/` - Code reviews, prompt engineering updates, dev guides
- `docs/evaluation/` - Testing strategies, evaluation frameworks, quality analysis
- `docs/examples/` - Example outputs, sample data, screenshots, PDFs

**Backend-specific documentation** (`backend/docs/`):
- `backend/docs/setup/` - Setup guides (LangSmith, Supabase, RAG systems)
- `backend/docs/implementation/` - Implementation summaries, change logs, fixes
- `backend/docs/api/` - API specifications and integration guides
- `backend/docs/reports/` - Generated feasibility reports (PDF outputs)

**Test documentation** (`backend/tests/`):
- `backend/tests/unit/` - Unit tests for services, utilities, models
- `backend/tests/integration/` - Agent node and multi-component integration tests
- `backend/tests/e2e/` - End-to-end workflow tests
- `backend/tests/evaluation/` - Quality evaluation frameworks (extractor, planner, etc.)

See README.md files in each directory for detailed organization guidelines.

### File Placement Guidelines

**When creating new documentation:**

1. **Architecture/Design docs** → `docs/architecture/`
   - System design, workflow diagrams, technology decisions

2. **Code reviews/Prompt updates** → `docs/development/`
   - Code review reports, prompt engineering changes, refactoring notes

3. **Evaluation/Testing strategies** → `docs/evaluation/`
   - Agent quality frameworks, test strategies, evaluation results

4. **Examples/Sample data** → `docs/examples/`
   - Example agent outputs (JSON), sample PDFs, screenshots, test data

5. **Setup/Configuration guides** → `backend/docs/setup/`
   - Installation instructions, environment configuration, service setup

6. **Implementation notes** → `backend/docs/implementation/`
   - Feature implementation summaries, bug fix documentation, change logs

7. **Generated reports** → `backend/docs/reports/`
   - PDF feasibility reports, output templates

8. **Test files** → `backend/tests/<category>/`
   - Unit tests → `tests/unit/`
   - Integration tests → `tests/integration/`
   - E2E tests → `tests/e2e/`
   - Evaluation frameworks → `tests/evaluation/<agent_name>/`

**Naming conventions:**
- Date-stamped: `TOPIC_YYYY-MM-DD.md` (e.g., `CODE_REVIEW_2025-10-21.md`)
- Versioned: `TOPIC_vN.md` (e.g., `EVALUATION_STRATEGY_v2.md`)
- General: `TOPIC.md` (e.g., `ARCHITECTURE.md`)
- Test files: `test_<feature>.py` (e.g., `test_extractor.py`)
