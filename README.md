# Oxytec Multi-Agent Feasibility Platform

Automated feasibility study platform using dynamic multi-agent AI system powered by Claude and LangGraph.

## Overview

This platform automatically analyzes customer inquiries for VOC treatment systems and generates comprehensive feasibility studies. The system uses a **dynamic multi-agent architecture** where a Planner autonomously decides how many subagents to create and what each should analyze - all running in parallel for maximum efficiency.

## Key Features

- **Dynamic Multi-Agent System**: Planner creates custom agents based on inquiry complexity
- **Parallel Execution**: Multiple agents work simultaneously for fast results
- **Product Database RAG**: Semantic search over Oxytec product catalog using pgvector
- **Real-time Progress Streaming**: Monitor agent execution via Server-Sent Events
- **Complete Debugging**: Full session history and agent outputs stored in PostgreSQL
- **Professional Reports**: Comprehensive feasibility studies with risk assessment

## Architecture

The system follows this workflow:

1. **EXTRACTOR**: Extracts structured facts from uploaded documents
2. **PLANNER**: Dynamically decides which subagents to create (3-8 agents)
3. **SUBAGENTS** (parallel): Each investigates a specific aspect (VOC analysis, product selection, energy analysis, etc.)
4. **RISK ASSESSOR**: Synthesizes findings and evaluates risks
5. **WRITER**: Generates final professional report

## Tech Stack

### Backend
- **FastAPI** (Python 3.11+) - Async web framework
- **LangGraph** - Dynamic agent orchestration
- **Anthropic Claude** - AI reasoning and generation
- **PostgreSQL + pgvector** - Database with vector search
- **SQLAlchemy 2.0** - Async ORM

### Frontend (To be implemented)
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe frontend
- **shadcn/ui + Tailwind** - UI components
- **Server-Sent Events** - Real-time updates

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── agents/          # LangGraph agents and workflow
│   │   │   ├── nodes/       # EXTRACTOR, PLANNER, SUBAGENT, RISK_ASSESSOR, WRITER
│   │   │   ├── graph.py     # Workflow definition
│   │   │   ├── state.py     # State management
│   │   │   └── tools.py     # Agent tools (RAG, web search)
│   │   ├── api/
│   │   │   └── routes/      # FastAPI endpoints
│   │   ├── models/
│   │   │   ├── database.py  # SQLAlchemy models
│   │   │   └── schemas.py   # Pydantic schemas
│   │   ├── services/        # LLM, RAG, document processing
│   │   ├── db/              # Database session management
│   │   └── utils/           # Helpers and logging
│   ├── tests/
│   └── pyproject.toml
├── frontend/                # Next.js application (to be built)
├── docker-compose.yml
└── README.md
```

## Setup Instructions

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Anthropic API key
- OpenAI API key (for embeddings)

### 1. Clone and Navigate

```bash
cd /path/to/Repository_Evaluator
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies using uv (fast)
pip install uv
uv pip install -r pyproject.toml

# Or use pip directly
pip install -e .
```

### 3. Environment Configuration

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

Required environment variables:
- `ANTHROPIC_API_KEY`: Your Anthropic Claude API key
- `OPENAI_API_KEY`: Your OpenAI API key (for embeddings)
- `DATABASE_URL`: PostgreSQL connection string

### 4. Database Setup

```bash
# Start PostgreSQL with pgvector using Docker
docker-compose up -d postgres

# Wait for database to be ready (check logs)
docker-compose logs -f postgres

# The database schema will be created automatically on first run
```

### 5. Run Backend

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --port 8000

# Or using Docker
docker-compose up backend
```

