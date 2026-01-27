"""Tests for logging context module.

This module tests the correlation ID management for request tracing.
"""

import logging
import re
from contextvars import ContextVar

import pytest


class TestCorrelationIdVar:
    """Test ContextVar management for correlation IDs."""

    def test_default_and_context_values(self):
        """Test correlation_id_var returns '-' outside context and ID inside."""
        from workshop_mcp.logging_context import correlation_id_var, request_context

        # Outside any request context, should return default
        assert correlation_id_var.get() == "-"

        with request_context() as corr_id:
            # Inside context, should return the generated 8-char hex ID
            assert correlation_id_var.get() == corr_id
            assert len(corr_id) == 8
            assert re.match(r"^[0-9a-f]{8}$", corr_id)

        # After exit, should be back to default
        assert correlation_id_var.get() == "-"

    def test_nested_contexts_isolate_ids(self):
        """Nested request contexts maintain separate IDs and restore properly."""
        from workshop_mcp.logging_context import correlation_id_var, request_context

        with request_context() as outer_id:
            with request_context() as inner_id:
                assert correlation_id_var.get() == inner_id
                assert inner_id != outer_id

            # After inner exits, outer ID restored
            assert correlation_id_var.get() == outer_id

        assert correlation_id_var.get() == "-"


class TestCorrelationIdFilter:
    """Test logging.Filter subclass for correlation IDs."""

    def test_filter_adds_correlation_id_to_records(self):
        """CorrelationIdFilter adds correlation_id matching context to records."""
        from workshop_mcp.logging_context import CorrelationIdFilter, request_context

        filter_instance = CorrelationIdFilter()

        # Outside context - should have default
        record_outside = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        assert filter_instance.filter(record_outside) is True
        assert record_outside.correlation_id == "-"

        # Inside context - should have context ID
        with request_context() as corr_id:
            record_inside = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="test",
                args=(),
                exc_info=None,
            )
            filter_instance.filter(record_inside)
            assert record_inside.correlation_id == corr_id


class TestRequestContextManager:
    """Test request_context() context manager behavior."""

    def test_unique_ids_per_context(self):
        """Each request_context() generates a unique 8-char hex ID."""
        from workshop_mcp.logging_context import request_context

        ids = []
        for _ in range(10):
            with request_context() as corr_id:
                assert len(corr_id) == 8
                assert re.match(r"^[0-9a-f]{8}$", corr_id)
                ids.append(corr_id)

        assert len(ids) == len(set(ids))

    def test_resets_on_exception(self):
        """Context properly resets correlation ID when exception is raised."""
        from workshop_mcp.logging_context import correlation_id_var, request_context

        with pytest.raises(ValueError):
            with request_context():
                raise ValueError("test error")

        assert correlation_id_var.get() == "-"


class TestIntegrationWithLogging:
    """Test integration with Python logging system."""

    def test_filter_works_with_logger(self):
        """CorrelationIdFilter integrates with logging handlers."""
        from workshop_mcp.logging_context import CorrelationIdFilter, request_context

        test_logger = logging.getLogger("test_logging_context_integration")
        test_logger.setLevel(logging.INFO)

        corr_filter = CorrelationIdFilter()
        test_logger.addFilter(corr_filter)

        captured_records = []

        class CaptureHandler(logging.Handler):
            def emit(self, record):
                captured_records.append(record)

        handler = CaptureHandler()
        test_logger.addHandler(handler)

        try:
            test_logger.info("outside context")

            with request_context() as corr_id:
                test_logger.info("inside context")

            assert len(captured_records) == 2
            assert captured_records[0].correlation_id == "-"
            assert captured_records[1].correlation_id == corr_id
        finally:
            test_logger.removeHandler(handler)
            test_logger.removeFilter(corr_filter)


class TestModuleExports:
    """Test that module exports the correct public API."""

    def test_exports_expected_types(self):
        """Module exports correlation_id_var, CorrelationIdFilter, request_context."""
        from workshop_mcp.logging_context import (
            CorrelationIdFilter,
            correlation_id_var,
            request_context,
        )

        assert isinstance(correlation_id_var, ContextVar)
        assert issubclass(CorrelationIdFilter, logging.Filter)
        assert callable(request_context)
