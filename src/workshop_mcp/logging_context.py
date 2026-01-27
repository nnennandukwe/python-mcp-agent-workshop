"""Logging context module for correlation ID management.

This module provides request-scoped correlation IDs that inject into all log
records within a request context. This supports error tracking and debugging
by linking log entries to specific requests.

Usage:
    from workshop_mcp.logging_context import (
        correlation_id_var,
        CorrelationIdFilter,
        request_context,
    )

    # Add filter to logger
    handler = logging.StreamHandler()
    handler.addFilter(CorrelationIdFilter())
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(correlation_id)s] %(message)s"
    ))

    # Use in request handling
    with request_context() as corr_id:
        logger.info("Processing request")
        # corr_id is available for including in error responses
"""

import logging
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar

# ContextVar for correlation ID with default "-" when not in request context
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="-")


class CorrelationIdFilter(logging.Filter):
    """Logging filter that adds correlation_id attribute to log records.

    This filter retrieves the current correlation ID from the context variable
    and adds it to each log record, enabling request-scoped log tracing.

    Example:
        filter = CorrelationIdFilter()
        handler.addFilter(filter)
        # Now all log records will have record.correlation_id available
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation_id to log record.

        Args:
            record: The log record to enhance with correlation ID.

        Returns:
            True to allow the record to be logged.
        """
        record.correlation_id = correlation_id_var.get()
        return True


@contextmanager
def request_context() -> Generator[str, None, None]:
    """Context manager for request-scoped correlation IDs.

    Generates an 8-character hexadecimal correlation ID (first 8 chars of
    uuid4 hex) and sets it in the context variable. The ID is automatically
    reset to the default "-" when the context exits, whether normally or
    due to an exception.

    Yields:
        str: The 8-character hexadecimal correlation ID for this request.

    Example:
        with request_context() as corr_id:
            logger.info("Processing request")
            # Include corr_id in error response if needed
    """
    # Generate 8-char hex ID from uuid4
    corr_id = uuid.uuid4().hex[:8]

    # Set the correlation ID in context, keeping token for reset
    token = correlation_id_var.set(corr_id)

    try:
        yield corr_id
    finally:
        # Always reset to previous value (default "-" in most cases)
        correlation_id_var.reset(token)
