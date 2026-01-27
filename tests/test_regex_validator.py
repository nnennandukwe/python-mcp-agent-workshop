"""Tests for RegexValidator security module.

Tests cover:
- Pattern length validation (max 500 characters)
- ReDoS pattern detection (nested quantifiers)
- Regex syntax validation
- Non-regex mode bypass
- Exception hierarchy
"""

import pytest

from workshop_mcp.security.exceptions import (
    RegexAbortError,
    RegexTimeoutError,
    RegexValidationError,
    SecurityValidationError,
)
from workshop_mcp.security.regex_validator import MAX_PATTERN_LENGTH, validate_pattern


class TestExceptionHierarchy:
    """Test that regex exceptions inherit from SecurityValidationError."""

    def test_regex_validation_error_inherits_from_security_validation_error(
        self,
    ) -> None:
        """RegexValidationError should inherit from SecurityValidationError."""
        error = RegexValidationError("test")
        assert isinstance(error, SecurityValidationError)
        assert isinstance(error, Exception)

    def test_regex_timeout_error_inherits_from_security_validation_error(self) -> None:
        """RegexTimeoutError should inherit from SecurityValidationError."""
        error = RegexTimeoutError()
        assert isinstance(error, SecurityValidationError)
        assert isinstance(error, Exception)

    def test_regex_abort_error_inherits_from_security_validation_error(self) -> None:
        """RegexAbortError should inherit from SecurityValidationError."""
        error = RegexAbortError()
        assert isinstance(error, SecurityValidationError)
        assert isinstance(error, Exception)

    def test_regex_timeout_error_default_message(self) -> None:
        """RegexTimeoutError should have default message."""
        error = RegexTimeoutError()
        assert str(error) == "Pattern evaluation timed out"

    def test_regex_abort_error_default_message(self) -> None:
        """RegexAbortError should have default message."""
        error = RegexAbortError()
        assert str(error) == "Pattern timed out on too many files"

    def test_regex_timeout_error_custom_message(self) -> None:
        """RegexTimeoutError should accept custom message."""
        error = RegexTimeoutError("custom timeout message")
        assert str(error) == "custom timeout message"

    def test_regex_abort_error_custom_message(self) -> None:
        """RegexAbortError should accept custom message."""
        error = RegexAbortError("custom abort message")
        assert str(error) == "custom abort message"


class TestMaxPatternLength:
    """Test that MAX_PATTERN_LENGTH constant is correctly set."""

    def test_max_pattern_length_is_500(self) -> None:
        """MAX_PATTERN_LENGTH should be 500."""
        assert MAX_PATTERN_LENGTH == 500


class TestPatternLengthValidation:
    """Test pattern length validation."""

    def test_pattern_exceeding_max_length_raises_error(self) -> None:
        """Pattern longer than 500 characters should raise RegexValidationError."""
        long_pattern = "a" * 501
        with pytest.raises(RegexValidationError) as exc_info:
            validate_pattern(long_pattern, use_regex=True)
        assert "Pattern exceeds maximum length (500 characters)" in str(exc_info.value)

    def test_pattern_at_max_length_passes(self) -> None:
        """Pattern at exactly 500 characters should pass."""
        pattern = "a" * 500
        # Should not raise
        validate_pattern(pattern, use_regex=True)

    def test_pattern_under_max_length_passes(self) -> None:
        """Pattern under 500 characters should pass."""
        pattern = "simple"
        # Should not raise
        validate_pattern(pattern, use_regex=True)

    def test_non_regex_mode_skips_length_check(self) -> None:
        """Non-regex mode should skip length validation."""
        long_pattern = "a" * 1000
        # Should not raise even with very long pattern
        validate_pattern(long_pattern, use_regex=False)


