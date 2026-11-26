"""Check that the FastAPI clone is at the version pinned in the settings.

Evaluation results are only comparable if the target repository never drifts. The clone
lives in data/repos/ (gitignored), so these tests skip themselves when it is missing.
"""

import subprocess
from pathlib import Path

import pytest

from coderag.config import Settings


@pytest.fixture(scope="module")
def settings() -> Settings:
    return Settings()


@pytest.fixture(scope="module")
def clone(settings: Settings) -> Path:
    root = settings.fastapi_repo_path
    # Without its own .git, `git -C` would silently answer for the enclosing repository.
    if not (root / ".git").exists():
        pytest.skip(f"FastAPI clone not found at {root}")
    return root


def rev_parse(repo: Path, revision: str) -> str:
    """Resolve a revision to a commit SHA without writing anything to the repository."""
    return subprocess.run(
        ["git", "--no-optional-locks", "-C", str(repo), "rev-parse", "--verify", revision],
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()


def test_clone_head_matches_pinned_sha(settings, clone):
    assert rev_parse(clone, "HEAD^{commit}") == settings.fastapi_sha


def test_pinned_tag_points_to_pinned_sha(settings, clone):
    tag = f"refs/tags/{settings.fastapi_tag}^{{commit}}"

    assert rev_parse(clone, tag) == settings.fastapi_sha
