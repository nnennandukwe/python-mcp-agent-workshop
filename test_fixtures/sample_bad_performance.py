"""Sample file with known performance anti-patterns for E2E testing.

This file contains intentional performance issues for testing the
performance profiler's detection capabilities. Each section is labeled
with the expected issue category.
"""

import json
import pickle
import time
import requests
from django.db import models


# =============================================================================
# ISSUE 1: N+1 Query Pattern (Django ORM in loop)
# Expected: HIGH severity, n_plus_one_query category
# =============================================================================
class Author(models.Model):
    name = models.CharField(max_length=100)


class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)


def get_all_book_authors_bad():
    """N+1 query: fetches author for each book in a loop."""
    books = Book.objects.all()
    result = []
    for book in books:
        # This triggers a separate query for each book's author
        author_name = book.author.name  # N+1 query here!
        result.append({"title": book.title, "author": author_name})
    return result


# =============================================================================
# ISSUE 2: Blocking I/O in Async Function
# Expected: CRITICAL severity, blocking_io_in_async category
# =============================================================================
async def fetch_data_bad():
    """Async function with blocking I/O calls."""
    # Blocking file I/O in async context
    with open("data.txt") as f:  # Blocking!
        data = f.read()

    # Blocking sleep in async context
    time.sleep(1)  # Blocking!

    # Blocking HTTP request in async context
    response = requests.get("https://api.example.com/data")  # Blocking!

    return data, response.json()


# =============================================================================
# ISSUE 3: Inefficient Loop - String Concatenation
# Expected: MEDIUM severity, inefficient_loop category
# =============================================================================
def build_report_bad(items):
    """Inefficient string building using concatenation in loop."""
    report = ""
    for item in items:
        # String concatenation in loop creates new string objects
        report = report + f"Item: {item}\n"  # Inefficient!
        report += f"  Status: processed\n"  # Also inefficient!
    return report


# =============================================================================
# ISSUE 4: Deeply Nested Loops
# Expected: MEDIUM severity, inefficient_loop category
# =============================================================================
def process_matrix_bad(matrix_3d):
    """Deeply nested loop structure (4 levels)."""
    result = []
    for layer in matrix_3d:
        for row in layer:
            for cell in row:
                for value in cell:
                    # 4 levels of nesting is a code smell
                    result.append(value * 2)
    return result


# =============================================================================
# ISSUE 5: Memory Inefficiency - Loading Entire File
# Expected: MEDIUM severity, memory_inefficiency category
# =============================================================================
def process_large_file_bad(filepath):
    """Loads entire file into memory at once."""
    with open(filepath) as f:
        # Reading entire file into memory
        content = f.read()  # Memory inefficient for large files!

    lines = content.split("\n")
    return len(lines)


def process_file_readlines_bad(filepath):
    """Uses readlines() which loads all lines into memory."""
    with open(filepath) as f:
        # Loads all lines into a list
        lines = f.readlines()  # Memory inefficient!
    return [line.strip() for line in lines]


# =============================================================================
# ISSUE 6: Memory Inefficiency - JSON/Pickle Load
# Expected: MEDIUM severity, memory_inefficiency category
# =============================================================================
def load_large_json_bad(filepath):
    """Loads entire JSON file into memory."""
    with open(filepath) as f:
        # For very large JSON files, this can exhaust memory
        data = json.load(f)  # Memory inefficient for large files!
    return data


def load_pickle_bad(filepath):
    """Loads pickle file which can be memory intensive."""
    with open(filepath, "rb") as f:
        # Pickle files can be very large
        data = pickle.load(f)  # Memory inefficient!
    return data


# =============================================================================
# ISSUE 7: SQLAlchemy N+1 Pattern
# Expected: HIGH severity, n_plus_one_query category
# =============================================================================
def get_users_with_orders_bad(session):
    """SQLAlchemy N+1 query pattern."""
    users = session.query(User).all()
    result = []
    for user in users:
        # This triggers a lazy load for each user
        orders = user.orders  # N+1 query!
        result.append({"user": user.name, "order_count": len(orders)})
    return result


# =============================================================================
# Multiple issues in one function
# =============================================================================
async def process_users_very_bad(session):
    """Function with multiple performance issues."""
    users = session.query(User).all()
    report = ""

    for user in users:
        # N+1 query
        orders = user.orders

        # String concatenation in loop
        report = report + f"User: {user.name}\n"

        # Blocking I/O in async
        time.sleep(0.1)

        for order in orders:
            report += f"  Order: {order.id}\n"

    # Blocking file write in async
    with open("report.txt", "w") as f:
        f.write(report)

    return report
