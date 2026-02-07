"""Tests for the Pythonic code checker."""

import pytest

from workshop_mcp.pythonic_check import IssueCategory, PythonicChecker, Severity


class TestRangeLenPattern:
    """Tests for range(len()) detection."""

    def test_detects_range_len(self):
        """Should detect for i in range(len(items)) pattern."""
        code = """
items = [1, 2, 3]
for i in range(len(items)):
    print(items[i])
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        assert len(issues) == 1
        assert issues[0].category == IssueCategory.NON_IDIOMATIC_LOOP
        assert "enumerate" in issues[0].message.lower()

    def test_ignores_plain_range(self):
        """Should not flag plain range() usage."""
        code = """
for i in range(10):
    print(i)
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        # Filter for loop issues only
        loop_issues = [i for i in issues if i.category == IssueCategory.NON_IDIOMATIC_LOOP]
        assert len(loop_issues) == 0


class TestDictKeysIteration:
    """Tests for dict.keys() iteration detection."""

    def test_detects_dict_keys(self):
        """Should detect for key in d.keys() pattern."""
        code = """
d = {"a": 1}
for key in d.keys():
    print(key)
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        loop_issues = [i for i in issues if i.category == IssueCategory.NON_IDIOMATIC_LOOP]
        assert len(loop_issues) == 1
        assert "keys" in loop_issues[0].message.lower()

    def test_ignores_direct_dict_iteration(self):
        """Should not flag direct dict iteration."""
        code = """
d = {"a": 1}
for key in d:
    print(key)
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        loop_issues = [i for i in issues if i.category == IssueCategory.NON_IDIOMATIC_LOOP]
        assert len(loop_issues) == 0


class TestNoneComparison:
    """Tests for None comparison detection."""

    def test_detects_equality_none(self):
        """Should detect x == None pattern."""
        code = """
x = None
if x == None:
    pass
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        none_issues = [i for i in issues if "None" in i.message]
        assert len(none_issues) == 1
        assert "is None" in none_issues[0].suggestion

    def test_detects_inequality_none(self):
        """Should detect x != None pattern."""
        code = """
x = None
if x != None:
    pass
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        none_issues = [i for i in issues if "None" in i.message]
        assert len(none_issues) == 1
        assert "is not None" in none_issues[0].suggestion

    def test_ignores_is_none(self):
        """Should not flag x is None."""
        code = """
x = None
if x is None:
    pass
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        none_issues = [i for i in issues if "None" in i.message]
        assert len(none_issues) == 0


class TestBoolComparison:
    """Tests for boolean comparison detection."""

    def test_detects_equality_true(self):
        """Should detect x == True pattern."""
        code = """
x = True
if x == True:
    pass
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        bool_issues = [i for i in issues if "boolean" in i.message.lower()]
        assert len(bool_issues) == 1

    def test_detects_equality_false(self):
        """Should detect x == False pattern."""
        code = """
x = False
if x == False:
    pass
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        bool_issues = [i for i in issues if "boolean" in i.message.lower()]
        assert len(bool_issues) == 1

    def test_ignores_truthiness_test(self):
        """Should not flag if x: or if not x:."""
        code = """
x = True
if x:
    pass
if not x:
    pass
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        bool_issues = [i for i in issues if "boolean" in i.message.lower()]
        assert len(bool_issues) == 0


class TestTypeComparison:
    """Tests for type() comparison detection."""

    def test_detects_type_equality(self):
        """Should detect type(x) == SomeClass pattern."""
        code = """
class MyClass:
    pass

x = MyClass()
if type(x) == MyClass:
    pass
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        type_issues = [i for i in issues if "isinstance" in i.message.lower()]
        assert len(type_issues) == 1

    def test_ignores_isinstance(self):
        """Should not flag isinstance() usage."""
        code = """
class MyClass:
    pass

x = MyClass()
if isinstance(x, MyClass):
    pass
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        type_issues = [i for i in issues if "isinstance" in i.message.lower()]
        assert len(type_issues) == 0


class TestLenComparison:
    """Tests for len() comparison detection."""

    def test_detects_len_zero(self):
        """Should detect len(x) == 0 pattern."""
        code = """
items = []
if len(items) == 0:
    pass
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        len_issues = [i for i in issues if "len" in i.message.lower()]
        assert len(len_issues) == 1
        assert "not items" in len_issues[0].suggestion

    def test_detects_len_greater_zero(self):
        """Should detect len(x) > 0 pattern."""
        code = """
items = []
if len(items) > 0:
    pass
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        len_issues = [i for i in issues if "len" in i.message.lower()]
        assert len(len_issues) == 1
        assert "if items" in len_issues[0].suggestion

    def test_ignores_truthiness(self):
        """Should not flag if items: or if not items:."""
        code = """
items = []
if items:
    pass
if not items:
    pass
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        len_issues = [i for i in issues if "len" in i.message.lower()]
        assert len(len_issues) == 0


class TestMutableDefaults:
    """Tests for mutable default argument detection."""

    def test_detects_list_default(self):
        """Should detect def foo(items=[]) pattern."""
        code = """
