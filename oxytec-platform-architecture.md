# Oxytec Multi-Agent Feasibility Platform - Technical Architecture

## Executive Summary

Moderne Web-Applikation zur Durchführung automatisierter Machbarkeitsstudien mit dynamischem Multi-Agent-System. Der Planner entscheidet autonom über die Anzahl und Aufgaben der Subagenten, die parallel arbeiten.

---

## 1. Tech Stack Overview

### Backend
- **Framework**: FastAPI (Python 3.11+)
  - Async/Await native support für parallele Agent-Ausführung
  - Automatische OpenAPI-Dokumentation
  - Exzellente Performance
  - WebSocket-Support für Real-time Updates

- **Agent Orchestrierung**: LangGraph
  - Perfekt für dynamische Agent-Workflows
  - Native Unterstützung für parallele Nodes
  - State Management eingebaut
  - Checkpointing für Debugging

- **LLM Integration**: Anthropic Python SDK
  - Direkte Claude API-Integration
  - Streaming-Support
  - Tool-Calling für Subagenten

- **Task Queue**: asyncio + aiohttp
  - Keine zusätzliche Infrastruktur nötig (im Gegensatz zu Celery)
  - Python-native
  - Perfekt für LLM-API-Calls

### Frontend
- **Framework**: Next.js 14 (App Router)
  - Server-Side Rendering
  - Moderne React-Patterns
  - Built-in API-Routes als Fallback

- **UI Components**: shadcn/ui + Tailwind CSS
  - Moderne, accessible Components
  - Copy-Paste statt npm-Dependencies
  - Flexibel anpassbar

- **File Upload**: react-dropzone
  - Drag & Drop
  - Multi-File Support
  - Validation

- **Real-time Updates**: Server-Sent Events (SSE)
  - Einfacher als WebSockets
  - Unidirektional (passt perfekt)
  - Native Browser-Support

### Database & Storage
- **Primary DB**: PostgreSQL 15+
  - JSONB für flexible Session-Speicherung
  - Robust und bewährt
  - Excellente Python-Integration

- **Vector Store**: pgvector Extension
  - Native PostgreSQL Integration
  - RAG für Produktdatenbank
  - Keine separate Vektordatenbank nötig

- **ORM**: SQLAlchemy 2.0 (async)
  - Type-safe
  - Async Support
  - Migration-Management mit Alembic

- **File Storage**: Local FS (Entwicklung) / S3-compatible (Produktion)
  - MinIO für self-hosted Option
  - Einfacher Wechsel später möglich

### Additional Services
- **Embedding Model**: 
  - OpenAI text-embedding-3-small (schnell, günstig)
  - Alternativ: sentence-transformers (self-hosted)

