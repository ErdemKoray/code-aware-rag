from dataclasses import FrozenInstanceError

import pytest

from coderag.chunking.model import Chunk, ChunkKind, make_chunk_id


def make_chunk(**overrides) -> Chunk:
    fields = {
        "id": "abc",
        "path": "pkg/mod.py",
        "kind": ChunkKind.FUNCTION,
        "qualname": "f",
        "start_line": 3,
        "end_line": 4,
        "text": "def f():\n    pass",
        "context": "pkg/mod.py\nf",
        "is_test": False,
        "has_error": False,
    }
    return Chunk(**{**fields, **overrides})


# --- ChunkKind -------------------------------------------------------------


def test_chunk_kinds_are_the_decided_set():
    assert [kind.value for kind in ChunkKind] == [
        "module",
        "function",
        "class",
        "class_header",
        "method",
        "class_block",
    ]


# --- Chunk -----------------------------------------------------------------


def test_chunk_defaults_describe_an_unsplit_unit():
    chunk = make_chunk()

    assert (chunk.part, chunk.part_count) == (1, 1)
    assert chunk.defined_names == ()


def test_chunk_is_frozen():
    chunk = make_chunk()

    with pytest.raises(FrozenInstanceError):
        chunk.text = "other"  # type: ignore[misc]


def test_chunk_arguments_are_keyword_only():
    with pytest.raises(TypeError):
        Chunk("abc", "pkg/mod.py")  # type: ignore[misc, call-arg]


def test_size_bytes_counts_utf8_bytes_not_characters():
    chunk = make_chunk(start_line=1, end_line=1, text="x = 'é'")

    assert len(chunk.text) == 7
    assert chunk.size_bytes == 8


@pytest.mark.parametrize(("start", "end"), [(0, 1), (-1, 0), (5, 4)])
def test_invalid_line_range_is_rejected(start, end):
    with pytest.raises(ValueError, match="invalid line range"):
        make_chunk(start_line=start, end_line=end)


@pytest.mark.parametrize("text", ["def f():", "def f():\n    pass\n"])
def test_text_must_match_the_line_range(text):
    with pytest.raises(ValueError, match="exactly the lines"):
        make_chunk(text=text)


@pytest.mark.parametrize(("part", "count"), [(0, 1), (2, 1), (1, 0)])
def test_invalid_part_is_rejected(part, count):
    with pytest.raises(ValueError, match="invalid part"):
        make_chunk(part=part, part_count=count)


def test_module_chunk_has_no_qualname():
    assert make_chunk(kind=ChunkKind.MODULE, qualname=None).qualname is None
    with pytest.raises(ValueError, match="qualname"):
        make_chunk(kind=ChunkKind.MODULE, qualname="f")


@pytest.mark.parametrize("kind", [k for k in ChunkKind if k is not ChunkKind.MODULE])
def test_other_chunks_need_a_qualname(kind):
    with pytest.raises(ValueError, match="qualname"):
        make_chunk(kind=kind, qualname=None)


# --- make_chunk_id ---------------------------------------------------------

BASE = ("pkg/mod.py", "f", ChunkKind.FUNCTION, "def f(): ...")


def test_chunk_id_is_deterministic_hex():
    first = make_chunk_id(*BASE)

    assert first == make_chunk_id(*BASE)
    assert len(first) == 16
    assert int(first, 16) >= 0


@pytest.mark.parametrize(
    "changed",
    [
        ("pkg/other.py", "f", ChunkKind.FUNCTION, "def f(): ..."),
        ("pkg/mod.py", "g", ChunkKind.FUNCTION, "def f(): ..."),
        ("pkg/mod.py", "f", ChunkKind.METHOD, "def f(): ..."),
        ("pkg/mod.py", "f", ChunkKind.FUNCTION, "def f(): pass"),
    ],
)
def test_chunk_id_depends_on_every_component(changed):
    assert make_chunk_id(*changed) != make_chunk_id(*BASE)


def test_chunk_id_parts_do_not_run_into_each_other():
    left = make_chunk_id("ab", "c", ChunkKind.FUNCTION, "x")
    right = make_chunk_id("a", "bc", ChunkKind.FUNCTION, "x")

    assert left != right


def test_chunk_id_numbers_identical_chunks():
    first = make_chunk_id(*BASE)

    assert make_chunk_id(*BASE, occurrence=1) == first
    assert make_chunk_id(*BASE, occurrence=2) == f"{first}-2"
    assert make_chunk_id(*BASE, occurrence=3) == f"{first}-3"


def test_chunk_id_rejects_occurrence_below_one():
    with pytest.raises(ValueError, match="occurrence"):
        make_chunk_id(*BASE, occurrence=0)
