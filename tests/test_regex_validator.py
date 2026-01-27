"""Tests for RegexValidator security module.

Tests cover:
- Pattern length validation (max 500 characters)
- ReDoS pattern detection (nested quantifiers)
- Regex syntax validation
- Non-regex mode bypass
"""

import pytest

from workshop_mcp.security.exceptions import (
    RegexValidationError,
)
from workshop_mcp.security.regex_validator import MAX_PATTERN_LENGTH, validate_pattern


class TestPatternLengthValidation:
    """Test pattern length validation."""

    def test_pattern_exceeding_max_length_raises_error(self) -> None:
        """Pattern longer than 500 characters should raise RegexValidationError."""
        long_pattern = "a" * 501
        with pytest.raises(RegexValidationError) as exc_info:
            validate_pattern(long_pattern, use_regex=True)
        assert "Pattern exceeds maximum length" in str(exc_info.value)

    def test_pattern_at_max_length_passes(self) -> None:
        """Pattern at exactly 500 characters should pass."""
        pattern = "a" * 500
        validate_pattern(pattern, use_regex=True)


class TestRedosPatternDetection:
    """Test detection of ReDoS patterns (nested quantifiers)."""

    def test_nested_quantifiers_rejected(self) -> None:
        """Patterns with nested quantifiers should be rejected as ReDoS."""
        redos_patterns = ["(a+)+", "(.*)+", "(.+)*", "(?:a+)+", "(a*)*"]
        for pattern in redos_patterns:
            with pytest.raises(RegexValidationError) as exc_info:
                validate_pattern(pattern, use_regex=True)
            assert "nested quantifiers detected" in str(exc_info.value)

    def test_safe_quantifiers_allowed(self) -> None:
        """Safe patterns with quantifiers should be allowed."""
        safe_patterns = ["a+b+", ".*", ".+", "[a-z]+", "(a|b)+", r"\b\w+\b"]
        for pattern in safe_patterns:
            validate_pattern(pattern, use_regex=True)


class TestSyntaxValidation:
    """Test regex syntax validation."""

    def test_invalid_syntax_rejected(self) -> None:
        """Patterns with invalid syntax should be rejected."""
        invalid_patterns = ["[invalid", "(unclosed", r"\x", "a{3,2}"]
        for pattern in invalid_patterns:
            with pytest.raises(RegexValidationError) as exc_info:
                validate_pattern(pattern, use_regex=True)
            assert "Invalid regex syntax" in str(exc_info.value)

    def test_valid_syntax_passes(self) -> None:
        """Valid regex patterns should pass."""
        valid_patterns = [
            "[a-z]+",
            "(foo|bar)+",
            r"\.\*\+\?",
            r"[\w.+-]+@[\w-]+\.[\w.-]+",
            r"foo(?=bar)",
        ]
        for pattern in valid_patterns:
            validate_pattern(pattern, use_regex=True)


class TestNonRegexMode:
    """Test non-regex mode behavior."""

    def test_non_regex_mode_skips_all_validation(self) -> None:
        """Non-regex mode should skip all validation."""
        # Long pattern - would fail length check
        validate_pattern("a" * 1000, use_regex=False)
        # ReDoS pattern - would fail nested quantifier check
        validate_pattern("(a+)+", use_regex=False)
        # Invalid syntax - would fail syntax check
        validate_pattern("[invalid", use_regex=False)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_string_passes(self) -> None:
        """Empty string should pass in both modes."""
        validate_pattern("", use_regex=True)
        validate_pattern("", use_regex=False)

    def test_max_pattern_length_constant(self) -> None:
        """MAX_PATTERN_LENGTH should be 500."""
        assert MAX_PATTERN_LENGTH == 500