- **Document Processing**:
  - PyMuPDF für PDFs
  - python-docx für Word
  - pandas für Excel/CSV

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                    │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  Upload UI │  │  Form Input  │  │  Results Viewer  │   │
│  └────────────┘  └──────────────┘  └──────────────────┘   │
│         │                │                    ▲             │
│         └────────────────┴────────────────────┘             │
│                          │                                   │
│                    SSE/HTTP API                             │
└──────────────────────────┼──────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────┐
│                    FastAPI Backend                          │
│                          │                                   │
│  ┌───────────────────────┴────────────────────────┐        │
│  │         API Endpoints Layer                     │        │
│  │  - /upload  - /session/{id}  - /stream/{id}   │        │
│  └───────────────────────┬────────────────────────┘        │
│                          │                                   │
│  ┌───────────────────────┴────────────────────────┐        │
│  │         LangGraph Agent Orchestrator            │        │
│  │                                                  │        │
│  │  ┌──────────┐                                   │        │
│  │  │EXTRACTOR │                                   │        │
│  │  └────┬─────┘                                   │        │
│  │       │                                          │        │
│  │  ┌────▼─────┐                                   │        │
│  │  │ PLANNER  │◄──────┐                          │        │
│  │  └────┬─────┘       │                          │        │
│  │       │         Dynamic                         │        │
│  │       │         Agent                           │        │
│  │  ┌────▼──────┐  Creation                       │        │
│  │  │ SUBAGENT  │      │                          │        │
│  │  │  Pool     │      │                          │        │
│  │  │ (Parallel)│──────┘                          │        │
│  │  └────┬──────┘                                  │        │
│  │       │                                          │        │
│  │  ┌────▼──────────┐                             │        │
│  │  │RISK ASSESSOR  │                             │        │
│  │  └────┬──────────┘                             │        │
│  │       │                                          │        │
│  │  ┌────▼─────┐                                   │        │
│  │  │  WRITER  │                                   │        │
│  │  └──────────┘                                   │        │
│  └─────────────────────────────────────────────────┘        │
│                          │                                   │
│  ┌───────────────────────┴────────────────────────┐        │
│  │         Tool Layer                              │        │
│  │  - Web Search Tool                              │        │
│  │  - Product DB RAG Tool                          │        │
│  │  - Document Extraction Tool                     │        │
│  └─────────────────────────────────────────────────┘        │
└──────────────────────────┼──────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────┐
│                    Data Layer                               │
│                          │                                   │
│  ┌──────────────┐  ┌────▼───────┐  ┌──────────────────┐   │
│  │  PostgreSQL  │  │  pgvector  │  │  File Storage    │   │
│  │              │  │            │  │  (S3-compatible) │   │
│  │  - Sessions  │  │  - Product │  │                  │   │
│  │  - Logs      │  │    Vectors │  │  - Uploads       │   │
│  │  - Results   │  │  - Docs    │  │  - Reports       │   │
│  └──────────────┘  └────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Component Design

### 3.1 Backend Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app initialization
│   ├── config.py                  # Settings (Pydantic)
│   ├── api/
│   │   ├── routes/
│   │   │   ├── upload.py          # File upload endpoint
│   │   │   ├── session.py         # Session management
│   │   │   └── stream.py          # SSE endpoint
│   │   └── dependencies.py        # FastAPI dependencies
│   ├── agents/
│   │   ├── graph.py               # LangGraph definition
│   │   ├── nodes/
│   │   │   ├── extractor.py       # EXTRACTOR node
│   │   │   ├── planner.py         # PLANNER node
│   │   │   ├── subagent.py        # SUBAGENT template
│   │   │   ├── risk_assessor.py   # RISK ASSESSOR node
│   │   │   └── writer.py          # WRITER node
│   │   ├── state.py               # Graph state definition
│   │   └── tools.py               # Agent tools
│   ├── services/
│   │   ├── llm_service.py         # Claude API wrapper
│   │   ├── embedding_service.py   # Embedding generation
│   │   ├── document_service.py    # Document parsing
│   │   └── rag_service.py         # Product DB RAG
│   ├── models/
│   │   ├── database.py            # SQLAlchemy models
│   │   └── schemas.py             # Pydantic schemas
│   ├── db/
│   │   ├── session.py             # DB session management
│   │   └── migrations/            # Alembic migrations
│   └── utils/
│       ├── logger.py              # Structured logging
│       └── helpers.py             # Utility functions
├── tests/
├── pyproject.toml                 # Poetry/uv dependencies
└── README.md
```

### 3.2 Frontend Structure

```
frontend/
├── app/
│   ├── layout.tsx                 # Root layout
│   ├── page.tsx                   # Home page
│   ├── upload/
│   │   └── page.tsx               # Upload page
│   ├── session/
│   │   └── [id]/
│   │       ├── page.tsx           # Session detail view
│   │       └── loading.tsx        # Loading state
│   └── api/                       # Optional API routes
├── components/
│   ├── ui/                        # shadcn components
│   ├── FileUpload.tsx             # Drag & drop upload
│   ├── SessionStatus.tsx          # Real-time status
│   ├── AgentVisualization.tsx     # Agent flow diagram
│   ├── ResultsViewer.tsx          # Final report display
│   └── DebugPanel.tsx             # Dev mode debugging
├── lib/
│   ├── api-client.ts              # Backend API wrapper
│   ├── sse-client.ts              # SSE connection handler
│   └── utils.ts                   # Utility functions
├── hooks/
│   ├── useSession.ts              # Session state hook
│   └── useSSE.ts                  # SSE hook
├── public/
└── package.json
```

---

## 4. Database Schema

### 4.1 Core Tables

```sql
-- Sessions table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    status VARCHAR(50) NOT NULL,  -- 'pending', 'processing', 'completed', 'failed'
    user_metadata JSONB,           -- User inputs, company name, etc.
    result JSONB,                  -- Final report
    error TEXT
);

