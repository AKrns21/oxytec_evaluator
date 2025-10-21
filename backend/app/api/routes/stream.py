"""Server-Sent Events (SSE) streaming endpoint."""

import asyncio
import json
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.dependencies import get_database
from app.models.database import Session as DBSession
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/sessions/{session_id}/stream")
async def stream_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_database)
):
    """
    SSE endpoint for real-time session updates.

    Client connects to this endpoint and receives events as the
    agent workflow progresses.

    Args:
        session_id: Session UUID
        db: Database session

    Returns:
        StreamingResponse with text/event-stream
    """

    # Verify session exists
    stmt = select(DBSession).where(DBSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        """
        Generate SSE events for this session.

        This is a polling implementation that queries the database periodically.
        Includes heartbeat mechanism to keep connections alive through proxies.

        For production with high concurrency, consider using Redis pub/sub or
        PostgreSQL LISTEN/NOTIFY to eliminate polling overhead.
        """

        import time

        last_status = None
        last_heartbeat = time.time()
        poll_interval = 2  # seconds
        heartbeat_interval = 30  # seconds - keep connection alive

        # Send initial status immediately on connection
        try:
            event_data = {
                "type": "connection_established",
                "status": session.status,
                "session_id": str(session_id),
                "updated_at": session.updated_at.isoformat()
            }
            yield f"event: status\ndata: {json.dumps(event_data)}\n\n"
            last_status = session.status
        except Exception as e:
            logger.error("sse_initial_status_error", session_id=str(session_id), error=str(e))

        while True:
            try:
                # Query session status
                async with AsyncSessionLocal() as poll_db:
                    stmt = select(DBSession).where(DBSession.id == session_id)
                    result = await poll_db.execute(stmt)
                    session_data = result.scalar_one_or_none()

                    if not session_data:
                        logger.warning("sse_session_not_found", session_id=str(session_id))
                        break

                    current_status = session_data.status

                    # Send status update if changed
                    if current_status != last_status:
                        event_data = {
                            "type": "status_update",
                            "status": current_status,
                            "updated_at": session_data.updated_at.isoformat()
                        }

                        yield f"event: status\ndata: {json.dumps(event_data)}\n\n"
                        last_status = current_status
                        logger.info(
                            "sse_status_update",
                            session_id=str(session_id),
                            status=current_status
                        )

                    # If completed or failed, send final event and close
                    if current_status in ["completed", "failed"]:
                        final_data = {
                            "type": "final",
                            "status": current_status,
                            "result": session_data.result,
                            "error": session_data.error
                        }
                        yield f"event: final\ndata: {json.dumps(final_data)}\n\n"
                        logger.info("sse_stream_completed", session_id=str(session_id))
                        break

                # Send heartbeat comment to keep connection alive
                # Many proxies/firewalls close idle connections after 60-120 seconds
                current_time = time.time()
                if current_time - last_heartbeat > heartbeat_interval:
                    # Send a comment (starts with :) which clients ignore
                    yield f": heartbeat {current_time}\n\n"
                    last_heartbeat = current_time

                # Poll every N seconds
                await asyncio.sleep(poll_interval)

            except Exception as e:
                logger.error("sse_error", session_id=str(session_id), error=str(e))
                error_data = {
                    "type": "error",
                    "error": "Internal server error"  # Don't expose details
                }
                yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


from app.db.session import AsyncSessionLocal
