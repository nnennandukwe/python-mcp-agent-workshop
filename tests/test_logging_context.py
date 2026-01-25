"""Tests for logging context module.

This module tests the correlation ID management for request tracing.
Tests follow TDD cycle: RED (write failing tests) -> GREEN (implement) -> REFACTOR.
"""

import logging
import re
from unittest import mock

import pytest


class TestCorrelationIdVar:
    """Test ContextVar management for correlation IDs."""

    def test_default_value_outside_request_context(self):
        """correlation_id_var.get() returns '-' when not in request context."""
        from workshop_mcp.logging_context import correlation_id_var

        # Outside any request context, should return default
        assert correlation_id_var.get() == "-"

    def test_returns_id_within_request_context(self):
        """correlation_id_var.get() returns 8-char hex ID within request_context."""
        from workshop_mcp.logging_context import correlation_id_var, request_context

        with request_context() as corr_id:
            # Inside context, should return the generated ID
            assert correlation_id_var.get() == corr_id
            # ID should be 8 chars hex
            assert len(corr_id) == 8
            assert re.match(r"^[0-9a-f]{8}$", corr_id)

    def test_resets_to_default_after_context_exit(self):
        """correlation_id_var.get() returns '-' after request_context exits."""
        from workshop_mcp.logging_context import correlation_id_var, request_context

        # Enter and exit context
        with request_context():
            pass

        # After exit, should be back to default
        assert correlation_id_var.get() == "-"

    def test_nested_contexts_isolate_ids(self):
        """Nested request contexts should maintain separate IDs."""
        from workshop_mcp.logging_context import correlation_id_var, request_context

        with request_context() as outer_id:
            with request_context() as inner_id:
                # Inner context has its own ID
                assert correlation_id_var.get() == inner_id
                assert inner_id != outer_id

            # After inner exits, outer ID restored
            assert correlation_id_var.get() == outer_id

        # After all exit, back to default
        assert correlation_id_var.get() == "-"


class TestCorrelationIdFilter:
    """Test logging.Filter subclass for correlation IDs."""

    def test_adds_correlation_id_to_log_record(self):
        """CorrelationIdFilter adds correlation_id attribute to log records."""
        from workshop_mcp.logging_context import CorrelationIdFilter

        filter_instance = CorrelationIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )

        # Apply filter
        result = filter_instance.filter(record)

        # Filter should return True (allow record)
        assert result is True
        # Record should have correlation_id attribute
        assert hasattr(record, "correlation_id")

    def test_correlation_id_is_default_outside_context(self):
        """Log record outside request context has correlation_id='-'."""
        from workshop_mcp.logging_context import CorrelationIdFilter

        filter_instance = CorrelationIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )

        filter_instance.filter(record)

        assert record.correlation_id == "-"

    def test_correlation_id_matches_context_inside_request(self):
        """Log record inside request context has matching correlation_id."""
        from workshop_mcp.logging_context import (
            CorrelationIdFilter,
            request_context,
        )

        filter_instance = CorrelationIdFilter()

        with request_context() as corr_id:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="test message",
                args=(),
                exc_info=None,
            )

            filter_instance.filter(record)

            assert record.correlation_id == corr_id


class TestRequestContextManager:
    """Test request_context() context manager behavior."""

    def test_yields_8_char_hex_id(self):
        """request_context() yields an 8-character hexadecimal ID."""
        from workshop_mcp.logging_context import request_context

        with request_context() as corr_id:
            assert len(corr_id) == 8
            assert re.match(r"^[0-9a-f]{8}$", corr_id)

    def test_unique_ids_per_context(self):
        """Each request_context() generates a unique ID."""
        from workshop_mcp.logging_context import request_context

        ids = []
        for _ in range(10):
            with request_context() as corr_id:
                ids.append(corr_id)

        # All IDs should be unique
        assert len(ids) == len(set(ids))

    def test_resets_on_normal_exit(self):
        """Context properly resets correlation ID on normal exit."""
        from workshop_mcp.logging_context import correlation_id_var, request_context

        with request_context():
            # Inside context
            pass

        # After normal exit
        assert correlation_id_var.get() == "-"

    def test_resets_on_exception(self):
        """Context properly resets correlation ID when exception is raised."""
        from workshop_mcp.logging_context import correlation_id_var, request_context

        with pytest.raises(ValueError):
            with request_context():
                raise ValueError("test error")

        # After exception, should still reset
        assert correlation_id_var.get() == "-"


class TestIntegrationWithLogging:
    """Test integration with Python logging system."""

    def test_filter_works_with_logger(self):
        """CorrelationIdFilter integrates with logging handlers."""
        from workshop_mcp.logging_context import (
            CorrelationIdFilter,
            request_context,
        )

        # Create a test logger with our filter
        test_logger = logging.getLogger("test_logging_context_integration")
        test_logger.setLevel(logging.INFO)

        # Add filter to capture correlation IDs
        corr_filter = CorrelationIdFilter()
        test_logger.addFilter(corr_filter)

        # Capture log records
        captured_records = []

        class CaptureHandler(logging.Handler):
            def emit(self, record):
                captured_records.append(record)

        handler = CaptureHandler()
        test_logger.addHandler(handler)

        try:
            # Log outside context
            test_logger.info("outside context")

            # Log inside context
            with request_context() as corr_id:
                test_logger.info("inside context")

            # Verify captured records
            assert len(captured_records) == 2
            assert captured_records[0].correlation_id == "-"
            assert captured_records[1].correlation_id == corr_id

        finally:
            # Cleanup
            test_logger.removeHandler(handler)
            test_logger.removeFilter(corr_filter)


class TestModuleExports:
    """Test that module exports the correct public API."""

    def test_exports_correlation_id_var(self):
        """Module exports correlation_id_var."""
        from workshop_mcp.logging_context import correlation_id_var
        from contextvars import ContextVar

        assert isinstance(correlation_id_var, ContextVar)

    def test_exports_correlation_id_filter(self):
        """Module exports CorrelationIdFilter as logging.Filter subclass."""
        from workshop_mcp.logging_context import CorrelationIdFilter

        assert issubclass(CorrelationIdFilter, logging.Filter)

    def test_exports_request_context(self):
        """Module exports request_context as a callable."""
        from workshop_mcp.logging_context import request_context

        assert callable(request_context)
