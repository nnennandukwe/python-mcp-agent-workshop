"""Cyclomatic and cognitive complexity calculators using Astroid."""

import astroid


class CyclomaticCalculator:
    """Calculates cyclomatic complexity for Python functions.

    Cyclomatic complexity counts the number of linearly independent paths
    through a function. Higher values indicate more complex branching logic.
    """

    def calculate(self, node: astroid.FunctionDef | astroid.AsyncFunctionDef) -> int:
        """Calculate cyclomatic complexity for a function node.

        Args:
            node: An Astroid FunctionDef or AsyncFunctionDef node.

        Returns:
            Cyclomatic complexity score (minimum 1).
        """
        complexity = 1  # Base complexity
        complexity += self._count_branches(node)
        return complexity

    def _count_branches(self, node: astroid.NodeNG) -> int:
        """Recursively count branching constructs."""
        count = 0
        for _child in node.nodes_of_class(
            (
                astroid.If,
                astroid.For,
                astroid.While,
                astroid.ExceptHandler,
                astroid.With,
                astroid.Assert,
                astroid.IfExp,
                astroid.Comprehension,
            )
        ):
            count += 1

        # Count boolean operators in conditions
        for bool_op in node.nodes_of_class(astroid.BoolOp):
            # Each 'and'/'or' adds a new path
            count += len(bool_op.values) - 1

        return count


class CognitiveCalculator:
    """Calculates cognitive complexity (Sonar's metric) for Python functions.

    Cognitive complexity measures how difficult code is to understand,
    applying nesting penalties for structures inside other structures.
    """

    def calculate(self, node: astroid.FunctionDef | astroid.AsyncFunctionDef) -> int:
        """Calculate cognitive complexity for a function node.

        Args:
            node: An Astroid FunctionDef or AsyncFunctionDef node.

        Returns:
            Cognitive complexity score (minimum 0).
        """
        return self._walk(node, nesting=0, func_name=node.name)

    def _walk(self, node: astroid.NodeNG, nesting: int, func_name: str) -> int:
        """Recursively walk the AST accumulating cognitive complexity."""
        total = 0

        for child in node.get_children():
            if isinstance(child, (astroid.FunctionDef, astroid.AsyncFunctionDef)):
                # Nested function definitions increase nesting
                total += self._walk(child, nesting + 1, func_name)
                continue

            # Increment for breaks in linear flow + nesting penalty
            if isinstance(child, astroid.If):
                total += 1 + nesting  # +1 for if + nesting penalty
                total += self._walk(child, nesting + 1, func_name)
                continue
            elif isinstance(child, (astroid.For, astroid.While)):
                total += 1 + nesting
                total += self._walk(child, nesting + 1, func_name)
                continue
            elif isinstance(child, astroid.ExceptHandler):
                total += 1 + nesting
                total += self._walk(child, nesting + 1, func_name)
                continue
            elif isinstance(child, astroid.With):
                total += 1 + nesting
                total += self._walk(child, nesting + 1, func_name)
                continue
            elif isinstance(child, astroid.IfExp):
                total += 1 + nesting
                total += self._walk(child, nesting, func_name)
                continue

            # Boolean operators: +1 for each sequence
            if isinstance(child, astroid.BoolOp):
                total += 1

            # Recursion: +1 when function calls itself
            if isinstance(child, astroid.Call):
                call_name = self._get_call_name(child)
                if call_name == func_name:
                    total += 1

            total += self._walk(child, nesting, func_name)

        return total

    @staticmethod
    def _get_call_name(node: astroid.Call) -> str | None:
        """Get the simple name of a function call."""
        if isinstance(node.func, astroid.Name):
            return node.func.name
        return None
