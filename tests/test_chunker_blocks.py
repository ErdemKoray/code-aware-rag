from functools import partial

import pytest

from coderag.chunking import chunker
from coderag.chunking.model import Chunk, ChunkKind

PATH = "pkg/mod.py"
# Large enough that nothing is split here; splitting has its own tests.
chunk_source = partial(chunker.chunk_source, max_chunk_bytes=4_000)


def summary(source: bytes) -> list[tuple[str, str | None, int, int]]:
    return [
        (c.kind.value, c.qualname, c.start_line, c.end_line) for c in chunk_source(source, PATH)
    ]


def assert_lines_covered_exactly_once(source: bytes, chunks: tuple[Chunk, ...]) -> None:
    lines = source.split(b"\n")
    owners = [0] * len(lines)
    for chunk in chunks:
        cited = b"\n".join(lines[chunk.start_line - 1 : chunk.end_line])
        assert chunk.text == cited.decode("utf-8", errors="replace")
        for index in range(chunk.start_line - 1, chunk.end_line):
            owners[index] += 1
    for number, (line, count) in enumerate(zip(lines, owners, strict=True), start=1):
        if line.strip():
            assert count == 1, f"line {number} {line!r} is in {count} chunks"
        else:
            assert count <= 1, f"blank line {number} is in {count} chunks"


# --- module blocks ---------------------------------------------------------


def test_code_around_definitions_becomes_module_chunks():
    source = b"import os\nimport sys\n\ndef f():\n    pass\n\nX = 1\n\nclass A:\n    pass\n\nf()\n"

    assert summary(source) == [
        ("module", None, 1, 2),
        ("function", "f", 4, 5),
        ("module", None, 7, 7),
        ("class", "A", 9, 10),
        ("module", None, 12, 12),
    ]


def test_module_chunk_context_is_only_the_path():
    (chunk,) = chunk_source(b"import os\n", PATH)

    assert chunk.context == PATH
    assert chunk.qualname is None
    assert chunk.defined_names == ()


def test_file_without_definitions_is_one_module_chunk():
    source = b'"""Re-exports."""\n\nfrom a import b\n\nfrom c import d\n'

    assert summary(source) == [("module", None, 1, 5)]


def test_blank_edges_are_not_part_of_a_block():
    assert summary(b"\n\n  \nX = 1\n\n\n") == [("module", None, 4, 4)]


@pytest.mark.parametrize("source", [b"", b"\n", b"  \n\t\n\r\n"])
def test_blank_files_have_no_chunks(source):
    assert chunk_source(source, PATH) == ()


# --- comments above definitions --------------------------------------------


def test_comment_directly_above_a_function_belongs_to_it():
    source = b"X = 1\n\n# about f\n# more\ndef f():\n    pass\n"

    assert summary(source) == [("module", None, 1, 1), ("function", "f", 3, 6)]


def test_comment_above_a_decorator_belongs_to_the_definition():
    assert summary(b"# about\n@dec\ndef f():\n    pass\n") == [("function", "f", 1, 4)]


def test_comment_separated_by_a_blank_line_stays_in_the_module():
    source = b"# section\n\ndef f():\n    pass\n"

    assert summary(source) == [("module", None, 1, 1), ("function", "f", 3, 4)]


def test_trailing_comment_on_a_code_line_is_not_attached():
    source = b"X = 1  # about X\ndef f():\n    pass\n"

    assert summary(source) == [("module", None, 1, 1), ("function", "f", 2, 3)]


def test_hash_line_inside_a_string_is_not_a_comment():
    source = b'X = """\n# not a comment"""\ndef f():\n    pass\n'

    assert summary(source) == [("module", None, 1, 2), ("function", "f", 3, 4)]


def test_comment_inside_the_previous_function_is_not_taken_over():
    source = b"def a():\n    pass  # done\ndef b():\n    pass\n"

    assert summary(source) == [("function", "a", 1, 2), ("function", "b", 3, 4)]


def test_comment_above_a_method_ends_the_class_header_before_it():
    source = b"class A:\n    x = 1\n    # about f\n    def f(self):\n        pass\n"

    assert summary(source) == [("class_header", "A", 1, 2), ("method", "A.f", 3, 5)]


