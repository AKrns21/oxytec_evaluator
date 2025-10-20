"""Diagnostic script to understand ingestion issues."""

import asyncio
import json
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.services.embedding_service import EmbeddingService
from app.models.database import TechnologyKnowledge, TechnologyEmbedding
from uuid import uuid4


async def diagnose():
    """Run diagnostic tests."""

    print("=" * 80, flush=True)
    print("DIAGNOSTIC: Ingestion Issue Investigation", flush=True)
    print("=" * 80, flush=True)

    # Test 1: Load JSON
    print("\n[Test 1] Loading JSON file...", flush=True)
    try:
        with open('../docs/scope_oxytec_industry.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Loaded {len(data)} pages", flush=True)
    except Exception as e:
        print(f"❌ Failed to load JSON: {e}", flush=True)
        return

    # Test 2: Database connection
    print("\n[Test 2] Testing database connection...", flush=True)
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("SELECT COUNT(*) FROM technology_knowledge"))
            count = result.scalar()
            print(f"✅ Database connected. Current records: {count}", flush=True)
    except Exception as e:
        print(f"❌ Database connection failed: {e}", flush=True)
        return

    # Test 3: Embedding service
    print("\n[Test 3] Testing embedding service...", flush=True)
    try:
        embedding_service = EmbeddingService()
        test_embedding = await embedding_service.embed("test text")
        print(f"✅ Embedding service works. Dimension: {len(test_embedding)}", flush=True)
    except Exception as e:
        print(f"❌ Embedding service failed: {e}", flush=True)
        return

    # Test 4: Process first page only
    print("\n[Test 4] Processing FIRST PAGE ONLY...", flush=True)
    first_page_key = list(data.keys())[0]
    first_page = data[first_page_key]
    page_num = int(first_page_key)

    title_block = first_page.get('title_block', {})
    title = title_block.get('title', 'Unknown')

    print(f"  Page: {page_num}", flush=True)
    print(f"  Title: {title[:50]}...", flush=True)

    # Test 5: Create minimal chunks
    print("\n[Test 5] Creating minimal chunks...", flush=True)
    try:
        # Just create header chunk
        header_text = f"{title_block.get('rubric', '')} - {title}"
        print(f"  Header text length: {len(header_text)}", flush=True)

        # Try embedding
        print("  Generating embedding...", flush=True)
        embedding = await embedding_service.embed(header_text)
        print(f"  ✅ Embedding generated: {len(embedding)} dimensions", flush=True)

    except Exception as e:
        print(f"  ❌ Chunk creation failed: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return

    # Test 6: Database write
    print("\n[Test 6] Writing to database...", flush=True)
    try:
        async with AsyncSessionLocal() as db:
            print("  Creating TechnologyKnowledge record...", flush=True)
            tech_id = uuid4()
            tech_knowledge = TechnologyKnowledge(
                id=tech_id,
                page_number=page_num,
                rubric=title_block.get('rubric', ''),
                title=title,
                technology_type='diagnostic_test',
                content=first_page,
                pollutant_types=None,
                industries=None,
                products_mentioned=None,
            )
            db.add(tech_knowledge)
            await db.flush()
            print(f"  ✅ TechnologyKnowledge flushed (ID: {tech_id})", flush=True)

            print("  Creating TechnologyEmbedding record...", flush=True)
            tech_embedding = TechnologyEmbedding(
                technology_id=tech_id,
                chunk_type='header',
                chunk_text=header_text,
                chunk_metadata={'test': True},
                embedding=embedding,
            )
            db.add(tech_embedding)
            await db.flush()
            print("  ✅ TechnologyEmbedding flushed", flush=True)

            print("  Committing transaction...", flush=True)
            await db.commit()
            print("  ✅ Transaction committed", flush=True)

    except Exception as e:
        print(f"  ❌ Database write failed: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return

    # Test 7: Verify write
    print("\n[Test 7] Verifying data was written...", flush=True)
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("SELECT COUNT(*) FROM technology_knowledge WHERE technology_type = 'diagnostic_test'"))
            count = result.scalar()
            print(f"  TechnologyKnowledge records: {count}", flush=True)

            result = await db.execute(text("SELECT COUNT(*) FROM technology_embeddings WHERE chunk_metadata->>'test' = 'true'"))
            count = result.scalar()
            print(f"  TechnologyEmbedding records: {count}", flush=True)

            if count > 0:
                print("  ✅ Data verified in database!", flush=True)
            else:
                print("  ❌ No data found after commit!", flush=True)

    except Exception as e:
        print(f"  ❌ Verification failed: {e}", flush=True)
        return

    # Test 8: Cleanup
    print("\n[Test 8] Cleaning up test data...", flush=True)
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("DELETE FROM technology_embeddings WHERE chunk_metadata->>'test' = 'true'"))
            await db.execute(text("DELETE FROM technology_knowledge WHERE technology_type = 'diagnostic_test'"))
            await db.commit()
            print("  ✅ Cleanup complete", flush=True)
    except Exception as e:
        print(f"  ❌ Cleanup failed: {e}", flush=True)

    print("\n" + "=" * 80, flush=True)
    print("DIAGNOSTIC COMPLETE", flush=True)
    print("=" * 80, flush=True)


if __name__ == "__main__":
    asyncio.run(diagnose())