def foo(items=[]):
    return items
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        mutable_issues = [i for i in issues if i.category == IssueCategory.MUTABLE_DEFAULT_ARGUMENT]
        assert len(mutable_issues) == 1
        assert mutable_issues[0].severity == Severity.ERROR

    def test_detects_dict_default(self):
        """Should detect def foo(d={}) pattern."""
        code = """
def foo(d={}):
    return d
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        mutable_issues = [i for i in issues if i.category == IssueCategory.MUTABLE_DEFAULT_ARGUMENT]
        assert len(mutable_issues) == 1

    def test_detects_set_default(self):
        """Should detect def foo(s=set()) pattern - but set() is a call not literal."""
        # Note: set literals like {1, 2} would be detected
        code = """
def foo(s={1, 2}):
    return s
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        mutable_issues = [i for i in issues if i.category == IssueCategory.MUTABLE_DEFAULT_ARGUMENT]
        assert len(mutable_issues) == 1

    def test_ignores_none_default(self):
        """Should not flag def foo(items=None) pattern."""
        code = """
def foo(items=None):
    items = items or []
    return items
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        mutable_issues = [i for i in issues if i.category == IssueCategory.MUTABLE_DEFAULT_ARGUMENT]
        assert len(mutable_issues) == 0


class TestCollectionBuilding:
    """Tests for collection building pattern detection."""

    def test_detects_append_in_loop(self):
        """Should detect list.append() in loop."""
        code = """
result = []
for x in range(10):
    result.append(x * 2)
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        append_issues = [i for i in issues if "comprehension" in i.message.lower()]
        assert len(append_issues) == 1

    def test_detects_dict_setitem_in_loop(self):
        """Should detect dict[key] = value in loop."""
        code = """
result = {}
for x in range(10):
    result[x] = x * 2
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        dict_issues = [i for i in issues if "dict comprehension" in i.message.lower()]
        assert len(dict_issues) == 1


class TestRedundantCode:
    """Tests for redundant code detection."""

    def test_detects_redundant_bool_return_true_false(self):
        """Should detect if x: return True else: return False."""
        code = """
def is_positive(x):
    if x > 0:
        return True
    else:
        return False
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        redundant_issues = [i for i in issues if i.category == IssueCategory.REDUNDANT_CODE]
        assert len(redundant_issues) == 1
        assert "return condition" in redundant_issues[0].suggestion

    def test_detects_redundant_bool_return_false_true(self):
        """Should detect if x: return False else: return True."""
        code = """
def is_negative(x):
    if x > 0:
        return False
    else:
        return True
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        redundant_issues = [i for i in issues if i.category == IssueCategory.REDUNDANT_CODE]
        assert len(redundant_issues) == 1
        assert "not" in redundant_issues[0].suggestion


class TestExceptionPatterns:
    """Tests for exception pattern detection."""

    def test_detects_bare_except(self):
        """Should detect bare except: clause."""
        code = """
try:
    risky_operation()
except:
    pass
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        except_issues = [i for i in issues if i.category == IssueCategory.NON_IDIOMATIC_EXCEPTION]
        assert len(except_issues) == 1
        assert "bare" in except_issues[0].message.lower()

    def test_ignores_specific_exception(self):
        """Should not flag except Exception:."""
        code = """
try:
    risky_operation()
except Exception:
    pass
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        except_issues = [i for i in issues if i.category == IssueCategory.NON_IDIOMATIC_EXCEPTION]
        assert len(except_issues) == 0


class TestSummary:
    """Tests for the summary functionality."""

    def test_summary_counts(self):
        """Should return correct issue counts in summary."""
        code = """
def foo(items=[]):
    for i in range(len(items)):
        if items[i] == None:
            pass
"""
        checker = PythonicChecker(source_code=code)
        checker.check_all()
        summary = checker.get_summary()

        assert summary["total_issues"] >= 3
        assert "by_category" in summary


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_file(self):
        """Should handle empty file."""
        code = ""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        assert issues == []

    def test_syntax_error(self):
        """Should raise SyntaxError for invalid code."""
        code = "def foo(:"

        with pytest.raises(SyntaxError):
            PythonicChecker(source_code=code)

    def test_no_issues_in_clean_code(self):
        """Should find no issues in Pythonic code."""
        code = """
def process_items(items=None):
    items = items or []
    return [x * 2 for x in items]

def check_value(x):
    if x is None:
        return False
    return bool(x)

def iterate_dict(d):
    for key in d:
        print(key)
"""
        checker = PythonicChecker(source_code=code)
        issues = checker.check_all()

        assert len(issues) == 0
