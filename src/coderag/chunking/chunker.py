from collections import Counter

from tree_sitter import Node

from coderag.chunking.model import Chunk, ChunkKind, make_chunk_id
from coderag.parsing.python import line_range, parse
from coderag.scan import is_test_path


def _unwrap(node: Node) -> Node:
    """The function or class inside a decorated definition; other nodes unchanged."""
    if node.type == "decorated_definition":
        return node.child_by_field_name("definition") or node
    return node


class _FileChunks:
    """Collects the chunks of one file and keeps their ids unique."""

    def __init__(self, source: bytes, path: str, has_error: bool) -> None:
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


def chunk_source(source: bytes, path: str) -> tuple[Chunk, ...]:
    """Split one file into chunks, in source order. path is repo-relative, "/" separated.

    Never raises on bad syntax. Work in progress: only module-level functions become
    chunks so far; classes, module code and size splitting come next.
    """
    result = parse(source)
    file_chunks = _FileChunks(source, path, result.has_error)

    for node in result.tree.root_node.named_children:
        definition = _unwrap(node)
        if definition.type != "function_definition":
            continue
        name_node = definition.child_by_field_name("name")
        if name_node is None:
            continue
        name = name_node.text.decode("utf-8", errors="replace")
        # The range of the outer node, so that decorators belong to the chunk.
        first_line, last_line = line_range(node)
        file_chunks.add(ChunkKind.FUNCTION, name, first_line, last_line, (path, name))

    return tuple(file_chunks.chunks)
