# Quick Start Guide

Get the Oxytec Feasibility Platform running in 5 minutes.

## Prerequisites

- Python 3.11+
- Docker Desktop running
- Anthropic API key
- OpenAI API key

## Step 1: Start Database

```bash
# Start PostgreSQL with pgvector
docker-compose up -d postgres

# Wait for it to be ready (about 10 seconds)
docker-compose logs -f postgres
# Press Ctrl+C when you see "database system is ready to accept connections"
```

## Step 2: Configure Backend

```bash
cd backend

# Copy environment file
cp .env.example .env

# Edit with your API keys
nano .env  # or use your favorite editor
```

Add your keys:
```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

## Step 3: Install Dependencies

```bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install uv for fast installation
pip install uv

# Install all dependencies
uv pip install -r pyproject.toml
```

## Step 4: Initialize Database

```bash
# The database schema will be created automatically on first run
# Just verify the connection
python -c "from app.db.session import init_db; import asyncio; asyncio.run(init_db())"
```

## Step 5: Load Sample Products

```bash
cd scripts

# Ingest example products
python ingest_products.py --source example_products.json

# This will load 9 sample Oxytec products into the database
```

## Step 6: Start Backend

```bash
cd ..  # Back to backend directory

# Start the API server
uvicorn app.main:app --reload --port 8000
```

You should see:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

## Step 7: Test the API

Open your browser to:
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/

## Step 8: Create Your First Feasibility Study

### Using the Swagger UI (http://localhost:8000/docs):

1. Navigate to `POST /api/sessions/create`
2. Click "Try it out"
3. Upload a test document (PDF, DOCX, or TXT)
4. Add user metadata:
   ```json
   {
     "company": "Test Company",
     "contact": "test@example.com",
     "requirements": "VOC treatment for 2000 m³/h"
   }
   ```
5. Click "Execute"

### Using curl:

```bash
# Create a test file
echo "VOC Analysis Report
Flow Rate: 2000 m³/h
VOC Concentration: 500 mg/m³
Compounds: Toluene, Xylene, MEK
Temperature: 25°C" > test_inquiry.txt

# Submit for analysis
curl -X POST "http://localhost:8000/api/sessions/create" \
  -F "files=@test_inquiry.txt" \
  -F 'user_metadata={"company":"Test Corp","requirements":"VOC treatment"}'
```

You'll get a response like:
```json
{
  "session_id": "uuid-here",
  "status": "processing",
  "stream_url": "/api/sessions/{uuid}/stream"
}
```

## Step 9: Monitor Progress

```bash
# Get session status
curl http://localhost:8000/api/sessions/{uuid}

# Or use the debug endpoint for details
curl http://localhost:8000/api/sessions/{uuid}/debug
```

The system will:
1. Extract facts from your document (5-10 seconds)
2. Create a plan with 3-8 subagents (5 seconds)
3. Execute subagents in parallel (15-30 seconds)
4. Assess risks (5-10 seconds)
5. Generate final report (10-15 seconds)

**Total time: ~40-70 seconds**

## Step 10: View Results

Once status is "completed":

```bash
curl http://localhost:8000/api/sessions/{uuid} | jq '.result.final_report'
```

You'll receive a comprehensive feasibility study report!

## Troubleshooting

### Database Connection Error
```bash
# Restart PostgreSQL
docker-compose restart postgres
```

### Import Errors
```bash
# Make sure you're in the virtual environment
source .venv/bin/activate

# Reinstall dependencies
uv pip install -r pyproject.toml
```

### API Key Errors
```bash
# Verify your .env file
cat .env | grep API_KEY

# Test Anthropic API
python -c "from anthropic import Anthropic; Anthropic(api_key='your-key').messages.create(model='claude-3-5-sonnet-20241022', max_tokens=10, messages=[{'role':'user','content':'test'}])"
```

## Next Steps

- Add your own product data
- Customize agent prompts in `app/agents/nodes/`
- Build the frontend UI (see architecture doc)
- Deploy to production with Docker Compose

## Common Commands

```bash
# Stop everything
docker-compose down

# View logs
docker-compose logs -f

# Restart backend
uvicorn app.main:app --reload --port 8000

# Run tests
pytest tests/ -v

# Format code
black app/

# Check types
mypy app/
```

## Need Help?

- Check the full [README.md](README.md) for detailed documentation
- Review the [Architecture Document](oxytec-platform-architecture.md)
- Look at API docs: http://localhost:8000/docs

---

**You're ready to go!** 🚀
