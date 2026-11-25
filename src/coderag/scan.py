import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from pathspec import GitIgnoreSpec

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


# Directory components that mark everything below them as test code.
TEST_DIR_NAMES: frozenset[str] = frozenset({"tests", "test"})


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
    # Directories os.walk could not list; their contents are missing from the result.
    unreadable_dirs: tuple[str, ...]  # relative to the repo root, "/" separated

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


def is_test_path(path: str) -> bool:
    """Tell whether a repo-relative, "/" separated path points at test code.

    Directory rule: any directory component (not the file name) is in TEST_DIR_NAMES.
    File rule: the name is conftest.py, test_*.py or *_test.py. A bare test.py is
    not a test. Matching is case-sensitive.
    """
    *directories, name = path.split("/")
    if any(part in TEST_DIR_NAMES for part in directories):
        return True
    return (
        name == "conftest.py"
        or (name.startswith("test_") and name.endswith(".py"))
        or name.endswith("_test.py")
    )


def load_gitignore(root: Path) -> GitIgnoreSpec:
    """Load the root .gitignore as a spec; a missing file gives an empty spec.

    Only <root>/.gitignore is read: no nested .gitignore files, no
    .git/info/exclude, no global ignore file. Other read errors propagate.
    """
    try:
        text = (root / ".gitignore").read_text(encoding="utf-8")
    except FileNotFoundError:
        return GitIgnoreSpec.from_lines([])
    return GitIgnoreSpec.from_lines(text.splitlines())


def _classify_file(
    file_path: Path, relative: str, gitignore: GitIgnoreSpec, max_file_size_bytes: int
) -> IncludedFile | ExcludedFile:
    """Decide the fate of one .py file; the first matching rule wins (K1, K2).

    Order: symlink, gitignore, size, readability. A rule only runs if every earlier
    rule passed, so e.g. a gitignored file is never stat-ed.
    """
    # islink() looks at the link itself (lstat), so the target is never touched. Unlike
    # Path.is_symlink() on Python 3.12, it treats any OSError as "not a symlink", so an
    # lstat failure falls through to the stat step below and ends up as UNREADABLE.
    if os.path.islink(file_path):
        return ExcludedFile(relative, ExclusionReason.SYMLINK)
    if gitignore.match_file(relative):
        return ExcludedFile(relative, ExclusionReason.GITIGNORED)

    try:
        size_bytes = file_path.stat().st_size
    except OSError:
        return ExcludedFile(relative, ExclusionReason.UNREADABLE)
    if size_bytes > max_file_size_bytes:  # equal to the limit is still included
        return ExcludedFile(relative, ExclusionReason.TOO_LARGE, size_bytes)

    # The scanner never reads contents, so open and close the file to find out
    # whether it could be read (e.g. a PermissionError).
    try:
        with file_path.open("rb"):
            pass
    except OSError:
        return ExcludedFile(relative, ExclusionReason.UNREADABLE)

    return IncludedFile(path=relative, size_bytes=size_bytes, is_test=is_test_path(relative))


def scan(root: Path, max_file_size_bytes: int) -> ScanResult:
    """Walk root and list the .py files to index.

    Returns the included files, every excluded file with a single reason code,
    the pruned directories and the directories that could not be listed.
    Raises ValueError for a non-positive size limit, FileNotFoundError or
    NotADirectoryError for a bad root, and OSError if the root cannot be listed.
    """
    if max_file_size_bytes <= 0:
        raise ValueError("max_file_size_bytes must be > 0")
    if not root.exists():
        raise FileNotFoundError(f"scan root does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"scan root is not a directory: {root}")

    gitignore = load_gitignore(root)
    included: list[IncludedFile] = []
    excluded: list[ExcludedFile] = []
    pruned_dirs: list[str] = []
    unreadable_dirs: list[str] = []

    def record_unlistable(error: OSError) -> None:
        # os.walk silently skips directories it cannot list unless we ask to hear about it.
        failed = Path(error.filename) if error.filename is not None else None
        if failed is None or failed == root:
            raise error  # an unlistable root is a caller problem, like a missing root
        unreadable_dirs.append(failed.relative_to(root).as_posix())

    # followlinks=False: symlinked directories are listed but never entered.
    # Known limit: Windows junctions are not reported as symlinks, so they may be followed.
    for dirpath, dirnames, filenames in os.walk(root, onerror=record_unlistable, followlinks=False):
        current = Path(dirpath)

        kept: list[str] = []
        for dirname in dirnames:
            if dirname in PRUNED_DIR_NAMES:
                pruned_dirs.append((current / dirname).relative_to(root).as_posix())
            else:
                kept.append(dirname)
        # Assign in place: os.walk only skips what is removed from this very list.
        dirnames[:] = kept

        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            file_path = current / filename
            relative = file_path.relative_to(root).as_posix()
            outcome = _classify_file(file_path, relative, gitignore, max_file_size_bytes)
            if isinstance(outcome, IncludedFile):
                included.append(outcome)
            else:
                excluded.append(outcome)

    # Sort on the "/" separated string, not on walk order, so results are deterministic.
    included.sort(key=lambda file: file.path)
    excluded.sort(key=lambda file: file.path)
    pruned_dirs.sort()
    unreadable_dirs.sort()
    return ScanResult(
        root=root,
        included=tuple(included),
        excluded=tuple(excluded),
        pruned_dirs=tuple(pruned_dirs),
        unreadable_dirs=tuple(unreadable_dirs),
    )
