"""Sample file with a mix of good and bad performance patterns.

This file tests that the profiler correctly identifies issues while
not flagging well-written code.
"""

import asyncio
import time


# =============================================================================
# GOOD: Simple synchronous functions
# =============================================================================
def calculate_sum(numbers):
    """Simple function - no issues expected."""
    return sum(numbers)


def filter_positives(numbers):
    """List comprehension - efficient pattern."""
    return [n for n in numbers if n > 0]


# =============================================================================
# BAD: Blocking I/O in async
# =============================================================================
async def mixed_async_function():
    """Async function with one blocking call."""
    # Good: using asyncio.sleep
    await asyncio.sleep(0.1)

    # Bad: blocking sleep in async context
    time.sleep(0.1)  # This should be flagged!

    # Good: pure computation
    result = sum(range(100))

    return result


# =============================================================================
# GOOD: Proper async function
# =============================================================================
async def proper_async_function():
    """Fully async function with no blocking calls."""
    await asyncio.sleep(0.1)
    result = await some_async_operation()
    return result


async def some_async_operation():
    """Helper async function."""
    await asyncio.sleep(0.01)
    return 42


# =============================================================================
# BAD: String concatenation in loop (but only one issue)
# =============================================================================
def build_message(names):
    """Function with inefficient string building."""
    message = "Hello to: "
    for name in names:
        message = message + name + ", "  # Inefficient!
    return message.rstrip(", ")


# =============================================================================
# GOOD: Efficient alternative
# =============================================================================
def build_message_good(names):
    """Efficient string building."""
    return "Hello to: " + ", ".join(names)


# =============================================================================
# Neutral: Simple loops that are fine
# =============================================================================
def process_items(items):
    """Simple loop - no issues."""
    results = []
    for item in items:
        results.append(item.upper())
    return results


def nested_but_shallow(matrix):
    """Two levels of nesting is acceptable."""
    total = 0
    for row in matrix:
        for cell in row:
            total += cell
    return total
