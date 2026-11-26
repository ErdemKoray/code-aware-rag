from collections import Counter
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


def _method_label(method: _Definition) -> str:
    keyword = "async def" if method.node.children[0].type == "async" else "def"
    return f"{keyword} {method.name}"


class _FileChunks:
    """Collects the chunks of one file and keeps their ids unique."""

    def __init__(self, source: bytes, path: str, has_error: bool) -> None:
        self._source = source
        # Split on "\n" only, which is how tree-sitter counts rows.
        self._lines = source.split(b"\n")
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
            )
        )

    def add_function(
        self, function: _Definition, kind: ChunkKind, qualname: str, context: tuple[str, ...]
    ) -> None:
        # The range of the outer node, so that decorators belong to the chunk.
        first_line, last_line = line_range(function.outer)
        self.add(kind, qualname, first_line, last_line, context)

    def add_class(self, cls: _Definition, qualname: str) -> None:
        """A class with methods or inner classes is split; any other class stays whole."""
        first_line, last_line = line_range(cls.outer)
        body = cls.node.child_by_field_name("body")
        colon = next((child for child in cls.node.children if child.type == ":"), None)
        members = _definitions(body) if body is not None else []

        # A member starting on the header's own line ("class A: def f(self): ...")
        # cannot be separated from it: a line belongs to exactly one chunk.
        if colon is None or not members or line_range(members[0].outer)[0] <= line_range(colon)[0]:
            self.add(ChunkKind.CLASS, qualname, first_line, last_line, (self._path, qualname))
            return

        signature = self._source[cls.node.start_byte : colon.end_byte].decode(
            "utf-8", errors="replace"
        )
        header_end = self._last_code_line(first_line, line_range(members[0].outer)[0] - 1)
        methods = tuple(_method_label(member) for member in members if not member.is_class)
        self.add(
            ChunkKind.CLASS_HEADER,
            qualname,
            first_line,
            header_end,
            (self._path, qualname, *methods),
        )
        for member in members:
            member_name = f"{qualname}.{member.name}"
            if member.is_class:
                self.add_class(member, member_name)
            else:
                context = (self._path, member_name, signature)
                self.add_function(member, ChunkKind.METHOD, member_name, context)

    def _last_code_line(self, first_line: int, last_line: int) -> int:
        """last_line moved up past blank lines, but never above first_line."""
        while last_line > first_line and not self._lines[last_line - 1].strip():
            last_line -= 1
        return last_line


def chunk_source(source: bytes, path: str) -> tuple[Chunk, ...]:
    """Split one file into chunks, in source order. path is repo-relative, "/" separated.

    Never raises on bad syntax. Work in progress: module-level functions and classes
    become chunks; module code, class blocks, comments and size splitting come next.
    """
    result = parse(source)
    file_chunks = _FileChunks(source, path, result.has_error)

    for definition in _definitions(result.tree.root_node):
        if definition.is_class:
            file_chunks.add_class(definition, definition.name)
        else:
            context = (path, definition.name)
            file_chunks.add_function(definition, ChunkKind.FUNCTION, definition.name, context)

    return tuple(file_chunks.chunks)
