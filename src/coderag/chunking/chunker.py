from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass

from tree_sitter import Node

from coderag.chunking.model import Chunk, ChunkKind, make_chunk_id
from coderag.parsing.python import line_range, parse
from coderag.scan import is_test_path


@dataclass(frozen=True, slots=True)
class _Definition:
    """A function or class that can get a chunk of its own."""

    outer: Node  # the decorated_definition if there are decorators, else the same as node
    node: Node  # the function_definition or class_definition
    name: str

    @property
    def is_class(self) -> bool:
        return self.node.type == "class_definition"


def _as_definition(node: Node) -> _Definition | None:
    inner = node
    if node.type == "decorated_definition":
        inner = node.child_by_field_name("definition") or node
    if inner.type not in ("function_definition", "class_definition"):
        return None
    name = inner.child_by_field_name("name")
    # Error recovery can leave a definition without a usable name.
    if name is None or not name.text:
        return None
    return _Definition(node, inner, name.text.decode("utf-8", errors="replace"))


def _definitions(parent: Node) -> list[_Definition]:
    """The definitions that are direct children of a module or a class body."""
    found = (_as_definition(child) for child in parent.named_children)
    return [definition for definition in found if definition is not None]


def _outermost_definitions(scope: Node) -> Iterator[_Definition]:
    """Every definition in a scope, also inside if/try/..., but not inside another one."""
    # Iterative, because long expression chains make very deep trees.
    stack = list(reversed(scope.named_children))
    while stack:
        node = stack.pop()
        definition = _as_definition(node)
        if definition is not None:
            yield definition
        else:
            stack.extend(reversed(node.named_children))


def _comment_only_lines(root: Node, lines: list[bytes]) -> frozenset[int]:
    """1-based numbers of the lines that hold a comment and nothing before it."""
    found: set[int] = set()
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type == "comment":
            row, column = node.start_point
            # tree-sitter knows a "#" inside a string is not a comment.
            if not lines[row][:column].strip():
                found.add(row + 1)
        else:
            stack.extend(node.children)
    return frozenset(found)


@dataclass(frozen=True, slots=True)
class _Member:
    """A definition that gets its own chunk, with the lines it owns."""

    definition: _Definition
    first_line: int  # includes decorators and the comment lines directly above
    last_line: int


def _method_label(method: _Definition) -> str:
    keyword = "async def" if method.node.children[0].type == "async" else "def"
    return f"{keyword} {method.name}"


