import os
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from coderag.scan import (
    PRUNED_DIR_NAMES,
    ExcludedFile,
    ExclusionReason,
    IncludedFile,
    ScanResult,
    is_test_path,
    load_gitignore,
    scan,
)


def make_result(
    included: tuple[IncludedFile, ...] = (),
    excluded: tuple[ExcludedFile, ...] = (),
) -> ScanResult:
    return ScanResult(
        root=Path("repo"),
        included=included,
        excluded=excluded,
        pruned_dirs=(),
        unreadable_dirs=(),
    )


def too_large(path: str, size: int) -> ExcludedFile:
    return ExcludedFile(path, ExclusionReason.TOO_LARGE, size)


# --- ExclusionReason -------------------------------------------------------


def test_exclusion_reason_members_follow_check_order():
    assert list(ExclusionReason) == [
        ExclusionReason.SYMLINK,
        ExclusionReason.GITIGNORED,
        ExclusionReason.TOO_LARGE,
        ExclusionReason.UNREADABLE,
    ]


def test_exclusion_reason_values_are_plain_strings():
    assert ExclusionReason.TOO_LARGE == "too_large"
    assert f"{ExclusionReason.SYMLINK}" == "symlink"


# --- PRUNED_DIR_NAMES ------------------------------------------------------


