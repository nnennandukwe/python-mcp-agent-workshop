"""Astroid type inference utilities."""

import astroid


def infer_callable(node: astroid.NodeNG) -> str | None:
    """Try to infer the fully qualified name of a callable.

    Uses Astroid's inference engine to resolve what a function actually is,
    providing fully qualified names when possible.

    Args:
        node: An Astroid node representing a callable expression.

    Returns:
        Fully qualified name string, or None if inference fails.
    """
    try:
        inferred = next(node.infer(), None)
        if inferred and hasattr(inferred, "qname"):
            return inferred.qname()
    except (astroid.InferenceError, StopIteration):
        pass
    return None


def get_qualified_name(node: astroid.NodeNG) -> str | None:
    """Get the qualified name for an Astroid node if available.

    Args:
        node: An Astroid node.

    Returns:
        Qualified name string, or None if not available.
    """
    if hasattr(node, "qname"):
        try:
            return node.qname()
        except Exception:  # noqa: S110
            return None
    return None
