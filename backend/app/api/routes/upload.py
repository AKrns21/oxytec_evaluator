"""Upload and session creation endpoints."""

import uuid
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.dependencies import get_database
from app.models.database import Session as DBSession, Document
from app.models.schemas import SessionStatus
from app.agents.graph import run_agent_graph
from app.config import settings
from app.utils.helpers import ensure_dir_exists, sanitize_filename
from app.utils.logger import get_logger
from app.db.session import AsyncSessionLocal

logger = get_logger(__name__)
router = APIRouter()


@router.post("/sessions/create", response_model=SessionStatus)
async def create_session(
    files: List[UploadFile] = File(...),
    user_metadata: str = Form("{}"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_database)
):
    """
    Create a new feasibility study session.

    Args:
        files: List of uploaded documents
        user_metadata: JSON string with user inputs (company, requirements, etc.)
        background_tasks: FastAPI background tasks
        db: Database session

    Returns:
        Session status with ID and stream URL
    """

    session_id = str(uuid.uuid4())

    logger.info(
        "session_creation_started",
        session_id=session_id,
        num_files=len(files)
    )

    try:
        # Parse user metadata
        import json
        try:
            user_input = json.loads(user_metadata)
        except json.JSONDecodeError:
            user_input = {}

        # Create session in database
        db_session = DBSession(
            id=uuid.UUID(session_id),
            status="pending",
            user_metadata=user_input
        )
        db.add(db_session)
        await db.commit()

        # Store uploaded files
        upload_dir = ensure_dir_exists(Path(settings.upload_dir) / session_id)
        document_records = []

        for file in files:
            # Validate file extension
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in settings.allowed_extensions:
                logger.warning(
                    "invalid_file_extension",
                    filename=file.filename,
                    extension=file_ext
                )
                continue

            # Save file
            safe_filename = sanitize_filename(file.filename)
            file_path = upload_dir / safe_filename

            content = await file.read()
            file_path.write_bytes(content)

            # Create document record
            doc = Document(
                session_id=uuid.UUID(session_id),
                filename=safe_filename,
                file_path=str(file_path),
                mime_type=file.content_type,
                size_bytes=len(content)
            )
            db.add(doc)
            document_records.append({
                "filename": safe_filename,
                "file_path": str(file_path),
                "mime_type": file.content_type
            })

        await db.commit()

        # Start agent graph execution in background
        background_tasks.add_task(
            execute_agent_workflow,
            session_id=session_id,
            documents=document_records,
            user_input=user_input
        )

        logger.info(
            "session_created",
            session_id=session_id,
            documents_count=len(document_records)
        )

        return SessionStatus(
            session_id=uuid.UUID(session_id),
            status="processing",
            stream_url=f"/api/sessions/{session_id}/stream"
        )

    except Exception as e:
        logger.error(
            "session_creation_failed",
            session_id=session_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


async def execute_agent_workflow(
    session_id: str,
    documents: List[dict],
    user_input: dict
):
    """
    Background task to execute the agent workflow.

    Args:
        session_id: Session UUID
        documents: List of document metadata
        user_input: User-provided metadata
    """

    logger.info("agent_workflow_started", session_id=session_id)

    async with AsyncSessionLocal() as db:
        try:
            # Update session status
            stmt = select(DBSession).where(DBSession.id == uuid.UUID(session_id))
            result = await db.execute(stmt)
            session = result.scalar_one()
            session.status = "processing"
            await db.commit()

            # Run agent graph
            result = await run_agent_graph(
                session_id=session_id,
                documents=documents,
                user_input=user_input
            )

            # Update session with results
            session.status = "completed"
            session.result = {
                "final_report": result.get("final_report"),
                "extracted_facts": result.get("extracted_facts"),
                "planner_plan": result.get("planner_plan"),
                "subagent_results": result.get("subagent_results", []),
                "risk_assessment": result.get("risk_assessment"),
                "num_subagents": len(result.get("subagent_results", [])),
                "errors": result.get("errors", []),
                "warnings": result.get("warnings", [])
            }
            await db.commit()

            logger.info("agent_workflow_completed", session_id=session_id)

        except Exception as e:
            logger.error("agent_workflow_failed", session_id=session_id, error=str(e))

            # Update session with error
            session.status = "failed"
            session.error = str(e)
            await db.commit()