def test_pruned_dir_names_matches_decided_list():
    expected = {
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

    assert expected == PRUNED_DIR_NAMES


def test_pruned_dir_names_is_immutable():
    assert isinstance(PRUNED_DIR_NAMES, frozenset)


# --- frozen records --------------------------------------------------------


def test_included_file_is_frozen():
    file = IncludedFile("a.py", 10, False)

    with pytest.raises(FrozenInstanceError):
        file.size_bytes = 20  # type: ignore[misc]


def test_excluded_file_is_frozen():
    file = ExcludedFile("a.py", ExclusionReason.SYMLINK)

    with pytest.raises(FrozenInstanceError):
        file.reason = ExclusionReason.GITIGNORED  # type: ignore[misc]


def test_scan_result_is_frozen():
    result = make_result()

    with pytest.raises(FrozenInstanceError):
        result.root = Path("other")  # type: ignore[misc]


# --- ExcludedFile size rule ------------------------------------------------


def test_too_large_accepts_size():
    file = ExcludedFile("a.py", ExclusionReason.TOO_LARGE, 600_000)

    assert file.size_bytes == 600_000


def test_too_large_without_size_is_rejected():
    with pytest.raises(ValueError, match="TOO_LARGE"):
        ExcludedFile("a.py", ExclusionReason.TOO_LARGE)


@pytest.mark.parametrize(
    "reason",
    [ExclusionReason.SYMLINK, ExclusionReason.GITIGNORED, ExclusionReason.UNREADABLE],
)
def test_other_reasons_default_to_no_size(reason):
    assert ExcludedFile("a.py", reason).size_bytes is None


@pytest.mark.parametrize(
    "reason",
    [ExclusionReason.SYMLINK, ExclusionReason.GITIGNORED, ExclusionReason.UNREADABLE],
)
def test_other_reasons_reject_a_size(reason):
    with pytest.raises(ValueError, match=reason.name):
        ExcludedFile("a.py", reason, 10)


# --- test_count ------------------------------------------------------------


def test_test_count_counts_only_tagged_files():
    result = make_result(
        included=(
            IncludedFile("app.py", 10, False),
            IncludedFile("tests/test_app.py", 10, True),
            IncludedFile("conftest.py", 10, True),
        ),
    )

    assert result.test_count == 2


def test_test_count_is_zero_for_empty_result():
    assert make_result().test_count == 0


# --- exclusion_counts ------------------------------------------------------


def test_exclusion_counts_includes_zero_reasons():
    assert dict(make_result().exclusion_counts) == {
        ExclusionReason.SYMLINK: 0,
        ExclusionReason.GITIGNORED: 0,
        ExclusionReason.TOO_LARGE: 0,
        ExclusionReason.UNREADABLE: 0,
    }


def test_exclusion_counts_sums_repeated_reasons():
    result = make_result(
        excluded=(
            ExcludedFile("a.py", ExclusionReason.GITIGNORED),
            ExcludedFile("b.py", ExclusionReason.GITIGNORED),
            too_large("c.py", 600_000),
            ExcludedFile("d.py", ExclusionReason.SYMLINK),
        ),
    )

    assert dict(result.exclusion_counts) == {
        ExclusionReason.SYMLINK: 1,
        ExclusionReason.GITIGNORED: 2,
        ExclusionReason.TOO_LARGE: 1,
        ExclusionReason.UNREADABLE: 0,
    }


def test_exclusion_counts_keeps_enum_order():
    result = make_result(excluded=(ExcludedFile("a.py", ExclusionReason.UNREADABLE),))

    assert list(result.exclusion_counts) == list(ExclusionReason)


# --- largest ---------------------------------------------------------------


def test_largest_mixes_included_and_too_large_only():
    result = make_result(
        included=(IncludedFile("small.py", 100, False), IncludedFile("mid.py", 400, False)),
        excluded=(
            too_large("huge.py", 900),
            ExcludedFile("link.py", ExclusionReason.SYMLINK),
            ExcludedFile("ignored.py", ExclusionReason.GITIGNORED),
            ExcludedFile("broken.py", ExclusionReason.UNREADABLE),
        ),
    )

    assert result.largest() == (("huge.py", 900), ("mid.py", 400), ("small.py", 100))


def test_largest_breaks_size_ties_by_path_ascending():
    result = make_result(
        included=(IncludedFile("b.py", 50, False), IncludedFile("a.py", 50, False)),
        excluded=(too_large("c.py", 50),),
    )

    assert result.largest() == (("a.py", 50), ("b.py", 50), ("c.py", 50))


def test_largest_defaults_to_five():
    result = make_result(
        included=tuple(IncludedFile(f"f{i}.py", i, False) for i in range(1, 8)),
    )

    assert result.largest() == (
        ("f7.py", 7),
        ("f6.py", 6),
        ("f5.py", 5),
        ("f4.py", 4),
        ("f3.py", 3),
    )


def test_largest_returns_everything_when_n_exceeds_count():
    result = make_result(included=(IncludedFile("a.py", 1, False),))

    assert result.largest(10) == (("a.py", 1),)


def test_largest_with_zero_is_empty():
    result = make_result(included=(IncludedFile("a.py", 1, False),))

    assert result.largest(0) == ()


def test_largest_rejects_negative_n():
    with pytest.raises(ValueError, match="n must be >= 0"):
        make_result().largest(-1)


def test_largest_is_empty_for_empty_result():
    assert make_result().largest() == ()


# --- is_test_path ----------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "tests/x.py",
        "test/x.py",
        "a/test/x.py",
        "scripts/tests/x.py",
        "tests/deep/er/x.py",
        "test_x.py",
        "pkg/test_x.py",
        "x_test.py",
        "pkg/x_test.py",
        "conftest.py",
        "pkg/conftest.py",
    ],
)
def test_is_test_path_detects_tests(path):
    assert is_test_path(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "app.py",
        "pkg/app.py",
        "test.py",  # a bare test.py is not a test
        "pkg/test.py",
        "latest.py",
        "contest.py",
        "x_tests.py",
        "testing/x.py",
        "pkg/tests.py",  # the directory rule only looks at directory components
        "Tests/x.py",  # case-sensitive
        "Test_x.py",
        "test_x.pyi",
    ],
)
def test_is_test_path_rejects_non_tests(path):
    assert is_test_path(path) is False


# --- load_gitignore --------------------------------------------------------


def write_gitignore(root: Path, content: str) -> None:
    (root / ".gitignore").write_text(content, encoding="utf-8")


def test_load_gitignore_without_file_matches_nothing(tmp_path):
    spec = load_gitignore(tmp_path)

    assert spec.match_file("app.py") is False
    assert spec.match_file("build/x.py") is False


