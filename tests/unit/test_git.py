"""Tests for cc_forge.git module."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from cc_forge.git import (
    GitError,
    add_remote,
    get_current_branch,
    get_repo_name,
    get_repo_root,
    has_remote,
    is_git_repo,
)


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Create a minimal git repo in a temp directory."""
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        env={**os.environ,
             "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
             "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t",
             "HOME": str(tmp_path)},
    )
    return tmp_path


def test_is_git_repo_true(git_repo: Path) -> None:
    assert is_git_repo(git_repo) is True


def test_is_git_repo_false(tmp_path: Path) -> None:
    assert is_git_repo(tmp_path) is False


def test_get_repo_root(git_repo: Path) -> None:
    subdir = git_repo / "sub"
    subdir.mkdir()
    root = get_repo_root(subdir)
    assert root == git_repo


def test_get_repo_name_from_directory(git_repo: Path) -> None:
    # No origin remote → falls back to directory name
    name = get_repo_name(git_repo)
    assert name == git_repo.name


def test_get_repo_name_from_origin(git_repo: Path) -> None:
    subprocess.run(
        ["git", "remote", "add", "origin", "https://example.com/owner/my-repo.git"],
        cwd=git_repo, check=True, capture_output=True,
    )
    assert get_repo_name(git_repo) == "my-repo"


def test_get_current_branch(git_repo: Path) -> None:
    branch = get_current_branch(git_repo)
    assert branch in ("main", "master")


def test_has_remote(git_repo: Path) -> None:
    assert has_remote(git_repo, "origin") is False
    subprocess.run(
        ["git", "remote", "add", "origin", "https://example.com/repo.git"],
        cwd=git_repo, check=True, capture_output=True,
    )
    assert has_remote(git_repo, "origin") is True


def test_add_remote(git_repo: Path) -> None:
    add_remote(git_repo, "forgejo", "http://localhost:3000/user/repo.git")
    assert has_remote(git_repo, "forgejo") is True


def test_git_error_on_bad_repo(tmp_path: Path) -> None:
    with pytest.raises(GitError):
        get_repo_root(tmp_path)


def test_is_git_repo_false_for_missing_path(tmp_path):
    """A path that was never created isn't a repo -- and mustn't crash."""
    from cc_forge.git import is_git_repo

    assert is_git_repo(tmp_path / "never-created") is False
    not_a_dir = tmp_path / "a-file.txt"
    not_a_dir.write_text("x")
    assert is_git_repo(not_a_dir) is False


def test_is_git_repo_propagates_permission_errors(tmp_path):
    """An unreadable directory is not the same as 'not a repo' -- reporting it
    that way would send the caller looking in the wrong place."""
    import os

    import pytest

    from cc_forge.git import is_git_repo

    locked = tmp_path / "locked"
    locked.mkdir()
    os.chmod(locked, 0o000)
    try:
        if os.access(locked, os.X_OK):  # running as root: the guard can't apply
            pytest.skip("cannot revoke access as root")
        with pytest.raises(PermissionError):
            is_git_repo(locked)
    finally:
        os.chmod(locked, 0o755)


def test_is_git_repo_surfaces_missing_git_executable(tmp_path, monkeypatch):
    """subprocess raises FileNotFoundError for a missing cwd *and* a missing
    binary. 'git isn't installed' must not be reported as 'not a repo'."""
    import subprocess

    import pytest

    from cc_forge.git import GitError, is_git_repo

    real_run = subprocess.run

    def fake_run(args, **kwargs):
        if args and args[0] == "git":
            raise FileNotFoundError(2, "No such file or directory", "git")
        return real_run(args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(GitError, match="git executable"):
        is_git_repo(tmp_path)
