#!/usr/bin/env python3
"""
Example: Using the Performance Profiler Programmatically

This script demonstrates how to use the PerformanceChecker class
directly in your Python code.

Run with:
    poetry run python examples/programmatic_usage.py
"""

import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from workshop_mcp.performance_profiler import PerformanceChecker
from workshop_mcp.performance_profiler.patterns import IssueCategory, Severity


def analyze_file(file_path: str) -> None:
    """Analyze a file and print results."""
    print(f"\n{'=' * 60}")
    print(f"Analyzing: {file_path}")
    print("=" * 60)

    try:
        checker = PerformanceChecker(file_path=file_path)
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        return
    except SyntaxError as e:
        print(f"Error: Syntax error in file: {e}")
        return

    # Run all checks
    issues = checker.check_all()

    # Get summary
    summary = checker.get_summary()

    # Print summary
    print("\nSummary:")
    print(f"  Total issues: {summary['total_issues']}")
    print("  By severity:")
    print(f"    Critical: {summary['by_severity']['critical']}")
    print(f"    High:     {summary['by_severity']['high']}")
    print(f"    Medium:   {summary['by_severity']['medium']}")
    print(f"    Low:      {summary['by_severity']['low']}")

    # Print detailed issues
    if issues:
        print("\nDetailed Issues:")
        print("-" * 60)

        for i, issue in enumerate(issues, 1):
            severity_color = {
                Severity.CRITICAL: "\033[91m",  # Red
                Severity.HIGH: "\033[93m",  # Yellow
                Severity.MEDIUM: "\033[94m",  # Blue
                Severity.LOW: "\033[90m",  # Gray
            }.get(issue.severity, "")
            reset = "\033[0m"

            print(
                f"\n{i}. {severity_color}[{issue.severity.value.upper()}]{reset} "
                f"{issue.category.value}"
            )
            print(f"   Line {issue.line_number}: {issue.description}")
            print(f"   Function: {issue.function_name or 'N/A'}")
            print(f"   Suggestion: {issue.suggestion}")

            if issue.code_snippet:
                print(f"   Code: {issue.code_snippet.strip()}")
    else:
        print("\n✓ No performance issues found!")


def analyze_source_code() -> None:
    """Demonstrate analyzing source code directly."""
    print(f"\n{'=' * 60}")
    print("Analyzing source code string")
    print("=" * 60)

    source = '''
async def bad_example():
    """This async function has blocking I/O."""
    import time

    # This blocks the event loop!
    with open('data.txt') as f:
        data = f.read()

    # This also blocks!
    time.sleep(1)

    return data
'''

    checker = PerformanceChecker(source_code=source)
    issues = checker.check_all()

    print("\nSource code:")
    print("-" * 40)
    for i, line in enumerate(source.strip().split("\n"), 1):
        print(f"{i:3}: {line}")
    print("-" * 40)

    print(f"\nIssues found: {len(issues)}")
    for issue in issues:
        print(f"  [{issue.severity.value.upper()}] Line {issue.line_number}: {issue.description}")


def demonstrate_filtering() -> None:
    """Demonstrate filtering issues by severity and category."""
    print(f"\n{'=' * 60}")
    print("Demonstrating issue filtering")
    print("=" * 60)

    source = """
async def multiple_issues():
    for user in users:
        # N+1 query
        orders = user.orders.filter(active=True)

        # Blocking I/O
        with open('log.txt') as f:
            log = f.read()

        # String concat in loop
        result = ""
        for order in orders:
            result += str(order)
"""

    checker = PerformanceChecker(source_code=source)

    # Get all issues
    all_issues = checker.check_all()
    print(f"\nAll issues: {len(all_issues)}")

    # Filter by severity
    critical = checker.get_issues_by_severity(Severity.CRITICAL)
    high = checker.get_issues_by_severity(Severity.HIGH)
    print(f"Critical issues: {len(critical)}")
    print(f"High issues: {len(high)}")

    # Filter by category
    n_plus_one = checker.get_issues_by_category(IssueCategory.N_PLUS_ONE_QUERY)
    blocking_io = checker.get_issues_by_category(IssueCategory.BLOCKING_IO_IN_ASYNC)
    print(f"N+1 query issues: {len(n_plus_one)}")
    print(f"Blocking I/O issues: {len(blocking_io)}")

    # Quick checks
    print(f"\nHas any issues: {checker.has_issues()}")
    print(f"Has critical issues: {len(checker.get_critical_issues()) > 0}")


def main():
    """Run all examples."""
    print("Performance Profiler - Programmatic Usage Examples")
    print("=" * 60)

    # Get the examples directory
    examples_dir = os.path.dirname(os.path.abspath(__file__))

    # Analyze the bad_performance.py example
    bad_file = os.path.join(examples_dir, "bad_performance.py")
    if os.path.exists(bad_file):
        analyze_file(bad_file)
    else:
        print(f"\nNote: {bad_file} not found, skipping file analysis")

    # Analyze the good_performance.py example
    good_file = os.path.join(examples_dir, "good_performance.py")
    if os.path.exists(good_file):
        analyze_file(good_file)

    # Demonstrate source code analysis
    analyze_source_code()

    # Demonstrate filtering
    demonstrate_filtering()

    print(f"\n{'=' * 60}")
    print("Examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
