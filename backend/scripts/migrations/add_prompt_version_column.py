"""
Database migration: Add prompt_version column to agent_outputs table

This migration adds version tracking for prompts used by each agent.
Allows tracing report outputs back to exact prompt versions.

Run with: python3 scripts/migrations/add_prompt_version_column.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from app.db.session import AsyncSessionLocal, engine
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def run_migration():
    """Add prompt_version column to agent_outputs table."""

    logger.info("migration_start", migration="add_prompt_version_column")

    try:
        async with engine.begin() as conn:
            # Check if column already exists
            check_query = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'agent_outputs'
                AND column_name = 'prompt_version'
            """)

            result = await conn.execute(check_query)
            existing = result.fetchone()

            if existing:
                logger.info("migration_skip", reason="Column prompt_version already exists")
                print("✅ Column 'prompt_version' already exists in agent_outputs table")
                return

            # Add the column
            alter_query = text("""
                ALTER TABLE agent_outputs
                ADD COLUMN prompt_version VARCHAR(20) NULL
            """)

            await conn.execute(alter_query)

            logger.info("migration_success", column="prompt_version", table="agent_outputs")
            print("✅ Successfully added 'prompt_version' column to agent_outputs table")
            print("   Type: VARCHAR(20), Nullable: TRUE")
            print("   Example values: 'v1.0.0', 'v1.2.3'")

    except Exception as e:
        logger.error("migration_failed", error=str(e))
        print(f"❌ Migration failed: {e}")
        raise


async def rollback_migration():
    """Remove prompt_version column from agent_outputs table."""

    logger.info("rollback_start", migration="add_prompt_version_column")

    try:
        async with engine.begin() as conn:
            # Check if column exists
            check_query = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'agent_outputs'
                AND column_name = 'prompt_version'
            """)

            result = await conn.execute(check_query)
            existing = result.fetchone()

            if not existing:
                logger.info("rollback_skip", reason="Column prompt_version does not exist")
                print("✅ Column 'prompt_version' does not exist (already rolled back or never created)")
                return

            # Drop the column
            drop_query = text("""
                ALTER TABLE agent_outputs
                DROP COLUMN prompt_version
            """)

            await conn.execute(drop_query)

            logger.info("rollback_success", column="prompt_version", table="agent_outputs")
            print("✅ Successfully removed 'prompt_version' column from agent_outputs table")

    except Exception as e:
        logger.error("rollback_failed", error=str(e))
        print(f"❌ Rollback failed: {e}")
        raise


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        print("\n🔄 Rolling back migration: Removing prompt_version column...\n")
        asyncio.run(rollback_migration())
    else:
        print("\n🚀 Running migration: Adding prompt_version column to agent_outputs table...\n")
        asyncio.run(run_migration())
        print("\n💡 To rollback this migration, run: python3 scripts/migrations/add_prompt_version_column.py rollback\n")
