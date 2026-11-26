import pytest

from coderag.chunking.chunker import chunk_source
from coderag.chunking.model import Chunk, ChunkKind

PATH = "pkg/mod.py"


def ranges(chunks: tuple[Chunk, ...]) -> list[tuple[int, int]]:
    return [(c.start_line, c.end_line) for c in chunks]


def numbered(chunks: tuple[Chunk, ...]) -> list[tuple[int, int]]:
    return [(c.part, c.part_count) for c in chunks]


# A signature much bigger than the body, like FastAPI's Annotated[..., Doc(...)] ones.
BIG_SIGNATURE = b"""def create(
    first: Annotated[
        int,
        Doc("the first parameter of this function"),
    ] = 1,
    second: Annotated[
        int,
        Doc("the second parameter of this function"),
    ] = 2,
    third: Annotated[
        int,
        Doc("the third parameter of this function"),
    ] = 3,
) -> None:
    return None
"""


# --- the limit -------------------------------------------------------------


def test_chunk_at_the_limit_is_not_split():
    source = b"def f():\n    pass\n"
    size = len(source.rstrip(b"\n"))

    (chunk,) = chunk_source(source, PATH, size)

    assert chunk.size_bytes == size
    assert (chunk.part, chunk.part_count) == (1, 1)


def test_one_byte_over_the_limit_is_split():
    source = b"def f():\n    pass\n"
    size = len(source.rstrip(b"\n"))

    chunks = chunk_source(source, PATH, size - 1)

    assert ranges(chunks) == [(1, 1), (2, 2)]
    assert numbered(chunks) == [(1, 2), (2, 2)]


def test_limit_counts_utf8_bytes():
    source = "x = '\u00e9\u00e9\u00e9\u00e9'\ny = 1\n".encode()
    characters = len(source.decode().rstrip("\n"))

    assert len(chunk_source(source, PATH, characters)) == 2


@pytest.mark.parametrize("limit", [0, -1])
def test_non_positive_limit_is_rejected(limit):
    with pytest.raises(ValueError, match="max_chunk_bytes"):
        chunk_source(b"x = 1\n", PATH, limit)


def test_single_line_longer_than_the_limit_stays_whole():
    (chunk,) = chunk_source(b"x = '" + b"a" * 100 + b"'\n", PATH, 20)

    assert chunk.size_bytes > 20
    assert (chunk.part, chunk.part_count) == (1, 1)


# --- cut points ------------------------------------------------------------


def test_big_signature_is_cut_between_parameters():
    # Lines 1-5 are 110 bytes, 6-9 are 100 and 10-15 (last parameter and body) 125.
    chunks = chunk_source(BIG_SIGNATURE, PATH, 130)

    assert ranges(chunks) == [(1, 5), (6, 9), (10, 15)]
    assert [c.text.split("\n")[0].strip() for c in chunks] == [
        "def create(",
        "second: Annotated[",
        "third: Annotated[",
    ]


def test_body_is_cut_between_statements():
    source = (
        b"def f():\n"
        b"    first = call(\n        1,\n        2,\n    )\n"
        b"    second = call(\n        3,\n        4,\n    )\n"
        b"    return first + second\n"
    )

    # Lines 1-5 are 54 bytes and 6-10 are 72; neither neighbour pair fits together.
    chunks = chunk_source(source, PATH, 75)

    assert ranges(chunks) == [(1, 5), (6, 10)]


def test_big_nested_block_is_cut_at_its_own_statements():
    source = (
        b"def f():\n"
        b"    for item in items:\n"
        b"        process_first(item)\n"
        b"        process_second(\n"
        b"            item,\n"
        b"        )\n"
    )

    chunks = chunk_source(source, PATH, 60)

    assert ranges(chunks) == [(1, 3), (4, 6)]