def test_comment_right_after_the_class_line_goes_to_the_first_method():
    source = b"class A:\n    # about f\n    def f(self):\n        pass\n"

    assert summary(source) == [("class_header", "A", 1, 1), ("method", "A.f", 2, 4)]


def test_comment_above_a_class_belongs_to_its_header():
    source = b"# about A\nclass A:\n    def f(self):\n        pass\n"

    assert summary(source) == [("class_header", "A", 1, 2), ("method", "A.f", 3, 4)]


# --- class blocks ----------------------------------------------------------


CLASS_WITH_BLOCKS = b"""class A(Base):
    def f(self):
        pass

    alias = f
    other = 2

    def g(self):
        pass

    last = g
"""


def test_code_between_and_after_methods_becomes_class_blocks():
    assert summary(CLASS_WITH_BLOCKS) == [
        ("class_header", "A", 1, 1),
        ("method", "A.f", 2, 3),
        ("class_block", "A", 5, 6),
        ("method", "A.g", 8, 9),
        ("class_block", "A", 11, 11),
    ]


def test_class_block_context_holds_the_class_signature():
    block = next(
        c for c in chunk_source(CLASS_WITH_BLOCKS, PATH) if c.kind is ChunkKind.CLASS_BLOCK
    )

    assert block.context == "pkg/mod.py\nA\nclass A(Base):"


# --- compound statements (definitions without their own chunk) -------------


def test_fallback_class_stays_in_the_module_chunk_and_is_named():
    source = (
        b"import os\n"
        b"try:\n"
        b"    from x import Color\n"
        b"except ImportError:\n"
        b"\n"
        b"    class Color:\n"
        b"        def f(self):\n"
        b"            pass\n"
    )

    (chunk,) = chunk_source(source, PATH)

    assert chunk.kind is ChunkKind.MODULE
    assert (chunk.start_line, chunk.end_line) == (1, 8)
    assert chunk.defined_names == ("Color",)


def test_defined_names_go_to_the_block_that_holds_them():
    source = (
        b"if A:\n    def a():\n        pass\n\ndef middle(): ...\n\n"
        b"if B:\n    class B:\n        pass\nelse:\n    def c():\n        pass\n"
    )

    first, _, last = chunk_source(source, PATH)

    assert first.defined_names == ("a",)
    assert last.defined_names == ("B", "c")


def test_definitions_in_compound_statements_in_a_class_are_qualified():
    source = (
        b"class A:\n"
        b"    if X:\n"
        b"        def hidden(self):\n"
        b"            pass\n"
        b"    def f(self):\n"
        b"        pass\n"
        b"    try:\n"
        b"        def other(self): ...\n"
        b"    except E:\n"
        b"        pass\n"
    )

    header, method, block = chunk_source(source, PATH)

    assert header.defined_names == ("A.hidden",)
    assert method.defined_names == ()
    assert block.defined_names == ("A.other",)


def test_unsplit_class_names_its_conditional_methods():
    source = b"class A:\n    if X:\n        def f(self):\n            pass\n"

    (chunk,) = chunk_source(source, PATH)

    assert chunk.defined_names == ("A.f",)


def test_very_deep_expression_trees_do_not_overflow():
    source = b"X = " + b" + ".join([b"1"] * 5000) + b"\n"

    assert summary(source) == [("module", None, 1, 1)]


# --- every line exactly once -----------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        CLASS_WITH_BLOCKS,
        b"# top\n\nimport a\n# above\n@d\ndef f():\n    x = 1\n    # inner end\n# after\n\ny = 2\n",
        b"class A:\n    '''Doc.'''\n    class B:\n        pass\n    # tail\n\n    x = 1\n",
        b"class A: pass\nx = 1; y = 2\ndef f(): return 1\n",
        b"def a():\n    pass\n    # deeper, before the next def\ndef b():\n    pass\n",
        b"def broken(:\n    pass\n\nclass B(\n    x = 1\n",
        b"x = (\ndef f():\n    pass\nclass\n@\n",
        b"class A:\n    def f(self): pass\n  bad = 1\n",
        b"import a\r\n\r\ndef f():\r\n    pass\r\n",
        b"X = 1 \\\n    + 2\ndef f():\n    pass",
    ],
)
def test_every_non_blank_line_is_in_exactly_one_chunk(source):
    assert_lines_covered_exactly_once(source, chunk_source(source, PATH))
