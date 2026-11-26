"""Cut an oversized line range into parts at syntax boundaries (decisions C5, B1).

First the range is broken into atoms, pieces that are never cut apart: the largest
syntax units that fit (parameters, statements), found level by level down the tree, and
plain lines as the last resort. Then neighbouring atoms are grouped into the fewest
parts that fit, as equal in size as possible.
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
        return self._balance(self._atoms(first_line, last_line))

    def _atoms(self, first_line: int, last_line: int) -> list[tuple[int, int]]:
        """The range as pieces that are never cut apart, each without blank edges."""
        while first_line <= last_line and self._is_blank(first_line):
            first_line += 1
        while last_line >= first_line and self._is_blank(last_line):
            last_line -= 1
        if first_line > last_line:
            return []
        if first_line == last_line or self._size(first_line, last_line) <= self._max_bytes:
            return [(first_line, last_line)]

        cuts, introductions = self._cut_points(first_line, last_line)
        if not cuts:
            numbers = range(first_line, last_line + 1)
            return [(number, number) for number in numbers if not self._is_blank(number)]

        atoms: list[tuple[int, int]] = []
        introduces_next = False
        ends = [cut - 1 for cut in cuts] + [last_line]
        for start, end in zip([first_line, *cuts], ends, strict=True):
            found = self._atoms(start, end)
            if introduces_next:
                self._glue(atoms, found)
            atoms += found
            introduces_next = start in introductions
        return atoms

    def _cut_points(self, first_line: int, last_line: int) -> tuple[list[int], frozenset[int]]:
        """Lines after first_line where the highest possible syntax level can be cut.

        Also returns the segment starts (first_line or a cut) whose segment only
        introduces the next one: the header of an enclosing unit, or a decorator.
        """
        level = [self._root]
        while level:
            units = []
            for node in level:
                for unit in _sub_units(node):
                    unit_first, unit_last = line_range(unit)
                    if unit_first <= last_line and unit_last >= first_line:
                        units.append(unit)
            starts = [(self._start_line(unit, first_line), unit.type) for unit in units]
            cuts = sorted({start for start, _ in starts if first_line < start <= last_line})
            if cuts:
                whole = {start for start, kind in starts if kind != "decorator"}
                introductions = {cut for cut in cuts if cut not in whole}
                if not any(start <= first_line for start in whole):
                    introductions.add(first_line)
                return cuts, frozenset(introductions)
            level = units
        return [], frozenset()

    def _start_line(self, node: Node, floor: int) -> int:
        """First line of a node, including the comment lines directly above it."""
        line = line_range(node)[0]
        while line > floor and line - 1 in self._comment_lines:
            line -= 1
        return line

    def _glue(self, before: list[tuple[int, int]], after: list[tuple[int, int]]) -> None:
        """Move the last atom of before into the first of after, if both fit in one part."""
        if before and after and self._size(before[-1][0], after[0][1]) <= self._max_bytes:
            after[0] = (before.pop()[0], after[0][1])

    def _balance(self, atoms: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """Group neighbouring atoms into the fewest parts that fit, as equal as possible.

        Of the groupings with the fewest parts, the one with the smallest sum of squared
        sizes wins; on a tie the later part is the shorter one.
        """
        # best[n], for the first n atoms: (parts, sum of squares, first atom of last part).
        best = [(0, 0, 0)]
        for end in range(1, len(atoms) + 1):
            choices = []
            for start in range(end - 1, -1, -1):
                size = self._size(atoms[start][0], atoms[end - 1][1])
                if size > self._max_bytes and start < end - 1:
                    break
                parts, squares, _ = best[start]
                choices.append((parts + 1, squares + size * size, start))
            best.append(min(choices, key=lambda choice: choice[:2]))

        grouped: list[tuple[int, int]] = []
        end = len(atoms)
        while end:
            start = best[end][2]
            grouped.append((atoms[start][0], atoms[end - 1][1]))
            end = start
        return grouped[::-1]

    def _size(self, first_line: int, last_line: int) -> int:
        newlines = last_line - first_line
        return self._totals[last_line] - self._totals[first_line - 1] + newlines

    def _is_blank(self, line: int) -> bool:
        return not self._lines[line - 1].strip()
