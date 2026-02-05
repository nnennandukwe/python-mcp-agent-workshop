"""Complexity categories, thresholds, and severity mapping."""

from enum import Enum


class ComplexityCategory(Enum):
    """Categories of complexity issues."""

    HIGH_CYCLOMATIC_COMPLEXITY = "high_cyclomatic_complexity"
    HIGH_COGNITIVE_COMPLEXITY = "high_cognitive_complexity"
    LONG_FUNCTION = "long_function"
    TOO_MANY_PARAMETERS = "too_many_parameters"
    DEEP_NESTING = "deep_nesting"
    LARGE_CLASS = "large_class"
    DEEP_INHERITANCE = "deep_inheritance"


# Cyclomatic complexity thresholds
CYCLOMATIC_SIMPLE = 10
CYCLOMATIC_MODERATE = 20
CYCLOMATIC_HIGH = 50

# Default thresholds
DEFAULT_CYCLOMATIC_THRESHOLD = 10
DEFAULT_COGNITIVE_THRESHOLD = 15
DEFAULT_MAX_FUNCTION_LENGTH = 50
DEFAULT_MAX_PARAMETERS = 5
DEFAULT_MAX_NESTING_DEPTH = 4
DEFAULT_MAX_CLASS_METHODS = 20
DEFAULT_MAX_INHERITANCE_DEPTH = 3


def cyclomatic_label(score: int) -> str:
    """Return a human-readable label for a cyclomatic complexity score.

    Args:
        score: Cyclomatic complexity value.

    Returns:
        One of 'simple', 'moderate', 'high', or 'very high'.
    """
    if score <= CYCLOMATIC_SIMPLE:
        return "simple"
    if score <= CYCLOMATIC_MODERATE:
        return "moderate"
    if score <= CYCLOMATIC_HIGH:
        return "high"
    return "very high"


def severity_for_cyclomatic(score: int, threshold: int) -> str:
    """Return severity string based on how far above threshold.

    Args:
        score: Cyclomatic complexity value.
        threshold: Configured threshold.

    Returns:
        Severity string: 'info', 'warning', 'error', or 'critical'.
    """
    if score <= threshold:
        return "info"
    if score <= CYCLOMATIC_MODERATE:
        return "warning"
    if score <= CYCLOMATIC_HIGH:
        return "error"
    return "critical"


def severity_for_cognitive(score: int, threshold: int) -> str:
    """Return severity string for cognitive complexity.

    Args:
        score: Cognitive complexity value.
        threshold: Configured threshold.

    Returns:
        Severity string.
    """
    if score <= threshold:
        return "info"
    ratio = score / max(threshold, 1)
    if ratio <= 2.0:
        return "warning"
    if ratio <= 3.0:
        return "error"
    return "critical"