class _FileChunks:
    """Collects the chunks of one file and keeps their ids unique.

    Lines are owned, so that every non-blank line ends up in exactly one chunk: each
    member takes its own line range, and the lines left between members become blocks.
    """

    def __init__(self, source: bytes, path: str, root: Node, has_error: bool) -> None:
        self._source = source
        # Split on "\n" only, which is how tree-sitter counts rows.
        self._lines = source.split(b"\n")
        self._comment_lines = _comment_only_lines(root, self._lines)
        self._path = path
        self._has_error = has_error
        self._is_test = is_test_path(path)
        self._seen: Counter[tuple[ChunkKind, str | None, str]] = Counter()
        self.chunks: list[Chunk] = []

    def add(
        self,
        kind: ChunkKind,
        qualname: str | None,
        first_line: int,
        last_line: int,
        context: tuple[str, ...],
        defined_names: tuple[str, ...] = (),
    ) -> None:
        raw = b"\n".join(self._lines[first_line - 1 : last_line])
        text = raw.decode("utf-8", errors="replace")
        self._seen[(kind, qualname, text)] += 1
        self.chunks.append(
            Chunk(
                id=make_chunk_id(
                    self._path, qualname, kind, text, self._seen[(kind, qualname, text)]
                ),
                path=self._path,
                kind=kind,
                qualname=qualname,
                start_line=first_line,
                end_line=last_line,
                text=text,
                context="\n".join(context),
                is_test=self._is_test,
                has_error=self._has_error,
                defined_names=defined_names,
            )
        )

    def add_block(
        self,
        kind: ChunkKind,
        qualname: str | None,
        first_line: int,
        last_line: int,
        context: tuple[str, ...],
        unchunked: list[tuple[str, int]],
    ) -> None:
        """Add the lines first_line..last_line without blank edges, if any are left.

        unchunked lists (name, line) of definitions that have no chunk of their own; the
        ones inside this block are recorded in its defined_names.
        """
        while first_line <= last_line and not self._lines[first_line - 1].strip():
            first_line += 1
        while last_line >= first_line and not self._lines[last_line - 1].strip():
            last_line -= 1
        if first_line > last_line:
            return
        names = tuple(name for name, line in unchunked if first_line <= line <= last_line)
        self.add(kind, qualname, first_line, last_line, context, names)

    def add_module(self, root: Node) -> None:
        members = self._members(_definitions(root), floor=0)
        unchunked = self._unchunked(root, members, prefix="")
        next_line = 1
        for member in members:
            self.add_block(
                ChunkKind.MODULE, None, next_line, member.first_line - 1, (self._path,), unchunked
            )
            name = member.definition.name
            if member.definition.is_class:
                self.add_class(member, name)
            else:
                self.add(
                    ChunkKind.FUNCTION,
                    name,
                    member.first_line,
                    member.last_line,
                    (self._path, name),
                )
            next_line = member.last_line + 1
        self.add_block(
            ChunkKind.MODULE, None, next_line, len(self._lines), (self._path,), unchunked
        )

    def add_class(self, cls: _Member, qualname: str) -> None:
        """A class with methods or inner classes is split; any other class stays whole."""
        node = cls.definition.node
        body = node.child_by_field_name("body")
        colon = next((child for child in node.children if child.type == ":"), None)
        members: list[_Member] = []
        if body is not None and colon is not None:
            # A member starting on the header's own line cannot be separated from it.
            members = self._members(_definitions(body), floor=line_range(colon)[0])
        unchunked = [] if body is None else self._unchunked(body, members, f"{qualname}.")

        if not members:
            self.add_block(
                ChunkKind.CLASS,
                qualname,
                cls.first_line,
                cls.last_line,
                (self._path, qualname),
                unchunked,
            )
            return

        signature = self._source[node.start_byte : colon.end_byte].decode("utf-8", errors="replace")
        methods = tuple(
            _method_label(member.definition) for member in members if not member.definition.is_class
        )
        self.add_block(
            ChunkKind.CLASS_HEADER,
            qualname,
            cls.first_line,
            members[0].first_line - 1,
            (self._path, qualname, *methods),
            unchunked,
        )
        block_context = (self._path, qualname, signature)
        next_line = members[0].first_line
        for member in members:
            self.add_block(
                ChunkKind.CLASS_BLOCK,
                qualname,
                next_line,
                member.first_line - 1,
                block_context,
                unchunked,
            )
            member_name = f"{qualname}.{member.definition.name}"
            if member.definition.is_class:
                self.add_class(member, member_name)
            else:
                self.add(
                    ChunkKind.METHOD,
                    member_name,
                    member.first_line,
                    member.last_line,
                    (self._path, member_name, signature),
                )
            next_line = member.last_line + 1
        self.add_block(
            ChunkKind.CLASS_BLOCK, qualname, next_line, cls.last_line, block_context, unchunked
        )

    def _members(self, definitions: list[_Definition], floor: int) -> list[_Member]:
        """Give each definition its lines; floor is the last line already taken.

        Decorators are part of the outer node. Comment lines directly above (no blank
        line between) are added, as long as nothing else owns them. A definition that
        starts on a taken line stays with whatever owns that line.
        """
        members: list[_Member] = []
        for definition in definitions:
            first_line, last_line = line_range(definition.outer)
            if first_line <= floor:
                continue
            while first_line - 1 > floor and first_line - 1 in self._comment_lines:
                first_line -= 1
            members.append(_Member(definition, first_line, last_line))
            floor = last_line
        return members

    def _unchunked(self, scope: Node, members: list[_Member], prefix: str) -> list[tuple[str, int]]:
        """(qualified name, first line) of the definitions in a scope without own chunks."""
        chunked = {member.definition.outer.start_byte for member in members}
        return [
            (f"{prefix}{definition.name}", line_range(definition.outer)[0])
            for definition in _outermost_definitions(scope)
            if definition.outer.start_byte not in chunked
        ]


def chunk_source(source: bytes, path: str) -> tuple[Chunk, ...]:
    """Split one file into chunks, in source order. path is repo-relative, "/" separated.

    Every non-blank line belongs to exactly one chunk. Never raises on bad syntax.
    Work in progress: chunks larger than the size limit are not split yet.
    """
    result = parse(source)
    root = result.tree.root_node
    file_chunks = _FileChunks(source, path, root, result.has_error)
    file_chunks.add_module(root)
    return tuple(file_chunks.chunks)
