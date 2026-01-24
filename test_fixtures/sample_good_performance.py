"""Sample file demonstrating performance best practices for E2E testing.

This file contains well-optimized code patterns that should NOT trigger
any performance warnings from the profiler.
"""

import asyncio
import json
from typing import AsyncIterator

# Using async libraries for I/O
try:
    import aiofiles
    import aiohttp
except ImportError:
    pass  # Optional dependencies for demonstration


# =============================================================================
# GOOD: Prefetched Queries (No N+1)
# =============================================================================
def get_all_book_authors_good():
    """Uses select_related to avoid N+1 queries."""
    # Prefetch author in a single query
    books = Book.objects.select_related("author").all()
    result = []
    for book in books:
        # No additional query - author is already loaded
        author_name = book.author.name
        result.append({"title": book.title, "author": author_name})
    return result


def get_users_with_orders_good(session):
    """SQLAlchemy with joinedload to avoid N+1."""
    from sqlalchemy.orm import joinedload

    users = session.query(User).options(joinedload(User.orders)).all()
    result = []
    for user in users:
        # Orders are already loaded via join
        orders = user.orders
        result.append({"user": user.name, "order_count": len(orders)})
    return result


# =============================================================================
# GOOD: Async I/O in Async Functions
# =============================================================================
async def fetch_data_good():
    """Properly async function using async I/O libraries."""
    # Async file I/O
    async with aiofiles.open("data.txt") as f:
        data = await f.read()

    # Async sleep
    await asyncio.sleep(1)

    # Async HTTP request
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.example.com/data") as response:
            json_data = await response.json()

    return data, json_data


async def process_items_async(items):
    """Async function that properly awaits async operations."""
    results = []
    for item in items:
        # Using async sleep instead of time.sleep
        await asyncio.sleep(0.01)
        results.append(item * 2)
    return results


# =============================================================================
# GOOD: Efficient String Building
# =============================================================================
def build_report_good(items):
    """Efficient string building using list and join."""
    parts = []
    for item in items:
        parts.append(f"Item: {item}")
        parts.append("  Status: processed")
    return "\n".join(parts)


def build_report_with_io(items):
    """Alternative: using StringIO for string building."""
    from io import StringIO

    buffer = StringIO()
    for item in items:
        buffer.write(f"Item: {item}\n")
        buffer.write("  Status: processed\n")
    return buffer.getvalue()


# =============================================================================
# GOOD: Reasonable Loop Nesting (2-3 levels)
# =============================================================================
def process_matrix_good(matrix_2d):
    """Acceptable nesting depth (2 levels)."""
    result = []
    for row in matrix_2d:
        for cell in row:
            result.append(cell * 2)
    return result


def process_with_comprehension(matrix_2d):
    """Using list comprehension for better readability."""
    return [cell * 2 for row in matrix_2d for cell in row]


# =============================================================================
# GOOD: Memory Efficient File Processing
# =============================================================================
def process_large_file_good(filepath):
    """Process file line by line without loading all into memory."""
    count = 0
    with open(filepath) as f:
        for line in f:  # Iterates line by line, memory efficient
            count += 1
    return count


def process_file_generator(filepath):
    """Generator-based file processing."""
    with open(filepath) as f:
        for line in f:
            yield line.strip()


async def process_large_file_async(filepath) -> AsyncIterator[str]:
    """Async file processing with streaming."""
    async with aiofiles.open(filepath) as f:
        async for line in f:
            yield line.strip()


# =============================================================================
# GOOD: Streaming JSON Processing
# =============================================================================
def process_large_json_streaming(filepath):
    """Process large JSON file using streaming parser."""
    try:
        import ijson

        with open(filepath, "rb") as f:
            # Stream parse JSON items
            for item in ijson.items(f, "items.item"):
                yield item
    except ImportError:
        # Fallback for when ijson isn't available
        pass


# =============================================================================
# GOOD: Clean Async Function with No Blocking
# =============================================================================
async def handle_request_good(request_id: int):
    """Well-structured async handler with no blocking calls."""
    # All I/O operations use async alternatives
    await asyncio.sleep(0.001)  # Simulated async work

    # Computation is fine in async (no I/O)
    result = sum(range(1000))

    return {"id": request_id, "result": result}


# =============================================================================
# GOOD: Batch Processing Instead of N+1
# =============================================================================
def get_user_stats_batch(user_ids):
    """Batch query instead of individual queries in loop."""
    # Single query to get all users
    users = User.objects.filter(id__in=user_ids).prefetch_related("orders")

    # Process without additional queries
    stats = {}
    for user in users:
        stats[user.id] = {
            "name": user.name,
            "order_count": len(user.orders.all()),
        }
    return stats


# =============================================================================
# GOOD: Simple synchronous code (no issues expected)
# =============================================================================
def calculate_total(items):
    """Simple synchronous function - no performance issues."""
    total = 0
    for item in items:
        total += item.price * item.quantity
    return total


def filter_active_users(users):
    """Simple filtering - no performance issues."""
    return [user for user in users if user.is_active]
