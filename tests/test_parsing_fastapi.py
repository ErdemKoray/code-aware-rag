"""Parse every file of the pinned FastAPI clone.

The clone lives in data/repos/ (gitignored), so these tests skip themselves when it is
missing, e.g. in CI.
"""

import subprocess
from pathlib import Path

import pytest

from coderag.config import Settings
from coderag.parsing.python import parse
from coderag.scan import scan


@pytest.fixture(scope="module")
def repo_root() -> Path:
    root = Settings().fastapi_repo_path
    if not root.is_dir():
        pytest.skip(f"FastAPI clone not found at {root}")
    return root


def parse_failures(root: Path, relative_paths: list[str]) -> list[str]:
    """Return one line per file that raised or whose tree has errors."""
    failures = []
    for relative in relative_paths:
        try:
            result = parse((root / relative).read_bytes())
        except Exception as error:  # noqa: BLE001 - any exception is a failure to report
            failures.append(f"{relative}: raised {error!r}")
            continue
        if result.has_error:
            failures.append(f"{relative}: has_error")
    return failures


def test_every_scanned_file_parses_without_errors(repo_root):
    included = scan(repo_root, Settings().max_file_size_bytes).included

    assert len(included) > 0
    assert parse_failures(repo_root, [file.path for file in included]) == []


def test_every_tracked_python_file_parses_without_errors(repo_root):
    if not (repo_root / ".git").exists():
        pytest.skip(f"{repo_root} is not a git checkout")
    listing = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "-z", "*.py"],
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    tracked = [path for path in listing.split("\0") if path]

    assert len(tracked) > 0
    assert parse_failures(repo_root, tracked) == []
