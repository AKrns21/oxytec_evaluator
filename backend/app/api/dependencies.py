"""FastAPI dependencies."""

from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db


async def get_database() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database session."""
    async for session in get_db():
        yield session
