from functools import partial

from coderag.chunking import chunker
from coderag.chunking.model import Chunk, ChunkKind

PATH = "pkg/mod.py"
# Large enough that nothing is split here; splitting has its own tests.
chunk_source = partial(chunker.chunk_source, max_chunk_bytes=4_000)


def summary(chunks: tuple[Chunk, ...]) -> list[tuple[str, str | None, int, int]]:
    return [(c.kind.value, c.qualname, c.start_line, c.end_line) for c in chunks]


SERVICE = b'''@register
class Service(Base):
    """Doc."""

    timeout: int = 1

    def start(self):
        pass

    @property
    async def state(self):
        return 1
'''


# --- classes without methods -----------------------------------------------


def test_class_without_methods_is_one_chunk():
    source = b"@dataclass\nclass Point:\n    x: int = 0\n    y: int = 0\n"

    (chunk,) = chunk_source(source, PATH)

    assert chunk.kind is ChunkKind.CLASS
    assert chunk.qualname == "Point"
    assert (chunk.start_line, chunk.end_line) == (1, 4)
    assert chunk.text.startswith("@dataclass")
    assert chunk.context == "pkg/mod.py\nPoint"


def test_method_inside_a_compound_statement_does_not_split_the_class():
    source = b"class A:\n    if X:\n        def f(self):\n            pass\n"

    assert summary(chunk_source(source, PATH)) == [("class", "A", 1, 4)]


def test_one_line_class_with_a_method_stays_whole():
    source = b"class A: pass\nclass B: x = 1\n"

    assert [c.kind for c in chunk_source(source, PATH)] == [ChunkKind.CLASS] * 2


def test_member_on_the_header_line_keeps_the_class_whole():
    source = b"class A(\n    Base\n): x = 1\n"

    assert summary(chunk_source(source, PATH)) == [("class", "A", 1, 3)]


# --- split classes ---------------------------------------------------------


def test_class_with_methods_is_always_split_even_when_small():
    chunks = chunk_source(b"class A:\n    def f(self):\n        pass\n", PATH)

    assert summary(chunks) == [("class_header", "A", 1, 1), ("method", "A.f", 2, 3)]


def test_header_runs_from_the_decorator_to_the_line_before_the_first_method():
    header, *_ = chunk_source(SERVICE, PATH)

    assert header.kind is ChunkKind.CLASS_HEADER
    assert (header.start_line, header.end_line) == (1, 5)
    assert header.text == '@register\nclass Service(Base):\n    """Doc."""\n\n    timeout: int = 1'


def test_header_context_lists_method_names_only():
    header, *_ = chunk_source(SERVICE, PATH)

    assert header.context == "pkg/mod.py\nService\ndef start\nasync def state"


def test_each_method_is_its_own_chunk_with_decorators():
    _, start, state = chunk_source(SERVICE, PATH)

    assert summary((start, state)) == [
        ("method", "Service.start", 7, 8),
        ("method", "Service.state", 10, 12),
    ]
    assert state.text.startswith("    @property")


def test_method_context_holds_path_name_and_class_signature():
    _, start, _ = chunk_source(SERVICE, PATH)

    assert start.context == "pkg/mod.py\nService.start\nclass Service(Base):"


def test_multi_line_class_signature_is_kept_in_the_method_context():
    source = b"class A(\n    Base,\n    metaclass=Meta,\n):\n    def f(self):\n        pass\n"

    header, method = chunk_source(source, PATH)

    assert method.context == "pkg/mod.py\nA.f\nclass A(\n    Base,\n    metaclass=Meta,\n):"
    assert (header.start_line, header.end_line) == (1, 4)


def test_nested_function_stays_inside_its_method():
    source = b"class A:\n    def f(self):\n        def g():\n            pass\n        return g\n"

    assert summary(chunk_source(source, PATH)) == [
        ("class_header", "A", 1, 1),
        ("method", "A.f", 2, 5),
    ]


def test_methods_with_the_same_name_get_distinct_ids():
    source = (
        b"class A:\n"
        b"    @property\n    def x(self):\n        return 1\n"
        b"    @x.setter\n    def x(self, v):\n        pass\n"
    )

    header, getter, setter = chunk_source(source, PATH)

    assert getter.qualname == setter.qualname == "A.x"
    assert getter.id != setter.id
    assert header.context.endswith("def x\ndef x")


# --- inner classes ---------------------------------------------------------


def test_inner_class_ends_the_header_and_gets_its_own_chunk():
    source = (
        b"class Outer:\n"
        b"    a = 1\n"
        b"    class Config:\n"
        b"        frozen = True\n"
        b"    def f(self):\n"
        b"        pass\n"
    )

    chunks = chunk_source(source, PATH)

    assert summary(chunks) == [
        ("class_header", "Outer", 1, 2),
        ("class", "Outer.Config", 3, 4),
        ("method", "Outer.f", 5, 6),
    ]
    # The method list names methods, not inner classes.
    assert chunks[0].context == "pkg/mod.py\nOuter\ndef f"


def test_class_with_only_an_inner_class_is_split():
    source = b"class Outer:\n    class Inner:\n        x = 1\n"

    chunks = chunk_source(source, PATH)

    assert summary(chunks) == [("class_header", "Outer", 1, 1), ("class", "Outer.Inner", 2, 3)]
    assert chunks[0].context == "pkg/mod.py\nOuter"


def test_inner_class_with_methods_is_split_by_the_same_rule():
    source = b"class A:\n    class B:\n        def g(self):\n            pass\n"

    chunks = chunk_source(source, PATH)

    assert summary(chunks) == [
        ("class_header", "A", 1, 1),
        ("class_header", "A.B", 2, 2),
        ("method", "A.B.g", 3, 4),
    ]
    assert chunks[2].context == "pkg/mod.py\nA.B.g\nclass B:"


# --- order and robustness --------------------------------------------------


def test_functions_and_classes_come_out_in_source_order():
    source = b"def a(): ...\nclass B:\n    def c(self): ...\ndef d(): ...\n"

    assert [c.qualname for c in chunk_source(source, PATH)] == ["a", "B", "B.c", "d"]


def test_broken_class_never_raises():
    for source in (b"class\n", b"class A(:\n    def f(self): pass\n", b"class A:\n    def (:\n"):
        chunk_source(source, PATH)