class TestRedosPatternDetection:
    """Test detection of ReDoS patterns (nested quantifiers)."""

    def test_nested_plus_quantifiers_rejected(self) -> None:
        """Pattern (a+)+ should be rejected as ReDoS."""
        with pytest.raises(RegexValidationError) as exc_info:
            validate_pattern("(a+)+", use_regex=True)
        assert "nested quantifiers detected" in str(exc_info.value)

    def test_nested_star_with_plus_rejected(self) -> None:
        """Pattern (.*)+ should be rejected as ReDoS."""
        with pytest.raises(RegexValidationError) as exc_info:
            validate_pattern("(.*)+", use_regex=True)
        assert "nested quantifiers detected" in str(exc_info.value)

    def test_nested_plus_with_star_rejected(self) -> None:
        """Pattern (.+)* should be rejected as ReDoS."""
        with pytest.raises(RegexValidationError) as exc_info:
            validate_pattern("(.+)*", use_regex=True)
        assert "nested quantifiers detected" in str(exc_info.value)

    def test_non_capturing_group_with_nested_quantifiers_rejected(self) -> None:
        """Pattern (?:a+)+ should be rejected as ReDoS."""
        with pytest.raises(RegexValidationError) as exc_info:
            validate_pattern("(?:a+)+", use_regex=True)
        assert "nested quantifiers detected" in str(exc_info.value)

    def test_nested_star_quantifiers_rejected(self) -> None:
        """Pattern (a*)* should be rejected as ReDoS."""
        with pytest.raises(RegexValidationError) as exc_info:
            validate_pattern("(a*)*", use_regex=True)
        assert "nested quantifiers detected" in str(exc_info.value)

    def test_sequential_quantifiers_allowed(self) -> None:
        """Pattern a+b+ should be allowed (not nested)."""
        # Should not raise
        validate_pattern("a+b+", use_regex=True)

    def test_simple_star_quantifier_allowed(self) -> None:
        """Pattern .* should be allowed."""
        # Should not raise
        validate_pattern(".*", use_regex=True)

    def test_simple_plus_quantifier_allowed(self) -> None:
        """Pattern .+ should be allowed."""
        # Should not raise
        validate_pattern(".+", use_regex=True)

    def test_character_class_with_quantifier_allowed(self) -> None:
        """Pattern [a-z]+ should be allowed."""
        # Should not raise
        validate_pattern("[a-z]+", use_regex=True)

    def test_alternation_with_quantifiers_allowed(self) -> None:
        """Pattern (a|b)+ should be allowed (alternation, not nested quantifier)."""
        # Should not raise
        validate_pattern("(a|b)+", use_regex=True)

    def test_word_boundary_patterns_allowed(self) -> None:
        r"""Pattern \b\w+\b should be allowed."""
        # Should not raise
        validate_pattern(r"\b\w+\b", use_regex=True)

    def test_non_regex_mode_allows_redos_pattern(self) -> None:
        """Non-regex mode should allow ReDoS patterns (treated as literal)."""
        # Should not raise
        validate_pattern("(a+)+", use_regex=False)


class TestSyntaxValidation:
    """Test regex syntax validation."""

    def test_unclosed_bracket_rejected(self) -> None:
        """Pattern with unclosed bracket should be rejected."""
        with pytest.raises(RegexValidationError) as exc_info:
            validate_pattern("[invalid", use_regex=True)
        assert "Invalid regex syntax" in str(exc_info.value)

    def test_unclosed_parenthesis_rejected(self) -> None:
        """Pattern with unclosed parenthesis should be rejected."""
        with pytest.raises(RegexValidationError) as exc_info:
            validate_pattern("(unclosed", use_regex=True)
        assert "Invalid regex syntax" in str(exc_info.value)

    def test_invalid_escape_sequence_rejected(self) -> None:
        r"""Pattern with invalid escape should be rejected."""
        with pytest.raises(RegexValidationError) as exc_info:
            # \x without hex digits is invalid
            validate_pattern(r"\x", use_regex=True)
        assert "Invalid regex syntax" in str(exc_info.value)

    def test_invalid_quantifier_rejected(self) -> None:
        """Pattern with invalid quantifier should be rejected."""
        with pytest.raises(RegexValidationError) as exc_info:
            # {3,2} has min > max, which is invalid
            validate_pattern("a{3,2}", use_regex=True)
        assert "Invalid regex syntax" in str(exc_info.value)

    def test_valid_bracket_expression_passes(self) -> None:
        """Valid bracket expression should pass."""
        # Should not raise
        validate_pattern("[a-z]+", use_regex=True)

    def test_valid_grouped_pattern_passes(self) -> None:
        """Valid grouped pattern should pass."""
        # Should not raise
        validate_pattern("(foo|bar)+", use_regex=True)

    def test_valid_escaped_special_chars_passes(self) -> None:
        r"""Valid escaped special characters should pass."""
        # Should not raise
        validate_pattern(r"\.\*\+\?", use_regex=True)

    def test_non_regex_mode_allows_invalid_syntax(self) -> None:
        """Non-regex mode should allow invalid regex syntax (treated as literal)."""
        # Should not raise
        validate_pattern("[invalid", use_regex=False)