def test_statement_without_inner_boundaries_is_cut_by_lines():
    entries = b"".join(b"    'key%d': %d,\n" % (i, i) for i in range(10))
    source = b"DATA = {\n" + entries + b"}\n"

    chunks = chunk_source(source, PATH, 40)

    assert len(chunks) > 2
    assert all(c.size_bytes <= 40 for c in chunks)


def test_neighbouring_pieces_share_parts_of_similar_size():
    source = b"".join(b"x%d = %d\n" % (i, i) for i in range(10))

    chunks = chunk_source(source, PATH, 20)

    # Four parts are the minimum; filling them in order would leave a single line behind.
    assert ranges(chunks) == [(1, 3), (4, 6), (7, 8), (9, 10)]


def test_no_small_tail_is_left_behind():
    source = b"def f():\n" + b"".join(b"    v%d = %d\n" % (i, i) for i in range(8))

    chunks = chunk_source(source, PATH, 80)

    assert ranges(chunks) == [(1, 5), (6, 9)]
    assert [c.size_bytes for c in chunks] == [52, 43]


def test_parts_are_the_best_grouping_found_by_brute_force():
    widths = (1, 9, 3, 14, 2, 2, 11, 5)
    lines = [f"v{i} = {'1' * width}" for i, width in enumerate(widths)]
    source = "\n".join(lines).encode()

    def score(sizes: list[int]) -> tuple[int, int]:
        return len(sizes), sum(size * size for size in sizes)

    for limit in range(max(map(len, lines)), len(source) + 1):
        candidates = []
        for mask in range(2 ** (len(lines) - 1)):
            cuts = [i + 1 for i in range(len(lines) - 1) if mask >> i & 1]
            bounds = zip([0, *cuts], [*cuts, len(lines)], strict=True)
            sizes = [len("\n".join(lines[start:end])) for start, end in bounds]
            if max(sizes) <= limit:
                candidates.append(score(sizes))

        found = score([c.size_bytes for c in chunk_source(source, PATH, limit)])

        assert found == min(candidates), limit


def test_header_stays_with_the_first_statement_of_a_split_block():
    source = (
        b"first = 1\n"
        b"if flag:\n"
        b"    second = 'yyyyyyyyyyyyyyyyyyyy'\n"
        b"    third = 'zzzzzzzzzzzzzzzzzzzz'\n"
    )

    # (1, 2), (3, 3), (4, 4) would be more even, but it would strand the "if" line.
    chunks = chunk_source(source, PATH, 50)

    assert ranges(chunks) == [(1, 1), (2, 3), (4, 4)]


def test_decorator_and_nested_header_stay_with_the_code_they_introduce():
    source = (
        b"if flag:\n"
        b"    first = 1\n"
        b"    @decorator\n"
        b"    def g():\n"
        b"        second = 'bbbbbbbbbbbbbbbbbbbb'\n"
        b"        third = 'cccccccccccccccccccc'\n"
    )

    chunks = chunk_source(source, PATH, 70)

    assert ranges(chunks) == [(1, 2), (3, 5), (6, 6)]


def test_comment_stays_with_the_statement_below_it_at_a_cut():
    source = b"def f():\n    alpha = 1\n    # about beta\n    beta = 2\n"

    chunks = chunk_source(source, PATH, 40)

    assert ranges(chunks) == [(1, 2), (3, 4)]


def test_blank_lines_at_a_cut_belong_to_no_part():
    source = b"def f():\n    alpha = 1\n\n\n    beta = 2\n"

    chunks = chunk_source(source, PATH, 24)

    assert ranges(chunks) == [(1, 2), (5, 5)]


# --- what the parts carry ----------------------------------------------------


def test_parts_share_kind_name_and_context():
    chunks = chunk_source(BIG_SIGNATURE, PATH, 130)

    assert {c.kind for c in chunks} == {ChunkKind.FUNCTION}
    assert {c.qualname for c in chunks} == {"create"}
    assert {c.context for c in chunks} == {"pkg/mod.py\ncreate"}
    assert len({c.id for c in chunks}) == len(chunks)
    assert numbered(chunks) == [(1, 3), (2, 3), (3, 3)]


