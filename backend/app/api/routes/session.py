"""Session management endpoints."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Dict, Any

from app.api.dependencies import get_database
from app.models.database import Session as DBSession, SessionLog, AgentOutput
from app.models.schemas import SessionResponse, DebugInfoResponse
from app.services.pdf_service import PDFService
from app.utils.logger import get_logger
from app.agents.prompts.versions import get_prompt_version, list_available_versions
from app.config import settings

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


@router.get("/sessions/{session_id}/prompts")
async def get_prompt_metadata(
    session_id: UUID,
    db: AsyncSession = Depends(get_database)
) -> Dict[str, Any]:
    """
    Get prompt version metadata for all agents used in this session.

    Returns information about which prompt versions were used by each agent,
    including version numbers, changelogs, and full prompt text.

    Args:
        session_id: Session UUID
        db: Database session

    Returns:
        Dictionary mapping agent types to their prompt metadata
    """

    try:
        # Get agent outputs to determine which agents were used and their versions
        outputs_stmt = select(AgentOutput).where(
            AgentOutput.session_id == session_id
        ).order_by(AgentOutput.created_at)
        outputs_result = await db.execute(outputs_stmt)
        outputs = outputs_result.scalars().all()

        if not outputs:
            raise HTTPException(
                status_code=404,
                detail="No agent outputs found for this session"
            )

        # Build response with prompt metadata for each agent
        prompt_data: Dict[str, Any] = {}

        # Map of agent types to their config version attribute
        agent_version_map = {
            "extractor": settings.extractor_prompt_version,
            "planner": settings.planner_prompt_version,
            "subagent": settings.subagent_prompt_version,
            "risk_assessor": settings.risk_assessor_prompt_version,
            "writer": settings.writer_prompt_version,
        }

        # Get unique agent types from outputs
        agent_types = set(output.agent_type for output in outputs)

        for agent_type in agent_types:
            # Get the version used (from agent_output or config)
            agent_output = next((o for o in outputs if o.agent_type == agent_type), None)
            version = (
                agent_output.prompt_version
                if agent_output and agent_output.prompt_version
                else agent_version_map.get(agent_type.lower(), "v1.0.0")
            )

            try:
                # Get prompt data for this version
                prompt_info = get_prompt_version(agent_type.lower(), version)

                # Get list of available versions for comparison
                available_versions = list_available_versions(agent_type.lower())

                # Find previous version for diff comparison
                previous_version = None
                if len(available_versions) > 1:
                    current_idx = available_versions.index(version)
                    if current_idx < len(available_versions) - 1:
                        previous_version = available_versions[current_idx + 1]

                # Check if agent output contains rendered prompt (actual prompt sent to LLM)
                rendered_prompt = None
                rendered_system_prompt = None
                if agent_output and agent_output.content:
                    rendered_prompt = agent_output.content.get("rendered_prompt")
                    rendered_system_prompt = agent_output.content.get("system_prompt")

                # Use rendered prompt if available, otherwise fall back to template
                prompt_text = rendered_prompt if rendered_prompt else prompt_info["PROMPT_TEMPLATE"]
                system_prompt_text = rendered_system_prompt if rendered_system_prompt else prompt_info["SYSTEM_PROMPT"]

                prompt_data[agent_type.lower()] = {
                    "version": version,
                    "changelog": prompt_info["CHANGELOG"],
                    "prompt_text": prompt_text,
                    "system_prompt": system_prompt_text,
                    "available_versions": available_versions,
                    "previous_version": previous_version,
                    "tokens_used": agent_output.tokens_used if agent_output else None,
                    "duration_ms": agent_output.duration_ms if agent_output else None,
                    "is_rendered": rendered_prompt is not None,  # Flag to indicate if this is the actual rendered prompt
                }

            except ImportError as e:
                logger.warning(
                    "prompt_version_not_found",
                    agent_type=agent_type,
                    version=version,
                    error=str(e)
                )
                # Return minimal data if prompt version not found
                prompt_data[agent_type.lower()] = {
                    "version": version,
                    "changelog": "Version not found",
                    "prompt_text": "",
                    "system_prompt": "",
                    "available_versions": [],
                    "previous_version": None,
                    "error": f"Prompt version {version} not found"
                }

        logger.info(
            "prompt_metadata_retrieved",
            session_id=str(session_id),
            agent_count=len(prompt_data)
        )

        return prompt_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_prompt_metadata_failed", session_id=str(session_id), error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
