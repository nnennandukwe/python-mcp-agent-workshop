"""Symbol usage and reference tracking for dead code detection."""

from dataclasses import dataclass, field

import astroid


@dataclass
class SymbolDefinition:
    """A symbol definition in the source code."""

    name: str
    line: int
    kind: str  # "import", "variable", "function", "parameter", "class"
    scope: str | None = None  # enclosing function name, or None for module-level


@dataclass
class UsageGraph:
    """Tracks symbol definitions and references in a module."""

    definitions: list[SymbolDefinition] = field(default_factory=list)
    references: set[str] = field(default_factory=set)
    all_exports: list[str] = field(default_factory=list)

    def is_referenced(self, name: str) -> bool:
        """Check if a symbol name appears in the set of references."""
        return name in self.references

    def is_in_all(self, name: str) -> bool:
        """Check if a symbol is listed in __all__."""
        return name in self.all_exports


def build_usage_graph(tree: astroid.Module) -> UsageGraph:
    """Build a usage graph from an Astroid module AST.

    Walks the AST to record all Name and Attribute references, then
    returns a UsageGraph with both definitions and references populated.

    Args:
        tree: Parsed Astroid module.

    Returns:
        Populated UsageGraph instance.
    """
    graph = UsageGraph()

    # Extract __all__ if defined
    _extract_all_exports(tree, graph)

    # Collect all name references (reads)
    _collect_references(tree, graph)

    return graph


def _extract_all_exports(tree: astroid.Module, graph: UsageGraph) -> None:
    """Extract names from __all__ assignment."""
    for node in tree.body:
        if isinstance(node, astroid.Assign):
            for target in node.targets:
                if isinstance(target, astroid.AssignName) and target.name == "__all__":
                    if isinstance(node.value, (astroid.List, astroid.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, astroid.Const) and isinstance(elt.value, str):
                                graph.all_exports.append(elt.value)


def _collect_references(node: astroid.NodeNG, graph: UsageGraph) -> None:
    """Recursively collect all Name references in the AST.

    Only collects Name nodes that represent reads (not definitions).
    Also collects the root of Attribute chains (e.g., 'os' in 'os.path.join').
    """
    # Name node in a read context (not assignment target)
    if isinstance(node, astroid.Name):
        # Only count as reference if it's not the target of an assignment
        parent = node.parent
        if isinstance(parent, astroid.Assign) and node in parent.targets:
            pass  # This is a definition, not a reference
        elif isinstance(parent, astroid.AugAssign) and node is parent.target:
            # AugAssign target is both read and write — count as reference
            graph.references.add(node.name)
        else:
            graph.references.add(node.name)

    # For attribute access like 'os.path.join', we still want 'os' as referenced
    elif isinstance(node, astroid.Attribute):
        # Walk down to the leftmost Name in the chain
        leftmost = node
        while isinstance(leftmost, astroid.Attribute):
            leftmost = leftmost.expr
        if isinstance(leftmost, astroid.Name):
            graph.references.add(leftmost.name)

    # Recurse into children
    for child in node.get_children():
        _collect_references(child, graph)