class TestNonRegexMode:
    """Test non-regex mode behavior."""

    def test_any_string_passes_in_non_regex_mode(self) -> None:
        """Any string should pass in non-regex mode."""
        # Should not raise
        validate_pattern("any string with special chars [(*)]", use_regex=False)

    def test_empty_string_passes_in_non_regex_mode(self) -> None:
        """Empty string should pass in non-regex mode."""
        # Should not raise
        validate_pattern("", use_regex=False)

    def test_empty_string_in_regex_mode_passes(self) -> None:
        """Empty string should pass in regex mode (valid empty pattern)."""
        # Should not raise - empty string is a valid regex
        validate_pattern("", use_regex=True)


class TestValidPatterns:
    """Test that valid patterns pass validation."""

    def test_email_pattern_passes(self) -> None:
        """Email-like pattern should pass."""
        # Should not raise
        validate_pattern(r"[\w.+-]+@[\w-]+\.[\w.-]+", use_regex=True)

    def test_url_pattern_passes(self) -> None:
        """URL-like pattern should pass."""
        # Should not raise
        validate_pattern(r"https?://[\w.-]+(?:/[\w./-]*)?", use_regex=True)

    def test_phone_pattern_passes(self) -> None:
        """Phone number pattern should pass."""
        # Should not raise
        validate_pattern(r"\d{3}[-.]?\d{3}[-.]?\d{4}", use_regex=True)

    def test_common_search_pattern_passes(self) -> None:
        """Common search patterns should pass."""
        # Should not raise
        validate_pattern(r"def\s+\w+\s*\(", use_regex=True)

    def test_lookahead_pattern_passes(self) -> None:
        """Lookahead pattern should pass."""
        # Should not raise
        validate_pattern(r"foo(?=bar)", use_regex=True)

    def test_lookbehind_pattern_passes(self) -> None:
        """Lookbehind pattern should pass."""
        # Should not raise
        validate_pattern(r"(?<=foo)bar", use_regex=True)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_pattern_with_all_quantifier_types(self) -> None:
        """Pattern with all quantifier types (non-nested) should pass."""
        # Should not raise - these are sequential, not nested
        validate_pattern("a+b*c?d{2}e{1,3}", use_regex=True)

    def test_deeply_nested_groups_without_quantifier_issue_passes(self) -> None:
        """Deeply nested groups without nested quantifiers should pass."""
        # Should not raise - nested groups, but no nested quantifiers
        validate_pattern("((a|b)|(c|d))+", use_regex=True)

    def test_unicode_pattern_passes(self) -> None:
        """Unicode pattern should pass."""
        # Should not raise
        validate_pattern(r"[\u0400-\u04FF]+", use_regex=True)

    def test_whitespace_only_pattern_passes(self) -> None:
        """Whitespace-only pattern should pass."""
        # Should not raise
        validate_pattern(r"\s+", use_regex=True)
