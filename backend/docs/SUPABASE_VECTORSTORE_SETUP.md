# Supabase Vectorstore Setup Guide

**Purpose**: Replace local PostgreSQL with Supabase-hosted vectorstore for better reliability and performance.

## Prerequisites

- Supabase account (free tier is sufficient for development)
- OpenAI API key (for embeddings)

## Step 1: Create Supabase Project

1. Go to https://supabase.com and sign in
2. Click "New Project"
3. Fill in details:
   - **Project Name**: `oxytec-vectorstore` (or your choice)
   - **Database Password**: Choose a strong password (save it!)
   - **Region**: Choose closest to your location (e.g., Europe for Germany)
4. Click "Create new project" (takes ~2 minutes)

## Step 2: Enable pgvector Extension

Once your project is created:

1. Go to **SQL Editor** in the Supabase dashboard
2. Create a new query
3. Run this SQL:

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT * FROM pg_extension WHERE extname = 'vector';
```

4. You should see the vector extension listed

## Step 3: Get Connection String

1. In Supabase dashboard, go to **Project Settings** > **Database**
2. Scroll to **Connection String** section
3. Select **Connection pooling** tab
4. Copy the **Connection string** (Transaction mode)
5. It should look like:
   ```
   postgresql://postgres.xxxxxxxxxxxxx:password@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
   ```

### Important: Convert to asyncpg format

The connection string needs to be modified for async Python:
- Change `postgresql://` to `postgresql+asyncpg://`
- Replace `[YOUR-PASSWORD]` with your actual database password

**Final format:**
```
postgresql+asyncpg://postgres.xxxxxxxxxxxxx:YOUR_PASSWORD@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

## Step 4: Update Backend Configuration

1. Open `backend/.env` file
2. **Backup existing DATABASE_URL** (comment it out):
   ```bash
   # Local PostgreSQL (backup)
   # DATABASE_URL=postgresql+asyncpg://oxytec:oxytec_dev_password@localhost:5433/oxytec_db
   ```

3. **Add Supabase DATABASE_URL**:
   ```bash
   # Supabase vectorstore
   DATABASE_URL=postgresql+asyncpg://postgres.xxxxxxxxxxxxx:YOUR_PASSWORD@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
   ```

4. Verify other required variables are set:
   ```bash
   OPENAI_API_KEY=sk-...
   ANTHROPIC_API_KEY=sk-ant-...
   ```

## Step 5: Run Migrations on Supabase

Now we'll create the tables on Supabase:

```bash
cd backend
source .venv/bin/activate
python scripts/migrate_add_technology_tables.py
```

**Expected output:**
```
Connecting to database...
Creating technology_knowledge table...
Creating technology_embeddings table...
✅ Technology knowledge tables created successfully!
✅ Verified tables: technology_embeddings, technology_knowledge
```

### Verify in Supabase Dashboard

1. Go to **Table Editor** in Supabase
2. You should see two new tables:
   - `technology_knowledge`
   - `technology_embeddings`

## Step 6: Ingest Technology Knowledge

Now populate the vectorstore with Oxytec catalog data:

```bash
python scripts/ingest_technology_knowledge.py --source ../docs/scope_oxytec_industry.json --clear
```

**What to expect:**
- Script will process 21 pages
- Each page creates 5-10 chunks
- Each chunk requires an OpenAI embedding API call
- **Total time**: ~2-3 minutes (150+ API calls)
- **Output** should show progress for each page

**Expected output:**
```
2025-10-20 13:05:12 [info] ingestion_started
📖 Loading technology knowledge from ../docs/scope_oxytec_industry.json
✅ Loaded 21 pages from catalog
🗑️  Clearing existing technology knowledge...
✅ Existing data cleared

📄 Processing page 229...
  ℹ️  Type: general, Pollutants: [...], Industries: [...]
  📦 Created 8 chunks
  ✅ Page 229 committed

📄 Processing page 230...
  ℹ️  Type: uv_ozone, Pollutants: [...], Industries: [...]
  📦 Created 7 chunks
  ✅ Page 230 committed

[... continues for all 21 pages ...]

🎉 Ingestion completed!
  📚 Pages processed: 21
  📦 Total chunks created: 156
  🔢 Average chunks per page: 7.4
```

### Verify Data in Supabase

Check that data was written:

```bash
python -c "
import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text('SELECT COUNT(*) FROM technology_knowledge'))
        print(f'Technology pages: {result.scalar()}')

        result = await db.execute(text('SELECT COUNT(*) FROM technology_embeddings'))
        print(f'Embeddings: {result.scalar()}')

        result = await db.execute(text('SELECT COUNT(*) FROM technology_embeddings WHERE embedding IS NOT NULL'))
        print(f'Embeddings with vectors: {result.scalar()}')

