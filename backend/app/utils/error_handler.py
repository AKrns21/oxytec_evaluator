"""Standardized error handling decorator for consistent error management across the application."""

import functools
import inspect
import traceback
from typing import Callable, Any, Optional
from app.utils.logger import get_logger


def handle_service_errors(
    operation_name: str,
    logger_name: Optional[str] = None,
    reraise: bool = True,
    default_return: Any = None
):
    """
    Decorator for consistent error handling in service methods.

    Provides standardized error logging with context and optional error recovery.

    Args:
        operation_name: Human-readable operation name for logging (e.g., "product_search")
        logger_name: Optional logger name override (defaults to decorated function's module)
        reraise: Whether to re-raise the exception after logging (default: True)
        default_return: Value to return if exception occurs and reraise=False (default: None)

    Usage:
        @handle_service_errors("product_search")
        async def search_products(self, query: str):
            # ... implementation
            return results

        # With custom error recovery
        @handle_service_errors("optional_feature", reraise=False, default_return=[])
        async def get_suggestions(self, query: str):
            # ... implementation that might fail
            return suggestions

    Example:
        # Before (inconsistent error handling):
        async def search_products(self, query: str):
            try:
                results = await self._query_database(query)
                return results
            except Exception as e:
                logger.error("product_search_failed", query=query, error=str(e))
                raise

        # After (standardized):
        @handle_service_errors("product_search")
        async def search_products(self, query: str):
            results = await self._query_database(query)
            return results
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get logger - use provided name or function's module
            logger = get_logger(logger_name or func.__module__)

            try:
                # Execute the function
                result = await func(*args, **kwargs)
                return result

            except Exception as e:
                # Extract function arguments for logging context
                # First arg is usually 'self' for methods
                context = {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "function": func.__name__
                }

                # Add first few kwargs as context (avoid logging sensitive data)
                if kwargs:
                    safe_kwargs = {
                        k: v for k, v in list(kwargs.items())[:3]
                        if k not in ["password", "api_key", "token", "secret"]
                    }
                    context.update(safe_kwargs)

                # Log the error with full context
                logger.error(
                    f"{operation_name}_failed",
                    **context,
                    exc_info=False  # Avoid duplicate stack traces
                )

                # Log stack trace at debug level for detailed debugging
                logger.debug(
                    f"{operation_name}_stack_trace",
                    stack_trace=traceback.format_exc()
                )

                # Re-raise or return default
                if reraise:
                    raise
                else:
                    logger.warning(
                        f"{operation_name}_using_default_return",
                        default_return=default_return
                    )
                    return default_return

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Get logger - use provided name or function's module
            logger = get_logger(logger_name or func.__module__)

            try:
                # Execute the function
                result = func(*args, **kwargs)
                return result

            except Exception as e:
                # Extract function arguments for logging context
                context = {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "function": func.__name__
                }

                # Add first few kwargs as context (avoid logging sensitive data)
                if kwargs:
                    safe_kwargs = {
                        k: v for k, v in list(kwargs.items())[:3]
                        if k not in ["password", "api_key", "token", "secret"]
                    }
                    context.update(safe_kwargs)

                # Log the error with full context
                logger.error(
                    f"{operation_name}_failed",
                    **context,
                    exc_info=False
                )

                # Log stack trace at debug level
                logger.debug(
                    f"{operation_name}_stack_trace",
                    stack_trace=traceback.format_exc()
                )

                # Re-raise or return default
                if reraise:
                    raise
                else:
                    logger.warning(
                        f"{operation_name}_using_default_return",
                        default_return=default_return
                    )
                    return default_return

        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def handle_agent_errors(
    agent_name: str,
    reraise: bool = False,
    include_in_state: bool = True
):
    """
    Decorator for error handling in agent nodes (LangGraph).

    Captures errors and optionally adds them to agent state for graceful degradation.

    Args:
        agent_name: Name of the agent for logging (e.g., "extractor", "planner")
        reraise: Whether to re-raise the exception (default: False for graceful degradation)
        include_in_state: Add error to state["errors"] list (default: True)

    Usage:
        @handle_agent_errors("extractor")
        async def extractor_node(state: GraphState) -> dict:
            # ... implementation
            return {"extracted_facts": facts}

    Returns:
        For agent nodes, returns partial state update with error information
        if exception occurs and reraise=False.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)

            try:
                # Execute agent node
                result = await func(*args, **kwargs)
                return result

            except Exception as e:
                # Log error with agent context
                logger.error(
                    f"{agent_name}_node_failed",
                    agent=agent_name,
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True  # Include stack trace for agent failures
                )

                # Prepare error info for state
                error_info = {
                    "agent": agent_name,
                    "error": str(e),
                    "error_type": type(e).__name__
                }

                # Re-raise or return error state
                if reraise:
                    raise
                else:
                    # Return partial state with error information
                    if include_in_state:
                        return {"errors": [error_info]}
                    else:
                        return {}

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)

            try:
                result = func(*args, **kwargs)
                return result

            except Exception as e:
                logger.error(
                    f"{agent_name}_node_failed",
                    agent=agent_name,
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True
                )

                error_info = {
                    "agent": agent_name,
                    "error": str(e),
                    "error_type": type(e).__name__
                }

                if reraise:
                    raise
                else:
                    if include_in_state:
                        return {"errors": [error_info]}
                    else:
                        return {}

        # Return appropriate wrapper
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
