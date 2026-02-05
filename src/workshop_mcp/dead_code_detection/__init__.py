"""Dead code detection tools for identifying unused Python code."""

__version__ = "0.1.0"

from .detector import DeadCodeDetector, DeadCodeResult, DeadCodeSummary, detect_dead_code
from .patterns import DeadCodeCategory, DeadCodeIssue
from .usage_graph import UsageGraph, build_usage_graph

__all__ = [
    "DeadCodeCategory",
    "DeadCodeDetector",
    "DeadCodeIssue",
    "DeadCodeResult",
    "DeadCodeSummary",
    "UsageGraph",
    "build_usage_graph",
    "detect_dead_code",
]
