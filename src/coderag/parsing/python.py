from dataclasses import dataclass

import tree_sitter_python
from tree_sitter import Language, Node, Parser, Tree

# Built once at import time; Parser objects are cheap and not thread-safe, so
# parse() makes a fresh one per call.
_PYTHON = Language(tree_sitter_python.language())


@dataclass(frozen=True, slots=True)
class ParseResult:
    tree: Tree
    source: bytes  # kept so callers can slice node text out of it

    @property
    def has_error(self) -> bool:
        """True if the tree contains any ERROR or MISSING node."""
        return self.tree.root_node.has_error


def parse(source: bytes) -> ParseResult:
    """Parse Python source into a syntax tree.

    Never raises on bad syntax: tree-sitter recovers and the damage is reported
    through ParseResult.has_error. The source is assumed to be UTF-8.
    """
    tree = Parser(_PYTHON).parse(source)
    return ParseResult(tree=tree, source=source)


def line_range(node: Node) -> tuple[int, int]:
    """Return the 1-based, inclusive (first_line, last_line) of a node.

    tree-sitter rows are 0-based and an end point is exclusive. When a node ends at
    column 0 of a later row (the module root, or the text inside a triple-quoted
    string whose closing quotes start a line), the node does not really include
    that row, so the last line is the one before it.
    """
    start_row = node.start_point.row
    end_row, end_column = node.end_point
    if end_column == 0 and end_row > start_row:
        return start_row + 1, end_row
    return start_row + 1, end_row + 1