asyncio.run(check())
"
```

**Expected output:**
```
Technology pages: 21
Embeddings: 156
Embeddings with vectors: 156
```

## Step 7: Test RAG System

Run the validation tests:

```bash
python scripts/test_technology_rag.py
```

**Expected output:**
```
🎉 All tests passed!
Total queries: 6
Passed: 6 (100.0%)
Failed: 0 (0.0%)
```

### Manual Query Test

Try a manual query:

```bash
python -c "
import asyncio
from app.services.technology_rag_service import TechnologyRAGService

async def test():
    rag = TechnologyRAGService()
    results = await rag.search_knowledge('UV ozone VOC removal efficiency', top_k=3)
    print(f'Found {len(results)} results:')
    for r in results:
        print(f'  - Page {r[\"page_number\"]}: {r[\"title\"][:60]}... (similarity: {r[\"similarity\"]:.3f})')

asyncio.run(test())
"
```

**Expected output:**
```
Found 3 results:
  - Page 232: UV/Ozon-System CEA/CFA - Produktinformation... (similarity: 0.856)
  - Page 250: Anwendungsbeispiel: Textilindustrie VOC-Reduktion... (similarity: 0.834)
  - Page 252: Technische Daten CEA-Serie... (similarity: 0.812)
```

## Step 8: Update Application Servers

If running the backend server, restart it to pick up the new DATABASE_URL:

```bash
# Stop existing server (Ctrl+C)
# Start fresh
uvicorn app.main:app --reload --port 8000
```

The application will now use Supabase for:
- RAG searches via `search_oxytec_knowledge` tool
- All technology knowledge queries
- Agent execution (session storage still uses local DB or can be migrated too)

## Troubleshooting

### Connection Timeout

**Error**: `asyncpg.exceptions.ConnectionDoesNotExistError`

**Solution**: Supabase connection pooler requires **transaction mode**. Ensure you're using the pooler connection string (port 6543), not the direct connection (port 5432).

### SSL Error

**Error**: `SSL certificate verification failed`

**Solution**: Add SSL parameters to connection string:
```
postgresql+asyncpg://postgres.xxx:password@aws-0-eu-central-1.pooler.supabase.com:6543/postgres?ssl=require
```

### Migration Already Exists

**Error**: `Table technology_knowledge already exists`

**Solution**: Tables were already created. Run with `--rollback` first:
```bash
python scripts/migrate_add_technology_tables.py --rollback
python scripts/migrate_add_technology_tables.py
```

### Ingestion Hangs

**Error**: Script runs but shows no output

**Solution**: Fixed in latest version with `flush=True` on all print statements. Pull latest code or add `flush=True` manually.

### No Results from RAG

**Error**: Queries return 0 results

**Causes**:
1. Data not ingested - check record counts (Step 6 verification)
2. Embeddings are NULL - check OpenAI API key is set
3. Wrong database - verify DATABASE_URL points to Supabase

## Monitoring in Supabase

### View Table Data

1. Go to **Table Editor**
2. Select `technology_knowledge` - see all catalog pages
3. Select `technology_embeddings` - see all chunks with embeddings

### Query Logs

1. Go to **Database** > **Logs**
2. See all SQL queries executed
3. Monitor performance

### Storage Usage

1. Go to **Project Settings** > **Database**
2. See **Database size** (should be ~10-20 MB after ingestion)
3. Free tier includes 500 MB

## Cost Considerations

### Supabase (Free Tier)
- ✅ 500 MB database storage (we use ~15 MB)
- ✅ 2 GB bandwidth/month
- ✅ Unlimited API requests
- ✅ 50,000 monthly active users

### OpenAI Embeddings
- Model: `text-embedding-ada-002`
- Cost: $0.0001 per 1K tokens
- One-time ingestion: ~156 chunks × 200 tokens avg = ~31K tokens = **$0.003**
- Ongoing queries: ~$0.0001 per search

**Total estimated cost**: < $1/month for development

## Next Steps

Once Supabase is working:

1. ✅ **Test agent workflow** - verify `search_oxytec_knowledge` tool works
2. ✅ **Run Phase 3 validation** - test with ammonia scrubber case
3. ✅ **Deploy to production** - update production .env with Supabase URL

## Rollback to Local PostgreSQL

If you need to switch back:

1. Uncomment local DATABASE_URL in `.env`
2. Comment out Supabase DATABASE_URL
3. Restart backend server
4. Data remains in both databases independently

## Benefits of Supabase

✅ **No local Docker** - works on any machine
✅ **Persistent storage** - survives reboots
✅ **Web UI** - easy data inspection
✅ **Backup/restore** - built-in snapshots
✅ **Scalable** - handles production load
✅ **Fast** - optimized PostgreSQL with pgvector
✅ **Free tier** - sufficient for development
