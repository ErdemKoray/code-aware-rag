from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

# Directory names pruned during the walk; their contents are never visited.
PRUNED_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        "build",
        "dist",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "docs_src",
        "scripts",
    }
)


class ExclusionReason(StrEnum):
    """Why a .py file was left out. Members follow the scanner's check order."""

    SYMLINK = "symlink"
    GITIGNORED = "gitignored"
    TOO_LARGE = "too_large"
    UNREADABLE = "unreadable"


@dataclass(frozen=True, slots=True)
class IncludedFile:
    path: str  # relative to the repo root, "/" separated
    size_bytes: int
    is_test: bool


@dataclass(frozen=True, slots=True)
class ExcludedFile:
    path: str  # relative to the repo root, "/" separated
    reason: ExclusionReason
    # Required for TOO_LARGE; None for every other reason (size is never measured).
    size_bytes: int | None = None

    def __post_init__(self) -> None:
        if self.reason is ExclusionReason.TOO_LARGE:
            if self.size_bytes is None:
                raise ValueError("size_bytes is required when reason is TOO_LARGE")
        elif self.size_bytes is not None:
            raise ValueError(f"size_bytes must be None when reason is {self.reason.name}")


@dataclass(frozen=True, slots=True)
class ScanResult:
    root: Path
    included: tuple[IncludedFile, ...]
    excluded: tuple[ExcludedFile, ...]
    pruned_dirs: tuple[str, ...]  # relative to the repo root, "/" separated

    @property
    def test_count(self) -> int:
        """Number of included files tagged as tests."""
        return sum(1 for file in self.included if file.is_test)

    @property
    def exclusion_counts(self) -> Mapping[ExclusionReason, int]:
        """Exclusions per reason, in ExclusionReason order, zeros included."""
        counts = dict.fromkeys(ExclusionReason, 0)
        for file in self.excluded:
            counts[file.reason] += 1
        return counts

    def largest(self, n: int = 5) -> tuple[tuple[str, int], ...]:
        """Top n (path, size_bytes) pairs among included and TOO_LARGE files.

        Sorted by size descending, then path ascending.
        """
        if n < 0:
            raise ValueError("n must be >= 0")
        sized = [(file.path, file.size_bytes) for file in self.included]
        sized += [
            (file.path, file.size_bytes)
            for file in self.excluded
            if file.reason is ExclusionReason.TOO_LARGE and file.size_bytes is not None
        ]
        sized.sort(key=lambda pair: (-pair[1], pair[0]))
        return tuple(sized[:n])
