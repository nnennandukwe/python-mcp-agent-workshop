"""Pythonic anti-pattern definitions and detection rules."""

from dataclasses import dataclass
from enum import Enum


class Severity(Enum):
    """Severity levels for Pythonic issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class IssueCategory(Enum):
    """Categories of Pythonic issues."""

    NON_IDIOMATIC_LOOP = "non_idiomatic_loop"
    NON_IDIOMATIC_COMPARISON = "non_idiomatic_comparison"
    MISSING_CONTEXT_MANAGER = "missing_context_manager"
    INEFFICIENT_COLLECTION_BUILDING = "inefficient_collection_building"
    MUTABLE_DEFAULT_ARGUMENT = "mutable_default_argument"
    REDUNDANT_CODE = "redundant_code"
    NON_IDIOMATIC_EXCEPTION = "non_idiomatic_exception"


@dataclass
class PythonicIssue:
    """Represents a detected Pythonic issue."""

    tool: str
    category: IssueCategory
    severity: Severity
    message: str
    line: int
    column: int
    suggestion: str
    code_snippet: str | None = None
    end_line: int | None = None


# Loop patterns that should use enumerate()
RANGE_LEN_PATTERN_MSG = "Use enumerate() instead of range(len())"
RANGE_LEN_SUGGESTION = "for i, item in enumerate({iterable}):"

# Loop patterns that should use direct iteration
DICT_KEYS_ITERATION_MSG = "Iterate directly over dict instead of .keys()"
DICT_KEYS_SUGGESTION = "for key in {dict_name}:"

# Loop patterns that should use zip()
PARALLEL_ITERATION_MSG = "Use zip() for parallel iteration"
PARALLEL_ITERATION_SUGGESTION = "for x, y in zip({iter1}, {iter2}):"

# Comparison patterns
EQUALITY_NONE_MSG = "Use 'is None' instead of '== None'"
EQUALITY_NONE_SUGGESTION = "if x is None:"

INEQUALITY_NONE_MSG = "Use 'is not None' instead of '!= None'"
INEQUALITY_NONE_SUGGESTION = "if x is not None:"

EQUALITY_TRUE_MSG = "Simplify boolean comparison"
EQUALITY_TRUE_SUGGESTION = "if x:"

EQUALITY_FALSE_MSG = "Simplify boolean comparison"
EQUALITY_FALSE_SUGGESTION = "if not x:"

TYPE_COMPARISON_MSG = "Use isinstance() instead of type() comparison"
TYPE_COMPARISON_SUGGESTION = "isinstance(x, SomeClass)"

LEN_ZERO_CHECK_MSG = "Use truthiness test instead of len() == 0"
LEN_ZERO_SUGGESTION = "if not items:"

LEN_NONZERO_CHECK_MSG = "Use truthiness test instead of len() > 0"
LEN_NONZERO_SUGGESTION = "if items:"

# Context manager patterns
OPEN_WITHOUT_WITH_MSG = "Use 'with' statement for file operations"
OPEN_WITHOUT_WITH_SUGGESTION = "with open(filename) as f:"

# Collection building patterns
APPEND_IN_LOOP_MSG = "Consider using a list comprehension"
APPEND_IN_LOOP_SUGGESTION = "[f(x) for x in iterable]"

STRING_CONCAT_IN_LOOP_MSG = "Use str.join() instead of string concatenation in loop"
STRING_CONCAT_IN_LOOP_SUGGESTION = "''.join(parts)"

DICT_SETITEM_IN_LOOP_MSG = "Consider using a dict comprehension"
DICT_SETITEM_IN_LOOP_SUGGESTION = "{k: v for k, v in items}"

# Mutable default argument patterns
MUTABLE_DEFAULT_LIST_MSG = "Avoid mutable default argument (list)"
MUTABLE_DEFAULT_LIST_SUGGESTION = "def foo(items=None): items = items or []"

MUTABLE_DEFAULT_DICT_MSG = "Avoid mutable default argument (dict)"
MUTABLE_DEFAULT_DICT_SUGGESTION = "def foo(d=None): d = d or {}"

MUTABLE_DEFAULT_SET_MSG = "Avoid mutable default argument (set)"
MUTABLE_DEFAULT_SET_SUGGESTION = "def foo(s=None): s = s or set()"

# Redundant code patterns
REDUNDANT_BOOL_RETURN_MSG = "Simplify boolean return"
REDUNDANT_BOOL_RETURN_SUGGESTION = "return condition"

UNNECESSARY_LAMBDA_MSG = "Unnecessary lambda wrapper"
UNNECESSARY_LAMBDA_SUGGESTION = "Just use the function directly"

# Exception patterns
BARE_EXCEPT_MSG = "Avoid bare 'except:' clause"
BARE_EXCEPT_SUGGESTION = "except Exception:"

RERAISE_WITHOUT_FROM_MSG = "Use 'raise ... from' to preserve exception context"
RERAISE_WITHOUT_FROM_SUGGESTION = "raise NewException() from original_exc"