def test_load_gitignore_empty_file_matches_nothing(tmp_path):
    write_gitignore(tmp_path, "")

    assert load_gitignore(tmp_path).match_file("app.py") is False


def test_load_gitignore_skips_comments_and_blank_lines(tmp_path):
    write_gitignore(tmp_path, "# a comment\n\n   \nignored.py\n")

    spec = load_gitignore(tmp_path)

    assert spec.match_file("ignored.py") is True
    assert spec.match_file("# a comment") is False
    assert spec.match_file("other.py") is False


def test_load_gitignore_glob_matches_at_any_depth(tmp_path):
    write_gitignore(tmp_path, "*_generated.py\n")

    spec = load_gitignore(tmp_path)

    assert spec.match_file("a_generated.py") is True
    assert spec.match_file("pkg/sub/a_generated.py") is True
    assert spec.match_file("a_generated.txt") is False


def test_load_gitignore_directory_pattern_matches_files_below(tmp_path):
    write_gitignore(tmp_path, "build/\n")

    spec = load_gitignore(tmp_path)

    assert spec.match_file("build/x.py") is True
    assert spec.match_file("build/deep/x.py") is True
    assert spec.match_file("pkg/build/x.py") is True
    assert spec.match_file("rebuild/x.py") is False


def test_load_gitignore_negation_reincludes_a_file(tmp_path):
    write_gitignore(tmp_path, "*.py\n!keep.py\n")

    spec = load_gitignore(tmp_path)

    assert spec.match_file("drop.py") is True
    assert spec.match_file("keep.py") is False


def test_load_gitignore_leading_slash_anchors_to_root(tmp_path):
    write_gitignore(tmp_path, "/x.py\n")

    spec = load_gitignore(tmp_path)

    assert spec.match_file("x.py") is True
    assert spec.match_file("a/x.py") is False


def test_load_gitignore_reads_utf8(tmp_path):
    write_gitignore(tmp_path, "ünï.py\n")

    assert load_gitignore(tmp_path).match_file("ünï.py") is True


def test_load_gitignore_ignores_nested_gitignore_files(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / ".gitignore").write_text("x.py\n", encoding="utf-8")

    assert load_gitignore(tmp_path).match_file("pkg/x.py") is False


# --- scan: skeleton (validation, walking, pruning, ordering) ---------------

MAX_SIZE = 500_000


def touch(root: Path, relative: str, content: bytes = b"") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


@pytest.mark.parametrize("value", [0, -1])
def test_scan_rejects_non_positive_size_limit(tmp_path, value):
    with pytest.raises(ValueError, match="max_file_size_bytes"):
        scan(tmp_path, value)


def test_scan_missing_root_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="does not exist"):
        scan(tmp_path / "nope", MAX_SIZE)


def test_scan_file_root_raises(tmp_path):
    touch(tmp_path, "a.py")

    with pytest.raises(NotADirectoryError, match="not a directory"):
        scan(tmp_path / "a.py", MAX_SIZE)


def test_scan_empty_directory(tmp_path):
    result = scan(tmp_path, MAX_SIZE)

    assert result.root == tmp_path
    assert result.included == ()
    assert result.excluded == ()
    assert result.pruned_dirs == ()


def test_scan_only_lists_py_files(tmp_path):
    touch(tmp_path, "app.py")
    touch(tmp_path, "README.md")
    touch(tmp_path, "types.pyi")
    touch(tmp_path, "data.txt")
    touch(tmp_path, "noext")

    result = scan(tmp_path, MAX_SIZE)

    assert [file.path for file in result.included] == ["app.py"]
    assert result.excluded == ()


def test_scan_paths_are_relative_and_slash_separated(tmp_path):
    touch(tmp_path, "pkg/sub/mod.py")

    result = scan(tmp_path, MAX_SIZE)

    assert [file.path for file in result.included] == ["pkg/sub/mod.py"]
    assert "\\" not in result.included[0].path


def test_scan_records_file_size(tmp_path):
    touch(tmp_path, "a.py", b"x" * 10)

    result = scan(tmp_path, MAX_SIZE)

    assert result.included[0].size_bytes == 10


