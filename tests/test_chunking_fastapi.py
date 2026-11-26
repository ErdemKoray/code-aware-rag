"""Chunk every indexed file of the pinned FastAPI clone and check the guarantees.

The clone lives in data/repos/ (gitignored), so these tests skip themselves when it is
missing, e.g. in CI.
"""

from collections import Counter
from dataclasses import dataclass

import pytest
from tree_sitter import Node

from coderag.chunking.chunker import chunk_source
from coderag.chunking.model import Chunk, ChunkKind
from coderag.config import Settings
from coderag.parsing.python import line_range, parse
from coderag.scan import scan


@dataclass(frozen=True)
class ChunkedRepo:
    limit: int
    sources: dict[str, bytes]
    chunks: dict[str, tuple[Chunk, ...]]

    def all_chunks(self) -> list[Chunk]:
        return [chunk for chunks in self.chunks.values() for chunk in chunks]


@pytest.fixture(scope="module")
def repo() -> ChunkedRepo:
    settings = Settings()
    root = settings.fastapi_repo_path
    if not root.is_dir():
        pytest.skip(f"FastAPI clone not found at {root}")
    included = scan(root, settings.max_file_size_bytes).included
    sources = {file.path: (root / file.path).read_bytes() for file in included}
    limit = settings.max_chunk_bytes
    chunks = {path: chunk_source(source, path, limit) for path, source in sources.items()}
    return ChunkedRepo(limit, sources, chunks)


def test_there_is_something_to_check(repo):
    assert len(repo.sources) > 0
    assert len(repo.all_chunks()) > len(repo.sources)


def test_every_non_blank_line_is_in_exactly_one_chunk(repo):
    problems = []
    for path, source in repo.sources.items():
        lines = source.split(b"\n")
        owners = Counter(
            number
            for chunk in repo.chunks[path]
            for number in range(chunk.start_line, chunk.end_line + 1)
        )
        for number, line in enumerate(lines, start=1):
            if owners[number] > 1 or (line.strip() and owners[number] == 0):
                problems.append(f"{path}:{number} is in {owners[number]} chunks")
    assert problems == []


def test_chunk_text_is_exactly_the_cited_lines(repo):
    for path, source in repo.sources.items():
        lines = source.split(b"\n")
        for chunk in repo.chunks[path]:
            cited = b"\n".join(lines[chunk.start_line - 1 : chunk.end_line])
            assert chunk.text.encode("utf-8") == cited, f"{path}:{chunk.start_line}"


def test_no_chunk_is_over_the_limit(repo):
    over = [
        f"{c.path}:{c.start_line} {c.size_bytes} B"
        for c in repo.all_chunks()
        if c.size_bytes > repo.limit and c.start_line != c.end_line
    ]
    assert over == []


def test_ids_are_unique_across_the_repository(repo):
    ids = Counter(chunk.id for chunk in repo.all_chunks())

    assert [chunk_id for chunk_id, count in ids.items() if count > 1] == []


def test_no_file_is_flagged_with_syntax_errors(repo):
    assert [c.path for c in repo.all_chunks() if c.has_error] == []


def test_parts_of_a_split_unit_are_consecutive_and_complete(repo):
    for path, chunks in repo.chunks.items():
        expected: tuple[ChunkKind, str | None, int, int] | None = None
        for chunk in chunks:
            if expected is not None:
                assert (chunk.kind, chunk.qualname, chunk.part, chunk.part_count) == expected, path
            else:
                assert chunk.part == 1, f"{path}:{chunk.start_line}"
            expected = None
            if chunk.part < chunk.part_count:
                expected = (chunk.kind, chunk.qualname, chunk.part + 1, chunk.part_count)
        assert expected is None, path


def test_chunking_twice_gives_the_same_result(repo):
    for path, source in repo.sources.items():
        assert chunk_source(source, path, repo.limit) == repo.chunks[path]


def unwrap(node: Node) -> Node:
    if node.type == "decorated_definition":
        return node.child_by_field_name("definition")
    return node


def expected_units(root: Node) -> Counter[tuple[ChunkKind, str]]:
    """Module-level functions and the methods of module-level classes, found independently."""
    expected: Counter[tuple[ChunkKind, str]] = Counter()
    for node in root.named_children:
        node = unwrap(node)
        if node.type == "function_definition":
            expected[ChunkKind.FUNCTION, node.child_by_field_name("name").text.decode()] += 1
        elif node.type == "class_definition":
            class_name = node.child_by_field_name("name").text.decode()
            for member in node.child_by_field_name("body").named_children:
                member = unwrap(member)
                if member.type == "function_definition":
                    name = member.child_by_field_name("name").text.decode()
                    expected[ChunkKind.METHOD, f"{class_name}.{name}"] += 1
    return expected


def test_every_function_and_method_has_its_own_chunk(repo):
    for path, source in repo.sources.items():
        found = Counter(
            (chunk.kind, chunk.qualname)
            for chunk in repo.chunks[path]
            if chunk.kind in (ChunkKind.FUNCTION, ChunkKind.METHOD) and chunk.part == 1
        )
        assert found == expected_units(parse(source).tree.root_node), path


def test_parameters_that_fit_are_never_cut_in_half(repo):
    cut = []
    for path, source in repo.sources.items():
        part_starts = {c.start_line for c in repo.chunks[path] if c.part > 1}
        if not part_starts:
            continue
        stack = [parse(source).tree.root_node]
        while stack:
            node = stack.pop()
            stack.extend(node.named_children)
            if node.type != "parameters":
                continue
            for parameter in node.named_children:
                first, last = line_range(parameter)
                fits = parameter.end_byte - parameter.start_byte < repo.limit // 2
                inside = [line for line in part_starts if first < line <= last]
                if fits and inside:
                    cut.append(f"{path}:{first} cut at {inside}")
    assert cut == []
