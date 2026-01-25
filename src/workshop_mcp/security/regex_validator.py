"""Regex pattern validation module for ReDoS protection.

This module validates regex patterns before execution to prevent
Regular Expression Denial of Service (ReDoS) attacks.

Validation includes:
- Pattern length limits
- Detection of known ReDoS patterns (nested quantifiers)
- Syntax validation

Usage:
    from workshop_mcp.security.regex_validator import validate_pattern

    try:
        validate_pattern(user_pattern, use_regex=True)
        # Safe to compile and use the pattern
    except RegexValidationError as e:
        # Pattern rejected - return error to client
        return error_response(str(e))
"""

import regex
from typing import Pattern

from .exceptions import RegexValidationError

# Maximum allowed pattern length
MAX_PATTERN_LENGTH: int = 500

# Compiled patterns for detecting ReDoS vulnerabilities
# These detect nested quantifiers: (x+)+, (x*)+, (x+)*, (x*)*, etc.
# Both capturing and non-capturing groups
_REDOS_PATTERNS: list[Pattern[str]] = [
    # Nested quantifiers: group with inner quantifier + outer quantifier
    # Matches: (a+)+, (.*)+, (.+)*, (a*)*, (?:a+)+, etc.
    regex.compile(r"\([^)]*[+*][^)]*\)[+*]"),
]


def _is_redos_pattern(pattern: str) -> bool:
    """Check if pattern contains known ReDoS constructs.

    Detects patterns with nested quantifiers that can cause
    exponential backtracking.

    Args:
        pattern: The regex pattern string to check.

    Returns:
        True if the pattern contains ReDoS-vulnerable constructs.
    """
    for redos_pattern in _REDOS_PATTERNS:
        if redos_pattern.search(pattern):
            return True
    return False


def validate_pattern(pattern: str, use_regex: bool) -> None:
    """Validate a regex pattern for safety before execution.

    Performs validation in order:
    1. If use_regex is False, skip all validation (literal string)
    2. Check pattern length (max 500 characters)
    3. Check for known ReDoS patterns (nested quantifiers)
    4. Validate regex syntax

    Args:
        pattern: The pattern string to validate.
        use_regex: If True, validate as regex. If False, treat as literal.

    Raises:
        RegexValidationError: If validation fails for any reason.

    Example:
        >>> validate_pattern("a+b+", use_regex=True)  # OK
        >>> validate_pattern("(a+)+", use_regex=True)  # Raises
        >>> validate_pattern("(a+)+", use_regex=False)  # OK (literal)
    """
    # Non-regex mode: skip all validation
    if not use_regex:
        return

    # Check pattern length
    if len(pattern) > MAX_PATTERN_LENGTH:
        raise RegexValidationError(
            f"Pattern exceeds maximum length ({MAX_PATTERN_LENGTH} characters)"
        )

    # Check for ReDoS patterns
    if _is_redos_pattern(pattern):
        raise RegexValidationError("Pattern rejected: nested quantifiers detected")

    # Validate regex syntax using regex library (same as execution engine)
    try:
        regex.compile(pattern)
    except regex.error:
        raise RegexValidationError("Invalid regex syntax")
