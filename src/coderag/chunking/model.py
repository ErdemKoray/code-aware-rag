import hashlib
from dataclasses import dataclass
from enum import StrEnum


class ChunkKind(StrEnum):
    MODULE = "module"  # module-level code that is not a function or class
    FUNCTION = "function"
    CLASS = "class"  # a class without methods, kept whole
    CLASS_HEADER = "class_header"  # a class up to its first method
    METHOD = "method"
    CLASS_BLOCK = "class_block"  # class-level code between or after methods


def make_chunk_id(
    path: str, qualname: str | None, kind: ChunkKind, text: str, occurrence: int = 1
) -> str:
    """Content-based chunk id: it does not change when the code only moves to other lines.

    occurrence numbers chunks that are otherwise identical, in source order: the first
    gets the plain digest, later ones get "-2", "-3" and so on.
    """
    if occurrence < 1:
        raise ValueError("occurrence must be >= 1")
    # NUL cannot appear in a path or a name, so the parts cannot run into each other.
    payload = "\0".join((path, qualname or "", kind.value, text))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return digest if occurrence == 1 else f"{digest}-{occurrence}"


# kw_only: later sprints add fields with defaults without breaking existing callers.
@dataclass(frozen=True, slots=True, kw_only=True)
class Chunk:
    id: str
    path: str  # relative to the repo root, "/" separated
    kind: ChunkKind
    qualname: str | None  # dotted name inside the file; None only for module chunks
    start_line: int  # 1-based, inclusive
    end_line: int  # 1-based, inclusive
    text: str  # exactly the source lines start_line..end_line
    context: str  # path, name and class signature; added to the text when embedding
    is_test: bool
    has_error: bool  # the file this chunk comes from has syntax errors
    defined_names: tuple[str, ...] = ()  # definitions without a chunk of their own
    part: int = 1  # 1-based index when a unit is split for size
    part_count: int = 1

    def __post_init__(self) -> None:
        if not 1 <= self.start_line <= self.end_line:
            raise ValueError(f"invalid line range {self.start_line}-{self.end_line}")
        # Citations rely on this: the text and the line range must describe the same lines.
        if self.text.count("\n") != self.end_line - self.start_line:
            raise ValueError("text must hold exactly the lines start_line..end_line")
        if not 1 <= self.part <= self.part_count:
            raise ValueError(f"invalid part {self.part}/{self.part_count}")
        if (self.qualname is None) != (self.kind is ChunkKind.MODULE):
            raise ValueError("module chunks, and only they, have no qualname")

    @property
    def size_bytes(self) -> int:
        """UTF-8 size of the text; the chunk size limit applies to this."""
        return len(self.text.encode("utf-8"))
