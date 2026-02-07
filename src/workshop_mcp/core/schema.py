"""Unified issue output schema for all analysis tools."""

from dataclasses import dataclass
from enum import Enum


class Severity(Enum):
    """Severity levels for code issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class CodeIssue:
    """Represents a code issue detected by any analysis tool."""

    tool: str
    category: str
    severity: Severity
    message: str
    line: int
    suggestion: str | None = None
    code_snippet: str | None = None
    function_name: str | None = None
    end_line: int | None = None
    column: int | None = None