def test_identical_parts_get_distinct_ids():
    source = b"def f():\n" + b"    step()\n" * 6

    chunks = chunk_source(source, PATH, 21)

    assert len({c.id for c in chunks}) == len(chunks)


def test_big_method_parts_keep_the_class_signature():
    source = b"class A(B):\n    def f(self):\n        one = 1\n        two = 2\n"

    parts = [c for c in chunk_source(source, PATH, 36) if c.kind is ChunkKind.METHOD]

    assert len(parts) == 2
    assert {c.context for c in parts} == {"pkg/mod.py\nA.f\nclass A(B):"}


def test_big_class_header_is_split_and_every_part_lists_the_methods():
    source = (
        b"class A:\n    first = 'value one'\n    second = 'value two'\n"
        b"    def f(self):\n        pass\n"
    )

    headers = [c for c in chunk_source(source, PATH, 34) if c.kind is ChunkKind.CLASS_HEADER]

    assert ranges(tuple(headers)) == [(1, 2), (3, 3)]
    assert {c.context for c in headers} == {"pkg/mod.py\nA\ndef f"}


def test_class_without_methods_is_split_between_attributes():
    source = b"class A:\n    first = 'value one'\n    second = 'value two'\n"

    chunks = chunk_source(source, PATH, 34)

    assert [c.kind for c in chunks] == [ChunkKind.CLASS] * 2
    assert ranges(chunks) == [(1, 2), (3, 3)]


def test_defined_names_follow_the_part_that_holds_the_definition():
    source = b"if A:\n    def first():\n        pass\nif B:\n    def second():\n        pass\n"

    chunks = chunk_source(source, PATH, 40)

    assert [c.defined_names for c in chunks] == [("first",), ("second",)]


# --- invariants for any limit ------------------------------------------------

SOURCES = [
    BIG_SIGNATURE,
    b"# top\n\n@dec(\n    1,\n)\ndef f(a, b):\n    '''Doc.\n\n    More.\n    '''\n    return a\n",
    b"class A(B):\n    x = 1\n\n    def f(self):\n        if x:\n            pass\n"
    b"        elif y:\n            pass\n        else:\n            pass\n\n    y = 2\n",
    b"try:\n    import a\nexcept ImportError:\n    class A:\n        pass\nfinally:\n    pass\n",
    b"match x:\n    case 1:\n        pass\n    case _:\n        pass\n",
    b"def broken(:\n    pass\n\nclass B(\n    x = 1\n",
    b"x = (\ndef f():\n    pass\nclass\n@\n",
    b"import a\r\n\r\ndef f():\r\n    pass\r\n",
    b'def f():\n    s = """line\n\n    # not a comment\n    """\n    return s\n',
    "s = '\u00e9\u00e9\u00e9'\n\ndef f():\n    return '\u00fc'\n".encode(),
]


@pytest.mark.parametrize("limit", [1, 12, 30, 80, 250])
@pytest.mark.parametrize("source", SOURCES)
def test_invariants_hold_for_any_limit(source, limit):
    chunks = chunk_source(source, PATH, limit)

    lines = source.split(b"\n")
    owners = [0] * len(lines)
    for chunk in chunks:
        cited = b"\n".join(lines[chunk.start_line - 1 : chunk.end_line])
        assert chunk.text == cited.decode("utf-8", errors="replace")
        assert chunk.size_bytes <= limit or chunk.start_line == chunk.end_line
        assert lines[chunk.start_line - 1].strip() and lines[chunk.end_line - 1].strip()
        for index in range(chunk.start_line - 1, chunk.end_line):
            owners[index] += 1
    for line, count in zip(lines, owners, strict=True):
        assert count == 1 if line.strip() else count <= 1
    assert [c.start_line for c in chunks] == sorted(c.start_line for c in chunks)
    assert len({c.id for c in chunks}) == len(chunks)
    assert chunk_source(source, PATH, limit) == chunks
