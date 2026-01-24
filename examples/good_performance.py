"""
Example: Code with Good Performance Practices

This file demonstrates the correct patterns that avoid the performance
issues detected by the Performance Profiler. Compare with bad_performance.py
to see the differences.

Running the profiler on this file should return 0 issues:

    from workshop_mcp.performance_profiler import PerformanceChecker
    checker = PerformanceChecker(file_path="examples/good_performance.py")
    print(f"Issues found: {len(checker.check_all())}")  # 0
"""

import asyncio
import json
from typing import AsyncIterator, Iterator, List

# Note: In real code, you'd import these:
# import aiofiles
# import aiohttp
# from django.db.models import Count, Q


# =============================================================================
# GOOD: Efficient Database Queries (No N+1)
# =============================================================================
def get_user_orders_good(user_queryset):
    """
    GOOD: Eager loading with prefetch/annotate.

    This makes 1-2 queries total, regardless of user count.
    Uses Django's annotate() to compute counts in the database.
    """
    # Hypothetical: User.objects.annotate(...)
    # This would be the actual code:
    # users = User.objects.annotate(
    #     pending_count=Count('orders', filter=Q(orders__status='pending'))
    # )

    # The key insight: NO queries inside the loop
    results = []
    for user in user_queryset:
        # Access pre-computed annotation, no extra query
        results.append({
            'user': user.name,
            'order_count': user.pending_count  # Already computed
        })
    return results


# =============================================================================
# GOOD: Non-Blocking Async I/O
# =============================================================================
async def fetch_config_good():
    """
    GOOD: Using async-safe I/O operations.

    aiofiles.open() and asyncio.sleep() don't block the event loop,
    allowing other coroutines to run while waiting for I/O.
    """
    # In real code with aiofiles:
    # async with aiofiles.open('config.json') as f:
    #     content = await f.read()
    #     config = json.loads(content)

    # Async sleep allows other tasks to run
    await asyncio.sleep(1)  # Non-blocking!

    # Simulated config for this example
    config = {"setting": "value"}
    return config


async def fetch_data_from_api_good(urls: List[str]) -> List[dict]:
    """
    GOOD: Concurrent async HTTP requests.

    Using aiohttp for non-blocking HTTP calls, and asyncio.gather()
    to run them concurrently.
    """
    # In real code:
    # async with aiohttp.ClientSession() as session:
    #     tasks = [fetch_url(session, url) for url in urls]
    #     return await asyncio.gather(*tasks)

    # Simulated for this example
    await asyncio.sleep(0.1)
    return [{"url": url, "data": "..."} for url in urls]


# =============================================================================
# GOOD: Efficient String Building
# =============================================================================
def build_report_good(items: List[dict]) -> str:
    """
    GOOD: Using list.append() + join().

    This is O(n) in memory allocations instead of O(n²).
    Each append is O(1) amortized, and join is O(n).
    """
    parts = []
    for item in items:
        parts.append(f"Item: {item['name']}, Value: {item['value']}")
    return "\n".join(parts)


def build_report_comprehension(items: List[dict]) -> str:
    """
    GOOD: Using list comprehension + join().

    Even more Pythonic and often faster due to optimizations.
    """
    return "\n".join(
        f"Item: {item['name']}, Value: {item['value']}"
        for item in items
    )


# =============================================================================
# GOOD: Memory-Efficient File Processing
# =============================================================================
def process_log_good(log_path: str) -> List[str]:
    """
    GOOD: Streaming file line-by-line.

    Iterating over a file object reads one line at a time,
    keeping memory usage constant regardless of file size.
    """
    errors = []
    with open(log_path) as f:
        for line in f:  # Streams line-by-line, O(1) memory
            if 'ERROR' in line:
                errors.append(line)
    return errors


def process_log_generator(log_path: str) -> Iterator[str]:
    """
    GOOD: Generator for lazy evaluation.

    Returns errors one at a time, useful when you don't need
    all results at once.
    """
    with open(log_path) as f:
        for line in f:
            if 'ERROR' in line:
                yield line


def process_large_json_good(json_path: str) -> Iterator[dict]:
    """
    GOOD: Streaming JSON parsing.

    For very large JSON files, use ijson to parse incrementally.
    This example shows the pattern (actual ijson import omitted).
    """
    # In real code with ijson:
    # import ijson
    # with open(json_path, 'rb') as f:
    #     for item in ijson.items(f, 'items.item'):
    #         yield item

    # Simulated for this example
    with open(json_path) as f:
        data = json.load(f)
        for item in data.get('items', []):
            yield item


# =============================================================================
# GOOD: Efficient Algorithms
# =============================================================================
def find_triplets_good(numbers: List[int], target: int) -> List[tuple]:
    """
    GOOD: O(n²) two-pointer algorithm.

    Instead of O(n³) brute force, we sort and use two pointers.
    For 1000 numbers: 1M operations instead of 1B.
    """
    numbers = sorted(numbers)  # O(n log n)
    triplets = []

    for i, num in enumerate(numbers):
        # Skip duplicates
        if i > 0 and num == numbers[i - 1]:
            continue

        # Two-pointer search for remaining sum
        left, right = i + 1, len(numbers) - 1

        while left < right:
            total = num + numbers[left] + numbers[right]

            if total == target:
                triplets.append((num, numbers[left], numbers[right]))
                left += 1
                # Skip duplicates
                while left < right and numbers[left] == numbers[left - 1]:
                    left += 1
            elif total < target:
                left += 1
            else:
                right -= 1

    return triplets


def find_pair_with_sum(numbers: List[int], target: int) -> tuple:
    """
    GOOD: O(n) hash-based lookup.

    Instead of O(n²) nested loops, use a set for O(1) lookups.
    """
    seen = set()
    for num in numbers:
        complement = target - num
        if complement in seen:
            return (complement, num)
        seen.add(num)
    return None


# =============================================================================
# GOOD: Complete Async Example
# =============================================================================
async def process_users_good(users):
    """
    GOOD: Proper async patterns combined.

    This function:
    1. Uses pre-fetched data (no N+1)
    2. Uses async sleep (non-blocking)
    3. Uses list + join (efficient strings)
    4. Uses async file I/O (non-blocking)
    """
    parts = []

    for user in users:
        # Assume profile was prefetch_related
        profile = user.profile  # No query, already loaded

        # Non-blocking delay
        await asyncio.sleep(0.1)

        # Efficient string building
        parts.append(f"User: {user.name}, Email: {profile.email}")

    report = "\n".join(parts)

    # In real code with aiofiles:
    # async with aiofiles.open('report.txt', 'w') as f:
    #     await f.write(report)

    return report


if __name__ == "__main__":
    print("This file demonstrates good performance practices.")
    print("Run the performance profiler to verify no issues:")
    print()
    print("  from workshop_mcp.performance_profiler import PerformanceChecker")
    print("  checker = PerformanceChecker(file_path='examples/good_performance.py')")
    print("  print(f'Issues: {len(checker.check_all())}')")
