"""Cut an oversized line range into parts at syntax boundaries (decision C5).

Parameters of a signature and statements of a body are the preferred cut points, found
level by level down the tree; plain lines are the last resort.
"""

from itertools import accumulate

from tree_sitter import Node

from coderag.parsing.python import line_range

# Statements and clauses whose nested blocks may be cut apart.
_COMPOUND = frozenset(
    {
        "if_statement",
        "elif_clause",
        "else_clause",
        "for_statement",
        "while_statement",
        "try_statement",
        "except_clause",
        "finally_clause",
        "with_statement",
        "match_statement",
        "case_clause",
    }
)
_COMPOUND_PARTS = frozenset(
    {"block", "elif_clause", "else_clause", "except_clause", "finally_clause"}
)


def _sub_units(node: Node) -> list[Node]:
    """The children of a node in front of which it may be cut."""
    if node.type in ("module", "block", "decorated_definition"):
        children = node.named_children
    elif node.type == "function_definition":
        parameters = node.child_by_field_name("parameters")
        body = node.child_by_field_name("body")
        children = [*(parameters.named_children if parameters else []), *([body] if body else [])]
    elif node.type == "class_definition":
        body = node.child_by_field_name("body")
        children = [body] if body else []
    elif node.type in _COMPOUND:
        children = [child for child in node.named_children if child.type in _COMPOUND_PARTS]
    else:
        return []
    # Comments are not cut points of their own: they travel with what follows them.
    return [child for child in children if child.type != "comment"]


class LineSplitter:
    """Splits line ranges (1-based, inclusive) of one file so that each part fits."""

    def __init__(
        self, root: Node, lines: list[bytes], comment_lines: frozenset[int], max_bytes: int
    ) -> None:
        self._root = root
        self._lines = lines
        self._comment_lines = comment_lines
        self._max_bytes = max_bytes
        # Running total of line sizes as they will be in the chunk text (UTF-8).
        sizes = (len(line.decode("utf-8", errors="replace").encode("utf-8")) for line in lines)
        self._totals = list(accumulate(sizes, initial=0))

    def split(self, first_line: int, last_line: int) -> list[tuple[int, int]]:
        """Parts of first_line..last_line without blank edges; none if all lines are blank.

        Each part is at most max_bytes long, unless it is a single longer line.
        """
        while first_line <= last_line and self._is_blank(first_line):
            first_line += 1
        while last_line >= first_line and self._is_blank(last_line):
            last_line -= 1
        if first_line > last_line:
            return []
        if first_line == last_line or self._size(first_line, last_line) <= self._max_bytes:
            return [(first_line, last_line)]

        starts = self._cut_points(first_line, last_line)
        if starts:
            ends = [start - 1 for start in starts] + [last_line]
            segments = zip([first_line, *starts], ends, strict=True)
            parts = [part for segment in segments for part in self.split(*segment)]
        else:
            numbers = range(first_line, last_line + 1)
            parts = [(number, number) for number in numbers if not self._is_blank(number)]
        return self._pack(parts)

    def _cut_points(self, first_line: int, last_line: int) -> list[int]:
        """Lines after first_line where the highest possible syntax level can be cut."""
        level = [self._root]
        while level:
            units = []
            for node in level:
                for unit in _sub_units(node):
                    unit_first, unit_last = line_range(unit)
                    if unit_first <= last_line and unit_last >= first_line:
                        units.append(unit)
            starts = {self._start_line(unit, first_line) for unit in units}
            cuts = sorted(start for start in starts if first_line < start <= last_line)
            if cuts:
                return cuts
            level = units
        return []

    def _start_line(self, node: Node, floor: int) -> int:
        """First line of a node, including the comment lines directly above it."""
        line = line_range(node)[0]
        while line > floor and line - 1 in self._comment_lines:
            line -= 1
        return line

    def _pack(self, parts: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """Join neighbouring parts, greedily, while the result still fits."""
        packed = parts[:1]
        for first_line, last_line in parts[1:]:
            previous_first = packed[-1][0]
            if self._size(previous_first, last_line) <= self._max_bytes:
                packed[-1] = (previous_first, last_line)
            else:
                packed.append((first_line, last_line))
        return packed

    def _size(self, first_line: int, last_line: int) -> int:
        newlines = last_line - first_line
        return self._totals[last_line] - self._totals[first_line - 1] + newlines

    def _is_blank(self, line: int) -> bool:
        return not self._lines[line - 1].strip()
