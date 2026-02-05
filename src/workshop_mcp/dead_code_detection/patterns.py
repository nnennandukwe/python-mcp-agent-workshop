"""Dead code pattern definitions and categories."""

from dataclasses import dataclass
from enum import Enum


class DeadCodeCategory(Enum):
    """Categories of dead code issues."""

    UNUSED_IMPORT = "unused_import"
    UNUSED_VARIABLE = "unused_variable"
    UNUSED_FUNCTION = "unused_function"
    UNUSED_PARAMETER = "unused_parameter"
    UNREACHABLE_CODE = "unreachable_code"
    REDUNDANT_CONDITION = "redundant_condition"


class Severity(Enum):
    """Severity levels for dead code issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class DeadCodeIssue:
    """Represents a detected dead code issue."""

    category: DeadCodeCategory
    severity: Severity
    message: str
    line: int
    name: str
    suggestion: str


# Decorators that indicate a function is used externally
EXTERNALLY_USED_DECORATORS = {
    "property",
    "staticmethod",
    "classmethod",
    "abstractmethod",
    "overload",
    "pytest.fixture",
    "fixture",
    "app.route",
    "router.get",
    "router.post",
    "router.put",
    "router.delete",
    "click.command",
    "celery.task",
}

# Parameters that are conventionally unused
IGNORED_PARAMETERS = {"self", "cls", "args", "kwargs"}