-- Session logs table (für Debugging)
CREATE TABLE session_logs (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    agent_type VARCHAR(50) NOT NULL,  -- 'extractor', 'planner', 'subagent', etc.
    agent_instance VARCHAR(100),      -- For parallel subagents: 'subagent_voc_analysis'
    log_level VARCHAR(20),            -- 'debug', 'info', 'warning', 'error'
    message TEXT,
    data JSONB                        -- Structured log data
);

-- Uploaded documents
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    mime_type VARCHAR(100),
    size_bytes INTEGER,
    uploaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    extracted_content JSONB         -- Cached extraction results
);

-- Agent outputs (für Debugging)
CREATE TABLE agent_outputs (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    agent_type VARCHAR(50) NOT NULL,
    agent_instance VARCHAR(100),
    output_type VARCHAR(50),        -- 'json', 'text', 'plan'
    content JSONB NOT NULL,
    tokens_used INTEGER,
    duration_ms INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Product database
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),          -- 'ntp_reactor', 'uv_lamp', 'scrubber', etc.
    technical_specs JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Product embeddings (für RAG)
CREATE TABLE product_embeddings (
    id BIGSERIAL PRIMARY KEY,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    chunk_metadata JSONB,
    embedding vector(1536),         -- OpenAI embedding dimension
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create index for vector similarity search
CREATE INDEX idx_product_embeddings_vector ON product_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Indexes
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_created_at ON sessions(created_at DESC);
CREATE INDEX idx_session_logs_session_id ON session_logs(session_id);
CREATE INDEX idx_documents_session_id ON documents(session_id);
CREATE INDEX idx_agent_outputs_session_id ON agent_outputs(session_id);
```

---

## 5. LangGraph Implementation

### 5.1 Graph State Definition

```python
from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
from operator import add

class GraphState(TypedDict):
    """State shared across all agents"""
    
    # Input data
    session_id: str
    documents: List[Dict[str, Any]]
    user_input: Dict[str, Any]
    
    # Extracted facts
    extracted_facts: Dict[str, Any]
    
    # Planner output
    planner_plan: Dict[str, Any]  # Contains subagent definitions
    
    # Subagent results (accumulated with add reducer)
    subagent_results: Annotated[List[Dict[str, Any]], add]
    
    # Risk assessment
    risk_assessment: Dict[str, Any]
    
    # Final report
    final_report: str
    
    # Metadata
    errors: Annotated[List[str], add]
    warnings: Annotated[List[str], add]
```

### 5.2 Dynamic Parallel Subagent Execution

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
import asyncio

def create_agent_graph():
    """Creates the dynamic agent graph"""
    
    # Initialize graph with checkpointing for debugging
    workflow = StateGraph(GraphState)
    
    # Add static nodes
    workflow.add_node("extractor", extractor_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("risk_assessor", risk_assessor_node)
    workflow.add_node("writer", writer_node)
    
    # Dynamic parallel subagent execution
    workflow.add_node("execute_subagents", execute_subagents_parallel)
    
    # Define edges
    workflow.set_entry_point("extractor")
    workflow.add_edge("extractor", "planner")
    workflow.add_edge("planner", "execute_subagents")
    workflow.add_edge("execute_subagents", "risk_assessor")
    workflow.add_edge("risk_assessor", "writer")
    workflow.add_edge("writer", END)
    
    # Compile with PostgreSQL checkpointing
    checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)
    app = workflow.compile(checkpointer=checkpointer)
    
    return app


async def execute_subagents_parallel(state: GraphState) -> GraphState:
    """
    Executes subagents in parallel based on planner's plan.
    This is the key innovation over Flowise.
    """
    
    plan = state["planner_plan"]
    subagent_definitions = plan.get("subagents", [])
    
    # Create tasks for parallel execution
    tasks = []
    for idx, subagent_def in enumerate(subagent_definitions):
        task = execute_single_subagent(
            subagent_def=subagent_def,
            state=state,
            instance_name=f"subagent_{idx}_{subagent_def['name']}"
        )
        tasks.append(task)
    
    # Execute all subagents in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect results and errors
    successful_results = []
    errors = []
    
    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            error_msg = f"Subagent {idx} failed: {str(result)}"
            errors.append(error_msg)
            log_agent_error(state["session_id"], f"subagent_{idx}", error_msg)
        else:
            successful_results.append(result)
            log_agent_output(state["session_id"], f"subagent_{idx}", result)
    
    return {
        "subagent_results": successful_results,
        "errors": errors
    }


async def execute_single_subagent(
    subagent_def: Dict[str, Any],
    state: GraphState,
    instance_name: str
) -> Dict[str, Any]:
    """
    Executes a single subagent with its specific instructions.
    """
    
    # Extract relevant JSON subset for this subagent
    relevant_data = extract_relevant_data(
        state["extracted_facts"],
        subagent_def["input_fields"]
    )
    
    # Build subagent prompt
    prompt = build_subagent_prompt(
        objective=subagent_def["objective"],
        questions=subagent_def["questions"],
        data=relevant_data,
        tools=subagent_def.get("tools", [])
    )
    
    # Execute with tools
    tools = get_tools_for_subagent(subagent_def.get("tools", []))
    
    result = await llm_service.execute_with_tools(
        prompt=prompt,
        tools=tools,
        max_iterations=5
    )
    
    return {
        "agent_name": subagent_def["name"],
        "instance": instance_name,
        "objective": subagent_def["objective"],
        "result": result
    }
```

---

## 6. Tool Implementation

### 6.1 Product Database RAG Tool

```python
from typing import List, Dict, Any
import numpy as np
from anthropic import Anthropic

class ProductRAGTool:
    """
    RAG tool for querying the product database.
    Uses pgvector for similarity search.
    """
    
    def __init__(self, db_session, embedding_service):
        self.db = db_session
        self.embedding_service = embedding_service
    
    async def search_products(
        self,
        query: str,
        top_k: int = 5,
        category_filter: str = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic search over product database.
        """
        
        # Generate query embedding
        query_embedding = await self.embedding_service.embed(query)
        
        # Build SQL query with optional category filter
        sql = """
            SELECT 
                p.id,
                p.name,
                p.category,
                p.technical_specs,
                pe.chunk_text,
                pe.chunk_metadata,
                1 - (pe.embedding <=> :query_embedding) as similarity
            FROM product_embeddings pe
            JOIN products p ON pe.product_id = p.id
            WHERE 1=1
        """
        
        params = {"query_embedding": query_embedding}
        
        if category_filter:
            sql += " AND p.category = :category"
            params["category"] = category_filter
        
        sql += """
            ORDER BY pe.embedding <=> :query_embedding
            LIMIT :top_k
        """
        params["top_k"] = top_k
        
        results = await self.db.execute(sql, params)
        
        return [
            {
                "product_id": row.id,
                "product_name": row.name,
                "category": row.category,
                "technical_specs": row.technical_specs,
                "relevant_chunk": row.chunk_text,
                "metadata": row.chunk_metadata,
                "similarity": row.similarity
            }
            for row in results
        ]
    
    async def get_product_details(self, product_id: str) -> Dict[str, Any]:
        """
        Get complete product information.
        """
        
        result = await self.db.execute(
            "SELECT * FROM products WHERE id = :product_id",
            {"product_id": product_id}
        )
        
        product = result.fetchone()
        
        if not product:
            return None
        
        return {
            "id": product.id,
            "name": product.name,
            "category": product.category,
            "technical_specs": product.technical_specs,
            "description": product.description
        }


# Tool definition for Claude
product_rag_tool_definition = {
    "name": "search_product_database",
    "description": """
    Search the oxytec product database for relevant equipment and components.
    Use this tool to find specific products, technical specifications, or 
    compare different solutions. You can filter by product category.
    
    Categories: 'ntp_reactor', 'uv_lamp', 'ozone_generator', 'scrubber', 
    'control_system', 'sensor', 'auxiliary'
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
                "enum": ["ntp_reactor", "uv_lamp", "ozone_generator", "scrubber", 
                         "control_system", "sensor", "auxiliary"],
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
```

### 6.2 Web Search Tool

```python
from anthropic import Anthropic
import httpx

class WebSearchTool:
    """
    Web search focused on oxytec.com and relevant technical sources.
    """
    
    def __init__(self):
        self.base_url = "https://www.oxytec.com/en"
    
    async def search_oxytec(self, query: str) -> Dict[str, Any]:
        """
        Search oxytec.com for relevant information.
        Uses Claude's web search capability.
        """
        
        client = Anthropic()
        
        # Use Claude's native web search with site restriction
        search_query = f"site:oxytec.com {query}"
        
        # This would use Claude's web_search tool
        # Implementation depends on Claude's tool availability
        
        pass  # Implement based on available search API


web_search_tool_definition = {
    "name": "search_web",
    "description": """
    Search the web for technical information about plasma treatment, 
    UV/ozone processes, or industry standards. Prioritizes oxytec.com.
    """,
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            }
        },
        "required": ["query"]
    }
}
```

---

## 7. API Design

### 7.1 Key Endpoints

```python
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List
import uuid

app = FastAPI(title="Oxytec Feasibility Platform")

@app.post("/api/sessions/create")
async def create_session(
    files: List[UploadFile] = File(...),
    user_input: Dict[str, Any] = Body(...),
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Creates a new feasibility study session.
    Stores uploaded files and starts agent execution in background.
    """
    
    session_id = str(uuid.uuid4())
    
    # Store files
    file_paths = await store_uploaded_files(session_id, files)
    
    # Create session in DB
    session = await create_db_session(
        session_id=session_id,
        user_input=user_input,
        file_paths=file_paths
    )
    
    # Start agent graph execution in background
    background_tasks.add_task(
        run_agent_graph,
        session_id=session_id
    )
    
    return {
        "session_id": session_id,
        "status": "processing",
        "stream_url": f"/api/sessions/{session_id}/stream"
    }


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> Dict[str, Any]:
    """
    Get session status and results.
    """
    
    session = await get_db_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session.id,
        "status": session.status,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "result": session.result,
        "error": session.error
    }


@app.get("/api/sessions/{session_id}/stream")
async def stream_session(session_id: str):
    """
    SSE endpoint for real-time updates during processing.
    """
    
    async def event_generator():
        """
        Yields SSE events as agents complete their work.
        """
        
        # Subscribe to session updates (using pub/sub or polling)
        async for event in subscribe_to_session_events(session_id):
            yield {
                "event": event["type"],
                "data": json.dumps(event["data"])
            }
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


@app.get("/api/sessions/{session_id}/debug")
async def get_debug_info(session_id: str) -> Dict[str, Any]:
    """
    Get detailed debug information for a session.
    Shows all agent outputs, logs, and intermediate results.
    """
    
    logs = await get_session_logs(session_id)
    agent_outputs = await get_agent_outputs(session_id)
    
    return {
        "session_id": session_id,
        "logs": logs,
        "agent_outputs": agent_outputs
    }


@app.post("/api/products/ingest")
async def ingest_product_data(
    products: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Ingest product data into the database and generate embeddings.
    Used during initial setup or when adding new products.
    """
    
    ingested_count = 0
    
    for product in products:
        # Store product
        product_id = await store_product(product)
        
        # Chunk description and technical specs
        chunks = chunk_product_content(product)
        
        # Generate embeddings
        for chunk in chunks:
            embedding = await embedding_service.embed(chunk["text"])
            await store_product_embedding(
                product_id=product_id,
                chunk_text=chunk["text"],
                chunk_metadata=chunk["metadata"],
                embedding=embedding
            )
        
        ingested_count += 1
    
    return {
        "status": "success",
        "ingested_count": ingested_count
    }
```

---

## 8. Frontend Implementation Highlights

### 8.1 Real-time Status Updates

```typescript
// hooks/useSSE.ts
import { useEffect, useState } from 'react';

export function useSSE(sessionId: string) {
  const [events, setEvents] = useState<any[]>([]);
  const [status, setStatus] = useState<string>('connecting');

  useEffect(() => {
    const eventSource = new EventSource(
      `/api/sessions/${sessionId}/stream`
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setEvents((prev) => [...prev, data]);
      
      if (data.type === 'status_update') {
        setStatus(data.status);
      }
    };

    eventSource.onerror = () => {
      setStatus('error');
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [sessionId]);

  return { events, status };
}
```

### 8.2 Agent Visualization Component

```typescript
// components/AgentVisualization.tsx
export function AgentVisualization({ sessionId }: { sessionId: string }) {
  const { events } = useSSE(sessionId);
  
  // Parse events to build agent execution flow
  const agentFlow = useMemo(() => {
    return buildFlowFromEvents(events);
  }, [events]);

  return (
    <div className="w-full h-96 border rounded-lg p-4">
      {/* Render flow diagram showing:
          - Completed agents (green)
          - Running agents (blue, animated)
          - Parallel subagents
          - Pending agents (gray)
      */}
      <FlowDiagram nodes={agentFlow} />
    </div>
  );
}
```

---

## 9. Development Workflow

### 9.1 Setup Steps

```bash
# 1. Backend setup
cd backend
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -r pyproject.toml

# 2. Database setup
docker-compose up -d postgres
alembic upgrade head

# 3. Install pgvector extension
psql -d oxytec_db -c "CREATE EXTENSION vector;"

# 4. Frontend setup
cd frontend
npm install

# 5. Environment variables
cp .env.example .env
# Edit .env with your API keys and database URL
```

### 9.2 Running in Development

```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Database
docker-compose up postgres
```

### 9.3 Initial Product Data Ingestion

```bash
# Create a script to load product data
python scripts/ingest_products.py --source products.json
```

---

## 10. Deployment Considerations

### 10.1 Docker Setup

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml ./
RUN pip install uv && uv pip install --system -r pyproject.toml

# Copy application
COPY app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: oxytec_db
      POSTGRES_USER: oxytec
      POSTGRES_PASSWORD: your_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  
  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://oxytec:your_password@postgres:5432/oxytec_db
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    depends_on:
      - postgres
    ports:
      - "8000:8000"
  
  frontend:
    build: ./frontend
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8000
    depends_on:
      - backend
    ports:
      - "3000:3000"

volumes:
  postgres_data:
```

### 10.2 Production Checklist

- [ ] Set up proper secret management (not .env files)
- [ ] Configure CORS properly
- [ ] Set up rate limiting on API
- [ ] Implement authentication (if needed)
- [ ] Set up monitoring (Sentry, DataDog, etc.)
- [ ] Configure automated backups for PostgreSQL
- [ ] Set up CI/CD pipeline
- [ ] Load testing for parallel agent execution
- [ ] Set up proper logging aggregation

---

## 11. Testing Strategy

### 11.1 Unit Tests

```python
# tests/test_agents.py
import pytest
from app.agents.nodes.planner import planner_node

@pytest.mark.asyncio
async def test_planner_creates_subagents():
    state = {
        "extracted_facts": {
            "voc_composition": [...],
            "flow_rate": 1000,
            ...
        }
    }
    
    result = await planner_node(state)
    
    assert "planner_plan" in result
    assert len(result["planner_plan"]["subagents"]) > 0
    assert all("objective" in sa for sa in result["planner_plan"]["subagents"])
```

### 11.2 Integration Tests

```python
# tests/test_graph.py
@pytest.mark.asyncio
async def test_full_graph_execution():
    """Test complete agent graph with mocked LLM"""
    
    graph = create_agent_graph()
    
    result = await graph.ainvoke({
        "session_id": "test-session",
        "documents": [...],
        "user_input": {...}
    })
    
    assert result["final_report"]
    assert len(result["errors"]) == 0
```

### 11.3 Load Testing

```python
# Use locust for load testing parallel agent execution
from locust import HttpUser, task, between

class FeasibilityUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def create_session(self):
        files = {"file": open("test_doc.pdf", "rb")}
        self.client.post("/api/sessions/create", files=files)
```

---

## 12. Monitoring & Debugging

### 12.1 Structured Logging

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "subagent_completed",
    session_id=session_id,
    agent_name=agent_name,
    duration_ms=duration,
    tokens_used=tokens
)
```

### 12.2 Optional: LangSmith Integration

```python
from langsmith import Client

client = Client()

# Automatically traces all LangGraph executions
# Great for debugging complex agent interactions
```

---

## 13. Performance Optimizations

### Parallel Execution
- asyncio for concurrent API calls
- Connection pooling for database
- Redis caching for frequently accessed data (optional)

### Cost Optimization
- Cache extracted facts (don't re-extract same documents)
- Batch embedding generation
- Use Claude Haiku for simple tasks, Sonnet for complex reasoning

### Database Optimization
- Indexes on frequently queried columns
- JSONB indexes for common query patterns
- Regular VACUUM and ANALYZE

---

## 14. Migration Path from Flowise

1. **Export Flowise Configuration**: Document current prompts and tool usage
2. **Set up backend skeleton**: FastAPI + LangGraph
3. **Implement static agents first**: EXTRACTOR, WRITER
4. **Add dynamic planner**: Test with hardcoded subagent plans
5. **Implement parallel execution**: Add asyncio task management
6. **Build frontend progressively**: Upload → Status → Results → Debug
7. **Migrate tool definitions**: Web search, then add Product RAG
8. **Testing & validation**: Compare outputs with Flowise
9. **Deploy to staging**: Test with real data
10. **Production deployment**

---

## 15. Future Enhancements

- **Feedback Loop**: Allow users to rate studies, fine-tune prompts
- **Agent Learning**: Store successful strategies, reuse for similar cases
- **Multi-language Support**: Beyond German/English
- **Advanced RAG**: Hybrid search (dense + sparse), reranking
- **Streaming Results**: Show partial results as agents complete
- **Template Library**: Pre-configured agent plans for common scenarios
- **Cost Tracking**: Per-session cost breakdown
- **A/B Testing**: Compare different prompting strategies

---

## 16. Key Advantages of This Setup

1. **True Parallel Execution**: Unlike Flowise's sequential flow
2. **Dynamic Agent Creation**: Planner decides agent count/tasks
3. **Full Debugging**: Complete session history in database
4. **RAG Integration**: Native product database search
5. **Production-Ready**: Scalable, testable, maintainable
6. **Modern Stack**: FastAPI, LangGraph, Next.js
7. **Cost-Effective**: Async execution, smart caching
8. **Flexible**: Easy to add new tools, agents, or modify flow

---

## Summary

This architecture gives you:
- ✅ Dynamic multi-agent system with parallel execution
- ✅ Complete session debugging and logging
- ✅ Product database RAG integration
- ✅ Modern, maintainable codebase
- ✅ Production-ready from day one
- ✅ Easy Claude Code implementation

Start with the backend skeleton, get the basic graph working, then progressively add complexity. The modular design means you can iterate quickly without breaking existing functionality.

Questions? Ready to start building with Claude Code?