def test_scan_tags_test_files(tmp_path):
    touch(tmp_path, "app.py")
    touch(tmp_path, "tests/test_app.py")
    touch(tmp_path, "conftest.py")

    result = scan(tmp_path, MAX_SIZE)

    assert {file.path: file.is_test for file in result.included} == {
        "app.py": False,
        "conftest.py": True,
        "tests/test_app.py": True,
    }


def test_scan_sorts_by_slash_string_not_walk_order(tmp_path):
    # Created in reverse order. Plain string order puts "a.py" before "a/z.py"
    # because "." sorts before "/", which a directory-by-directory walk would not.
    touch(tmp_path, "b.py")
    touch(tmp_path, "a/z.py")
    touch(tmp_path, "a.py")

    result = scan(tmp_path, MAX_SIZE)

    assert [file.path for file in result.included] == ["a.py", "a/z.py", "b.py"]


def test_scan_prunes_fixed_directories_and_reports_them(tmp_path):
    touch(tmp_path, "keep.py")
    touch(tmp_path, "scripts/tool.py")
    touch(tmp_path, "pkg/scripts/deep.py")
    touch(tmp_path, "node_modules/lib/x.py")
    touch(tmp_path, ".venv/lib/y.py")

    result = scan(tmp_path, MAX_SIZE)

    assert [file.path for file in result.included] == ["keep.py"]
    assert result.pruned_dirs == (".venv", "node_modules", "pkg/scripts", "scripts")


def test_scan_prunes_by_exact_name_only(tmp_path):
    touch(tmp_path, "scripts_extra/a.py")
    touch(tmp_path, "my_build/b.py")

    result = scan(tmp_path, MAX_SIZE)

    assert [file.path for file in result.included] == ["my_build/b.py", "scripts_extra/a.py"]
    assert result.pruned_dirs == ()


