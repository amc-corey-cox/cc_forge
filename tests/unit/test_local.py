"""Tests for the forge local workflow (prepare_local_directory)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import click
import pytest

from cc_forge.git import is_git_repo
from cc_forge.session import prepare_local_directory


@pytest.fixture()
def source_dir(tmp_path: Path) -> Path:
    """Create a sample directory with loose text files."""
    d = tmp_path / "my-docs"
    d.mkdir()
    (d / "notes.txt").write_text("some notes")
    (d / "todo.md").write_text("# TODO\n- item 1\n")
    sub = d / "subdir"
    sub.mkdir()
    (sub / "deep.txt").write_text("deep file")
    return d


@pytest.fixture(autouse=True)
def _local_repos_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point _LOCAL_REPOS_DIR at a temp path so tests don't touch the real home."""
    import cc_forge.session as session_mod
    monkeypatch.setattr(session_mod, "_LOCAL_REPOS_DIR", tmp_path / "local-repos")


def test_prepare_creates_git_repo(source_dir: Path) -> None:
    repo = prepare_local_directory(source_dir)
    assert is_git_repo(repo)
    assert repo.name.startswith(source_dir.name)


def test_prepare_copies_files(source_dir: Path) -> None:
    repo = prepare_local_directory(source_dir)
    assert (repo / "notes.txt").read_text() == "some notes"
    assert (repo / "todo.md").exists()
    assert (repo / "subdir" / "deep.txt").read_text() == "deep file"


def test_prepare_skips_hidden_files(source_dir: Path) -> None:
    (source_dir / ".secret").write_text("hidden")
    (source_dir / "subdir" / ".nested-secret").write_text("also hidden")
    hidden_dir = source_dir / ".hidden-dir"
    hidden_dir.mkdir()
    (hidden_dir / "inside.txt").write_text("should not be copied")

    repo = prepare_local_directory(source_dir)

    assert not (repo / ".secret").exists()
    assert not (repo / "subdir" / ".nested-secret").exists()
    assert not (repo / ".hidden-dir").exists()


def test_prepare_excludes_symlinks(source_dir: Path, tmp_path: Path) -> None:
    """Symlinks are dropped, not followed — they can resolve outside the source."""
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("must not leave the machine")
    (source_dir / "link.txt").symlink_to(outside)
    (source_dir / "subdir" / "nested-link.txt").symlink_to(outside)

    repo = prepare_local_directory(source_dir)

    assert not (repo / "link.txt").exists()
    assert not (repo / "subdir" / "nested-link.txt").exists()
    copied = [
        p.read_text()
        for p in repo.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(repo).parts
    ]
    assert "must not leave the machine" not in copied


def test_prepare_is_idempotent(source_dir: Path) -> None:
    repo1 = prepare_local_directory(source_dir)
    # Modify source and re-prepare
    (source_dir / "notes.txt").write_text("updated notes")
    repo2 = prepare_local_directory(source_dir)
    assert repo1 == repo2
    assert (repo2 / "notes.txt").read_text() == "updated notes"


def test_prepare_removes_deleted_source_files(source_dir: Path) -> None:
    repo = prepare_local_directory(source_dir)
    assert (repo / "notes.txt").exists()
    # Delete a file from source and re-prepare
    (source_dir / "notes.txt").unlink()
    prepare_local_directory(source_dir)
    assert not (repo / "notes.txt").exists()
    # The deletion must also be committed, not just applied to the working tree
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.split()
    assert "notes.txt" not in tracked


def test_prepare_distinct_repos_for_same_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Two directories with the same basename but different paths get separate repos."""
    import cc_forge.session as session_mod
    monkeypatch.setattr(session_mod, "_LOCAL_REPOS_DIR", tmp_path / "local-repos-2")

    dir_a = tmp_path / "a" / "docs"
    dir_a.mkdir(parents=True)
    (dir_a / "file.txt").write_text("from a")

    dir_b = tmp_path / "b" / "docs"
    dir_b.mkdir(parents=True)
    (dir_b / "file.txt").write_text("from b")

    repo_a = prepare_local_directory(dir_a)
    repo_b = prepare_local_directory(dir_b)
    assert repo_a != repo_b
    assert (repo_a / "file.txt").read_text() == "from a"
    assert (repo_b / "file.txt").read_text() == "from b"


def test_prepare_rejects_file(tmp_path: Path) -> None:
    f = tmp_path / "not-a-dir.txt"
    f.write_text("hello")
    with pytest.raises(click.ClickException):
        prepare_local_directory(f)
