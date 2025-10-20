"""
Migration script to add technology_knowledge and technology_embeddings tables.

This script can be run manually to add the new tables to an existing database.
Alternatively, the tables will be created automatically on next app startup via init_db().

Usage:
    python scripts/migrate_add_technology_tables.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.db.session import engine
from app.models.database import Base, TechnologyKnowledge, TechnologyEmbedding
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def run_migration():
    """Create technology knowledge tables if they don't exist."""

    logger.info("migration_started", tables=["technology_knowledge", "technology_embeddings"])

    try:
        async with engine.begin() as conn:
            # Ensure pgvector extension exists
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

            # Create only the new tables (existing tables won't be affected)
            await conn.run_sync(Base.metadata.create_all)

            logger.info("migration_completed", status="success")
            print("✅ Technology knowledge tables created successfully!")

            # Verify tables exist
            result = await conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('technology_knowledge', 'technology_embeddings')
                ORDER BY table_name
            """))

            tables = [row[0] for row in result]
            print(f"✅ Verified tables: {', '.join(tables)}")

    except Exception as e:
        logger.error("migration_failed", error=str(e))
        print(f"❌ Migration failed: {e}")
        raise


async def rollback_migration():
    """Drop technology knowledge tables (rollback)."""

    logger.warning("rollback_started", tables=["technology_knowledge", "technology_embeddings"])

    try:
        async with engine.begin() as conn:
            # Drop tables in correct order (embeddings first due to foreign key)
            await conn.execute(text("DROP TABLE IF EXISTS technology_embeddings CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS technology_knowledge CASCADE"))

            logger.info("rollback_completed", status="success")
            print("✅ Technology knowledge tables dropped successfully!")

    except Exception as e:
        logger.error("rollback_failed", error=str(e))
        print(f"❌ Rollback failed: {e}")
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate technology knowledge tables")
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback migration (drop tables)"
    )

    args = parser.parse_args()

    if args.rollback:
        print("⚠️  WARNING: This will drop technology_knowledge and technology_embeddings tables!")
        confirm = input("Type 'yes' to confirm: ")
        if confirm.lower() == 'yes':
            asyncio.run(rollback_migration())
        else:
            print("Rollback cancelled.")
    else:
        asyncio.run(run_migration())
