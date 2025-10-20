"""Session management endpoints."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.api.dependencies import get_database
from app.models.database import Session as DBSession, SessionLog, AgentOutput
from app.models.schemas import SessionResponse, DebugInfoResponse
from app.services.pdf_service import PDFService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_database)
):
    """
    Get session status and results.

    Args:
        session_id: Session UUID
        db: Database session

    Returns:
        Session details with status and results
    """

    try:
        stmt = select(DBSession).where(DBSession.id == session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return SessionResponse(
            id=session.id,
            status=session.status,
            created_at=session.created_at,
            updated_at=session.updated_at,
            user_metadata=session.user_metadata,
            result=session.result,
            error=session.error
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_session_failed", session_id=str(session_id), error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/debug", response_model=DebugInfoResponse)
async def get_debug_info(
    session_id: UUID,
    db: AsyncSession = Depends(get_database)
):
    """
    Get detailed debug information for a session.

    Includes all agent outputs, logs, and intermediate results.

    Args:
        session_id: Session UUID
        db: Database session

    Returns:
        Debug information with logs and agent outputs
    """

    try:
        # Get logs
        logs_stmt = select(SessionLog).where(
            SessionLog.session_id == session_id
        ).order_by(SessionLog.timestamp)
        logs_result = await db.execute(logs_stmt)
        logs = logs_result.scalars().all()

        # Get agent outputs
        outputs_stmt = select(AgentOutput).where(
            AgentOutput.session_id == session_id
        ).order_by(AgentOutput.created_at)
        outputs_result = await db.execute(outputs_stmt)
        outputs = outputs_result.scalars().all()

        return DebugInfoResponse(
            session_id=session_id,
            logs=logs,
            agent_outputs=outputs
        )

    except Exception as e:
        logger.error("get_debug_info_failed", session_id=str(session_id), error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/pdf")
async def download_pdf(
    session_id: UUID,
    db: AsyncSession = Depends(get_database)
):
    """
    Download the feasibility report as PDF.

    Args:
        session_id: Session UUID
        db: Database session

    Returns:
        PDF file as binary response
    """

    try:
        # Get session
        stmt = select(DBSession).where(DBSession.id == session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Check if report is available
        if not session.result or "final_report" not in session.result:
            raise HTTPException(
                status_code=400,
                detail="Report not yet generated or session not completed"
            )

        # Get the markdown report
        markdown_report = session.result["final_report"]

        # Generate PDF
        pdf_service = PDFService()
        pdf_bytes = pdf_service.generate_pdf(
            markdown_content=markdown_report,
            title="Machbarkeitsstudie"
        )

        # Create filename with date
        filename = f"feasibility-report-{datetime.now().strftime('%Y-%m-%d')}.pdf"

        logger.info(
            "pdf_downloaded",
            session_id=str(session_id),
            pdf_size=len(pdf_bytes)
        )

        # Return PDF as response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("pdf_download_failed", session_id=str(session_id), error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
