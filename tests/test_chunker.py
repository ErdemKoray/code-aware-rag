from functools import partial

import pytest

from coderag.chunking import chunker
from coderag.chunking.model import Chunk, ChunkKind, make_chunk_id

PATH = "pkg/mod.py"
# Large enough that nothing is split here; splitting has its own tests.
chunk_source = partial(chunker.chunk_source, max_chunk_bytes=4_000)


def functions(source: bytes, path: str = PATH) -> list[Chunk]:
    return [c for c in chunk_source(source, path) if c.kind is ChunkKind.FUNCTION]


# --- module-level functions ------------------------------------------------


def test_function_becomes_one_chunk():
    source = b'def f(a):\n    """Doc."""\n    return a\n'

    (chunk,) = chunk_source(source, PATH)

    assert chunk.kind is ChunkKind.FUNCTION
    assert chunk.qualname == "f"
    assert chunk.path == PATH
    assert (chunk.start_line, chunk.end_line) == (1, 3)
    assert chunk.text == 'def f(a):\n    """Doc."""\n    return a'
    assert chunk.context == "pkg/mod.py\nf"
    assert chunk.id == make_chunk_id(PATH, "f", ChunkKind.FUNCTION, chunk.text)


def test_async_function_is_a_function_chunk():
    (chunk,) = functions(b"async def fetch():\n    return 1\n")

    assert chunk.qualname == "fetch"
    assert chunk.text.startswith("async def fetch")


def test_decorators_belong_to_the_chunk():
    source = b"x = 1\n\n@app.get(\n    '/x'\n)\n@other\ndef f():\n    pass\n"

    (chunk,) = functions(source)

    assert (chunk.start_line, chunk.end_line) == (3, 8)
    assert chunk.text.startswith("@app.get(")


def test_comment_between_decorator_and_def_is_kept():
    (chunk,) = functions(b"@dec\n# why\ndef f():\n    pass\n")

    assert "# why" in chunk.text
    assert (chunk.start_line, chunk.end_line) == (1, 4)


def test_functions_come_out_in_source_order_with_their_own_lines():
    source = b"def a():\n    pass\n\n\ndef b():\n    pass\n"

    first, second = functions(source)

    assert [first.qualname, second.qualname] == ["a", "b"]
    assert (first.start_line, first.end_line) == (1, 2)
    assert (second.start_line, second.end_line) == (5, 6)


def test_nested_functions_stay_in_their_parent():
    source = b"def outer():\n    def inner():\n        pass\n    return inner\n"

    (chunk,) = chunk_source(source, PATH)

    assert chunk.qualname == "outer"
    assert "def inner" in chunk.text


def test_function_inside_a_compound_statement_gets_no_function_chunk():
    source = b"try:\n    import x\nexcept ImportError:\n    def x():\n        pass\n"

    assert functions(source) == []


def test_empty_source_has_no_chunks():
    assert chunk_source(b"", PATH) == ()


# --- text fidelity ---------------------------------------------------------


def test_text_equals_the_cited_source_lines():
    source = "import os\n\n\ndef f():\n    return 'naïve'\n".encode()

    (chunk,) = functions(source)

    cited = source.split(b"\n")[chunk.start_line - 1 : chunk.end_line]
    assert chunk.text.encode("utf-8") == b"\n".join(cited)


def test_crlf_line_endings_are_kept_exactly():
    (chunk,) = functions(b"def f():\r\n    pass\r\n")

    assert chunk.text == "def f():\r\n    pass\r"
    assert (chunk.start_line, chunk.end_line) == (1, 2)


def test_file_without_trailing_newline():
    (chunk,) = functions(b"def f():\n    pass")

    assert chunk.text == "def f():\n    pass"


# --- identity --------------------------------------------------------------


def test_chunking_is_deterministic():
    source = b"def a():\n    pass\n\ndef b():\n    pass\n"

    assert chunk_source(source, PATH) == chunk_source(source, PATH)


def test_id_survives_moving_the_code_to_other_lines():
    (before,) = functions(b"def f():\n    pass\n")
    (after,) = functions(b"# new header\n\n\n\ndef f():\n    pass\n")

    assert after.start_line != before.start_line
    assert after.id == before.id


def test_identical_definitions_get_distinct_ids_in_source_order():
    first, second, third = functions(b"def f(): ...\n" * 3)

    assert second.id == f"{first.id}-2"
    assert third.id == f"{first.id}-3"


def test_same_code_in_another_file_has_another_id():
    (one,) = functions(b"def f(): ...\n", "a.py")
    (two,) = functions(b"def f(): ...\n", "b.py")

    assert one.id != two.id


# --- file flags ------------------------------------------------------------


@pytest.mark.parametrize(("path", "expected"), [("pkg/mod.py", False), ("tests/test_mod.py", True)])
def test_is_test_comes_from_the_path(path, expected):
    (chunk,) = functions(b"def f(): ...\n", path)

    assert chunk.is_test is expected


def test_syntax_errors_are_flagged_on_every_chunk_of_the_file():
    source = b"def broken(:\n    pass\n\ndef fine():\n    pass\n"

    chunks = functions(source)

    assert chunks
    assert all(chunk.has_error for chunk in chunks)


def test_valid_source_is_not_flagged():
    (chunk,) = functions(b"def f(): ...\n")

    assert chunk.has_error is False


@pytest.mark.parametrize(
    "source",
    [b"def (:\n", b"def\n", b"@\n", b"x = (\ndef f(", b"\xff\xfe def f(): \xfa\n", b"\n\n"],
)
def test_broken_input_never_raises(source):
    chunks = chunk_source(source, PATH)

    assert all(isinstance(chunk, Chunk) for chunk in chunks)
