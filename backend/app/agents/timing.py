"""Agent timing tracking utilities."""

import time
import functools
from typing import Any, Callable
from app.db.session import AsyncSessionLocal
from app.models.database import AgentOutput, SessionLog
from app.utils.logger import get_logger

logger = get_logger(__name__)


def track_agent_timing(agent_name: str):
    """
    Decorator to track agent execution time and save to database.

    Args:
        agent_name: Name of the agent (e.g., "extractor", "planner")

    Returns:
        Decorated async function with timing tracking
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(state: dict[str, Any]) -> dict[str, Any]:
            session_id = state.get("session_id")
            start_time = time.time()

            # Log agent start
            logger.info(f"{agent_name}_started", session_id=session_id)

            try:
                # Execute agent
                result = await func(state)

                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)
                duration_sec = duration_ms / 1000

                # Log agent completion
                logger.info(
                    f"{agent_name}_completed",
                    session_id=session_id,
                    duration_ms=duration_ms,
                    duration_sec=duration_sec
                )

                # Save timing data to database
                try:
                    async with AsyncSessionLocal() as db:
                        # Save to agent_outputs table
                        agent_output = AgentOutput(
                            session_id=session_id,
                            agent_type=agent_name,
                            agent_instance=None,
                            output_type="timing",
                            content={
                                "duration_ms": duration_ms,
                                "duration_sec": duration_sec,
                                "status": "completed"
                            },
                            tokens_used=None,  # Could be extracted from LLM service if available
                            duration_ms=duration_ms
                        )
                        db.add(agent_output)

                        # Save to session_logs table
                        log_start = SessionLog(
                            session_id=session_id,
                            agent_type=agent_name,
                            log_level="info",
                            message=f"{agent_name}_started",
                            data={"agent": agent_name}
                        )
                        log_completed = SessionLog(
                            session_id=session_id,
                            agent_type=agent_name,
                            log_level="info",
                            message=f"{agent_name}_completed",
                            data={
                                "agent": agent_name,
                                "duration_ms": duration_ms,
                                "duration_sec": duration_sec
                            }
                        )
                        db.add(log_start)
                        db.add(log_completed)

                        await db.commit()

                except Exception as db_error:
                    logger.warning(
                        "agent_timing_save_failed",
                        agent_name=agent_name,
                        session_id=session_id,
                        error=str(db_error)
                    )

                return result

            except Exception as e:
                # Calculate duration even on failure
                duration_ms = int((time.time() - start_time) * 1000)

                logger.error(
                    f"{agent_name}_failed",
                    session_id=session_id,
                    duration_ms=duration_ms,
                    error=str(e)
                )

                # Try to save failure timing
                try:
                    async with AsyncSessionLocal() as db:
                        agent_output = AgentOutput(
                            session_id=session_id,
                            agent_type=agent_name,
                            agent_instance=None,
                            output_type="timing",
                            content={
                                "duration_ms": duration_ms,
                                "status": "failed",
                                "error": str(e)
                            },
                            duration_ms=duration_ms
                        )
                        db.add(agent_output)

                        log_failed = SessionLog(
                            session_id=session_id,
                            agent_type=agent_name,
                            log_level="error",
                            message=f"{agent_name}_failed",
                            data={
                                "agent": agent_name,
                                "duration_ms": duration_ms,
                                "error": str(e)
                            }
                        )
                        db.add(log_failed)

                        await db.commit()
                except Exception:
                    pass  # Don't let DB errors mask the original exception

                raise

        return wrapper
    return decorator
