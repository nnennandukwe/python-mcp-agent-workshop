"""
Example: Code with Performance Anti-Patterns

This file demonstrates common performance issues that the
Performance Profiler can detect. Run the profiler on this file
to see the analysis:

    poetry run python examples/programmatic_usage.py

Each anti-pattern is annotated with comments explaining the issue.
"""

import json
import time
from typing import List


# =============================================================================
# ISSUE 1: N+1 Query (Django ORM Example)
# Severity: HIGH
# =============================================================================
def get_user_orders_bad(users):
    """
    BAD: N+1 query pattern.

    This makes 1 query to get users, then N queries to get each user's orders.
    With 1000 users, that's 1001 database queries!
    """
    results = []
    for user in users:
        # This triggers a new database query for each user
        orders = user.orders.filter(status='pending')  # N+1 query!
        results.append({
            'user': user.name,
            'order_count': orders.count()
        })
    return results


# FIX: Use prefetch_related or annotate
# def get_user_orders_good(users):
#     users = User.objects.annotate(
#         pending_count=Count('orders', filter=Q(orders__status='pending'))
#     )
#     return [{'user': u.name, 'order_count': u.pending_count} for u in users]


# =============================================================================
# ISSUE 2: Blocking I/O in Async Function
# Severity: CRITICAL
# =============================================================================
async def fetch_config_bad():
    """
    BAD: Blocking I/O in async function.

    Using open() and time.sleep() in an async function blocks the
    entire event loop, defeating the purpose of async/await.
    """
    # This blocks the event loop while reading!
    with open('config.json') as f:  # Blocking I/O!
        config = json.load(f)

    # This blocks all other coroutines!
    time.sleep(1)  # Blocking sleep!

    return config


# FIX: Use async alternatives
# async def fetch_config_good():
#     async with aiofiles.open('config.json') as f:
#         content = await f.read()
#         config = json.loads(content)
#     await asyncio.sleep(1)
#     return config


# =============================================================================
# ISSUE 3: Inefficient String Concatenation in Loop
# Severity: MEDIUM
# =============================================================================
def build_report_bad(items: List[dict]) -> str:
    """
    BAD: String concatenation in loop.

    Each += creates a new string object, copying all previous content.
    With 1000 items, this is O(n²) in memory allocations.
    """
    report = ""
    for item in items:
        # Each concatenation creates a new string!
        report += f"Item: {item['name']}, Value: {item['value']}\n"
    return report


# FIX: Use list and join
# def build_report_good(items: List[dict]) -> str:
#     parts = []
#     for item in items:
#         parts.append(f"Item: {item['name']}, Value: {item['value']}")
#     return "\n".join(parts)


# =============================================================================
# ISSUE 4: Memory Inefficiency - Loading Entire File
# Severity: MEDIUM
# =============================================================================
def process_log_bad(log_path: str) -> List[str]:
    """
    BAD: Loading entire file into memory.

    readlines() loads the entire file into a list. For a 1GB log file,
    this could crash your process with an OutOfMemoryError.
    """
    errors = []
    with open(log_path) as f:
        # Loads entire file into memory!
        lines = f.readlines()

    for line in lines:
        if 'ERROR' in line:
            errors.append(line)
    return errors


# FIX: Iterate over file object directly
# def process_log_good(log_path: str) -> List[str]:
#     errors = []
#     with open(log_path) as f:
#         for line in f:  # Streams line-by-line
#             if 'ERROR' in line:
#                 errors.append(line)
#     return errors


# =============================================================================
# ISSUE 5: Deeply Nested Loops
# Severity: MEDIUM
# =============================================================================
def find_triplets_bad(numbers: List[int], target: int) -> List[tuple]:
    """
    BAD: O(n³) algorithm with deeply nested loops.

    For 1000 numbers, this executes 1 billion iterations.
    Consider using better algorithms or data structures.
    """
    triplets = []
    for i in range(len(numbers)):
        for j in range(len(numbers)):
            for k in range(len(numbers)):  # Deeply nested!
                if numbers[i] + numbers[j] + numbers[k] == target:
                    triplets.append((numbers[i], numbers[j], numbers[k]))
    return triplets


# FIX: Use two-pointer technique or hash set
# def find_triplets_good(numbers: List[int], target: int) -> List[tuple]:
#     numbers.sort()
#     triplets = []
#     for i, num in enumerate(numbers):
#         left, right = i + 1, len(numbers) - 1
#         while left < right:
#             total = num + numbers[left] + numbers[right]
#             if total == target:
#                 triplets.append((num, numbers[left], numbers[right]))
#                 left += 1
#             elif total < target:
#                 left += 1
#             else:
#                 right -= 1
#     return triplets  # O(n²) instead of O(n³)


# =============================================================================
# Combined Example: Multiple Issues in One Function
# =============================================================================
async def process_users_bad(users):
    """
    BAD: Multiple performance issues in one function.

    This function has:
    1. N+1 query (HIGH)
    2. Blocking I/O in async (CRITICAL)
    3. String concatenation in loop (MEDIUM)
    """
    report = ""

    for user in users:
        # Issue 1: N+1 query
        profile = user.profile.get()

        # Issue 2: Blocking sleep in async
        time.sleep(0.1)

        # Issue 3: String concatenation
        report += f"User: {user.name}, Email: {profile.email}\n"

    # Issue 2: Blocking file I/O in async
    with open('report.txt', 'w') as f:
        f.write(report)

    return report


if __name__ == "__main__":
    print("This file contains intentionally bad code for demonstration.")
    print("Run the performance profiler to analyze it:")
    print("  poetry run python examples/programmatic_usage.py")