def test_scan_does_not_follow_directory_symlinks(tmp_path):
    touch(tmp_path, "real/mod.py")
    try:
        os.symlink(tmp_path / "real", tmp_path / "link", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("cannot create symlinks in this environment")

    result = scan(tmp_path, MAX_SIZE)

    assert [file.path for file in result.included] == ["real/mod.py"]
    assert result.excluded == ()


# --- scan: symlink and gitignore rules -------------------------------------


def make_symlink(link: Path, target: Path) -> None:
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        pytest.skip("cannot create symlinks in this environment")


def excluded_by_path(result: ScanResult) -> dict[str, tuple[ExclusionReason, int | None]]:
    return {file.path: (file.reason, file.size_bytes) for file in result.excluded}


def test_scan_excludes_file_symlinks(tmp_path):
    touch(tmp_path, "real.py", b"x" * 10)
    make_symlink(tmp_path / "link.py", tmp_path / "real.py")

    result = scan(tmp_path, MAX_SIZE)

    assert [file.path for file in result.included] == ["real.py"]
    assert excluded_by_path(result) == {"link.py": (ExclusionReason.SYMLINK, None)}


def test_scan_excludes_broken_symlinks_without_failing(tmp_path):
    make_symlink(tmp_path / "dangling.py", tmp_path / "missing.py")

    result = scan(tmp_path, MAX_SIZE)

    assert result.included == ()
    assert excluded_by_path(result) == {"dangling.py": (ExclusionReason.SYMLINK, None)}


def test_scan_ignores_symlinks_that_are_not_py_files(tmp_path):
    touch(tmp_path, "real.py")
    make_symlink(tmp_path / "link.txt", tmp_path / "real.py")

    result = scan(tmp_path, MAX_SIZE)

    assert result.excluded == ()


def test_scan_excludes_gitignored_files_without_measuring_them(tmp_path):
    (tmp_path / ".gitignore").write_text("*_generated.py\n", encoding="utf-8")
    touch(tmp_path, "app.py")
    touch(tmp_path, "model_generated.py", b"x" * 10)
    touch(tmp_path, "pkg/deep_generated.py")

    result = scan(tmp_path, MAX_SIZE)

    assert [file.path for file in result.included] == ["app.py"]
    assert excluded_by_path(result) == {
        "model_generated.py": (ExclusionReason.GITIGNORED, None),
        "pkg/deep_generated.py": (ExclusionReason.GITIGNORED, None),
    }


def test_scan_does_not_prune_gitignored_directories(tmp_path):
    # Only the fixed PRUNED_DIR_NAMES are pruned (K3); gitignored directories are
    # walked and every file in them gets its own GITIGNORED record.
    (tmp_path / ".gitignore").write_text("out/\n", encoding="utf-8")
    touch(tmp_path, "out/a.py")
    touch(tmp_path, "out/sub/b.py")
    touch(tmp_path, "keep.py")

    result = scan(tmp_path, MAX_SIZE)

    assert [file.path for file in result.included] == ["keep.py"]
    assert sorted(excluded_by_path(result)) == ["out/a.py", "out/sub/b.py"]
    assert result.pruned_dirs == ()


def test_scan_honours_gitignore_negation(tmp_path):
    (tmp_path / ".gitignore").write_text("*.py\n!keep.py\n", encoding="utf-8")
    touch(tmp_path, "keep.py")
    touch(tmp_path, "drop.py")

    result = scan(tmp_path, MAX_SIZE)

    assert [file.path for file in result.included] == ["keep.py"]
    assert excluded_by_path(result) == {"drop.py": (ExclusionReason.GITIGNORED, None)}


def test_scan_without_gitignore_excludes_nothing(tmp_path):
    touch(tmp_path, "a.py")

    assert scan(tmp_path, MAX_SIZE).excluded == ()


def test_scan_symlink_wins_over_gitignore(tmp_path):
    (tmp_path / ".gitignore").write_text("*.py\n", encoding="utf-8")
    touch(tmp_path, "real.txt")
    make_symlink(tmp_path / "link.py", tmp_path / "real.txt")
    touch(tmp_path, "plain.py")

    result = scan(tmp_path, MAX_SIZE)

    assert excluded_by_path(result) == {
        "link.py": (ExclusionReason.SYMLINK, None),
        "plain.py": (ExclusionReason.GITIGNORED, None),
    }


def test_scan_sorts_excluded_by_path_and_counts_reasons(tmp_path):
    (tmp_path / ".gitignore").write_text("g*.py\n", encoding="utf-8")
    touch(tmp_path, "z_real.py")
    touch(tmp_path, "gb.py")
    touch(tmp_path, "ga.py")
    make_symlink(tmp_path / "a_link.py", tmp_path / "z_real.py")

    result = scan(tmp_path, MAX_SIZE)

    assert [file.path for file in result.excluded] == ["a_link.py", "ga.py", "gb.py"]
    assert dict(result.exclusion_counts) == {
        ExclusionReason.SYMLINK: 1,
        ExclusionReason.GITIGNORED: 2,
        ExclusionReason.TOO_LARGE: 0,
        ExclusionReason.UNREADABLE: 0,
    }


# --- scan: size and readability rules --------------------------------------


def fail_on(monkeypatch, method: str, *blocked: Path) -> None:
    """Make Path.<method> raise PermissionError for the given files only.

    Removing permissions is not reliable on Windows, so the failure is simulated.
    """
    real = getattr(Path, method)

    def fake(self, *args, **kwargs):
        if self in blocked:
            raise PermissionError(13, "Access is denied", str(self))
        return real(self, *args, **kwargs)

    monkeypatch.setattr(Path, method, fake)


def test_scan_size_limit_is_inclusive(tmp_path):
    touch(tmp_path, "exact.py", b"x" * 100)
    touch(tmp_path, "over.py", b"x" * 101)

    result = scan(tmp_path, 100)

    assert [file.path for file in result.included] == ["exact.py"]
    assert excluded_by_path(result) == {"over.py": (ExclusionReason.TOO_LARGE, 101)}


def test_scan_too_large_files_feed_largest(tmp_path):
    touch(tmp_path, "small.py", b"x" * 10)
    touch(tmp_path, "huge.py", b"x" * 500)

    result = scan(tmp_path, 100)

    assert result.largest(2) == (("huge.py", 500), ("small.py", 10))


def test_scan_excludes_file_when_stat_fails(tmp_path, monkeypatch):
    touch(tmp_path, "ok.py")
    touch(tmp_path, "broken.py")
    fail_on(monkeypatch, "stat", tmp_path / "broken.py")

    result = scan(tmp_path, MAX_SIZE)

    assert [file.path for file in result.included] == ["ok.py"]
    assert excluded_by_path(result) == {"broken.py": (ExclusionReason.UNREADABLE, None)}


def test_scan_excludes_file_when_open_fails_and_keeps_going(tmp_path, monkeypatch):
    touch(tmp_path, "a.py")
    touch(tmp_path, "locked.py", b"x" * 10)
    touch(tmp_path, "z.py")
    fail_on(monkeypatch, "open", tmp_path / "locked.py")

    result = scan(tmp_path, MAX_SIZE)

    assert [file.path for file in result.included] == ["a.py", "z.py"]
    assert excluded_by_path(result) == {"locked.py": (ExclusionReason.UNREADABLE, None)}
    assert result.exclusion_counts[ExclusionReason.UNREADABLE] == 1


def test_scan_too_large_wins_over_unreadable(tmp_path, monkeypatch):
    touch(tmp_path, "big_locked.py", b"x" * 200)
    fail_on(monkeypatch, "open", tmp_path / "big_locked.py")

    result = scan(tmp_path, 100)

    assert excluded_by_path(result) == {"big_locked.py": (ExclusionReason.TOO_LARGE, 200)}


def test_scan_gitignored_wins_over_size_and_is_never_stat_ed(tmp_path, monkeypatch):
    (tmp_path / ".gitignore").write_text("big.py\n", encoding="utf-8")
    touch(tmp_path, "big.py", b"x" * 200)
    fail_on(monkeypatch, "stat", tmp_path / "big.py")

    result = scan(tmp_path, 100)

    assert excluded_by_path(result) == {"big.py": (ExclusionReason.GITIGNORED, None)}


def test_scan_symlink_wins_over_size(tmp_path):
    touch(tmp_path, "real.txt", b"x" * 200)
    make_symlink(tmp_path / "link.py", tmp_path / "real.txt")

    result = scan(tmp_path, 100)

    assert excluded_by_path(result) == {"link.py": (ExclusionReason.SYMLINK, None)}


# --- scan: directories that cannot be listed -------------------------------


def block_listing(monkeypatch, *blocked: Path) -> None:
    """Make os.scandir fail with PermissionError for the given directories.

    Removing permissions is not reliable on Windows, so the failure is simulated.
    """
    real_scandir = os.scandir

    def fake_scandir(path="."):
        if Path(path) in blocked:
            raise PermissionError(13, "Access is denied", os.fspath(path))
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", fake_scandir)


def test_scan_reports_directories_it_cannot_list(tmp_path, monkeypatch):
    touch(tmp_path, "a.py")
    touch(tmp_path, "pkg/ok.py")
    touch(tmp_path, "pkg/locked/hidden.py")
    touch(tmp_path, "zzz/locked/hidden.py")
    block_listing(monkeypatch, tmp_path / "pkg" / "locked", tmp_path / "zzz" / "locked")

    result = scan(tmp_path, MAX_SIZE)

    assert [file.path for file in result.included] == ["a.py", "pkg/ok.py"]
    assert result.unreadable_dirs == ("pkg/locked", "zzz/locked")
    assert result.excluded == ()


def test_scan_without_listing_problems_has_no_unreadable_dirs(tmp_path):
    touch(tmp_path, "a.py")

    assert scan(tmp_path, MAX_SIZE).unreadable_dirs == ()


def test_scan_raises_when_root_cannot_be_listed(tmp_path, monkeypatch):
    touch(tmp_path, "a.py")
    block_listing(monkeypatch, tmp_path)

    with pytest.raises(PermissionError):
        scan(tmp_path, MAX_SIZE)