The API will be available at: `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

### 6. Initial Product Data Ingestion

Before running feasibility studies, you need to populate the product database:

```bash
# Create a script to load your product catalog
python scripts/ingest_products.py --source path/to/products.json
```

Example product JSON structure:
```json
{
  "name": "NTP Reactor XL-5000",
  "category": "ntp_reactor",
  "technical_specs": {
    "flow_rate_max": 5000,
    "power_consumption": 12.5,
    "removal_efficiency": 95
  },
  "description": "High-capacity non-thermal plasma reactor..."
}
```

## Usage

### Creating a Feasibility Study

**Via API:**

```bash
curl -X POST "http://localhost:8000/api/sessions/create" \
  -F "files=@customer_inquiry.pdf" \
  -F "files=@voc_analysis.xlsx" \
  -F 'user_metadata={"company":"ABC Corp","contact":"john@example.com"}'
```

**Response:**
```json
{
  "session_id": "uuid",
  "status": "processing",
  "stream_url": "/api/sessions/{uuid}/stream"
}
```

### Monitoring Progress

Connect to the SSE stream to get real-time updates:

```javascript
const eventSource = new EventSource('http://localhost:8000/api/sessions/{uuid}/stream');

eventSource.addEventListener('status', (event) => {
  const data = JSON.parse(event.data);
  console.log('Status:', data.status);
});

eventSource.addEventListener('final', (event) => {
  const data = JSON.parse(event.data);
  console.log('Report:', data.result.final_report);
  eventSource.close();
});
```

### Retrieving Results

```bash
# Get session status and results
curl http://localhost:8000/api/sessions/{uuid}

# Get debug information (logs, agent outputs)
curl http://localhost:8000/api/sessions/{uuid}/debug
```

## Development

### Running Tests

```bash
cd backend
pytest tests/ -v
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Code Quality

```bash
# Format code
black app/

# Lint
ruff check app/

# Type checking
mypy app/
```

## Agent System Details

### How the Planner Works

The PLANNER agent analyzes the extracted facts and customer requirements, then dynamically creates 3-8 specialized subagents. Example subagents:

1. **VOC Analysis Agent**: Analyzes compound composition and treatment challenges
2. **Product Selection Agent**: Queries product database to find suitable equipment
3. **Process Design Agent**: Designs the treatment system configuration
4. **Energy Analysis Agent**: Calculates energy consumption and operating costs
5. **Regulatory Agent**: Checks compliance requirements
6. **Economic Analysis Agent**: Calculates ROI and payback period

### Parallel Execution

All subagents execute simultaneously using `asyncio.gather()`, dramatically reducing execution time compared to sequential systems.

### Tool System

Subagents can use:
- **Product Database Tool**: Semantic search via pgvector
- **Web Search Tool**: Search oxytec.com and technical resources
- **Document Tool**: Extract specific information from uploaded files

## Production Deployment

### Using Docker Compose

```bash
# Build and run all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Environment Variables for Production

Set these in your production environment:

```bash
DEBUG=false
LOG_LEVEL=WARNING
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/oxytec
CORS_ORIGINS=["https://yourdomain.com"]
```

### Performance Optimization

- Use connection pooling (configured in `config.py`)
- Enable Redis caching for frequent queries (optional)
- Use Claude Haiku for simple tasks, Sonnet for complex reasoning
- Cache document extraction results in database

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Recreate database
docker-compose down -v
docker-compose up -d postgres
```

### Agent Execution Failures

Check the debug endpoint for detailed logs:
```bash
curl http://localhost:8000/api/sessions/{uuid}/debug
```

### API Key Issues

Ensure your `.env` file has valid API keys:
```bash
# Test Anthropic API
python -c "from anthropic import Anthropic; print(Anthropic(api_key='your_key').messages.create(model='claude-3-5-sonnet-20241022', max_tokens=10, messages=[{'role':'user','content':'Hi'}]))"
```

## Roadmap

- [ ] Frontend implementation with Next.js
- [ ] Real-time agent visualization UI
- [ ] Advanced RAG with reranking
- [ ] Multi-language support (German/English)
- [ ] Template library for common scenarios
- [ ] Cost tracking per session
- [ ] Feedback loop for agent improvement
- [ ] Export reports as PDF/Word

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests
4. Run code quality checks
5. Submit a pull request

## License

Proprietary - Oxytec Internal Use

## Support

For questions or issues, contact the development team.

---

**Built with Claude Code** 🤖
