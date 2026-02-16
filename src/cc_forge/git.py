"""Git operations via subprocess."""

from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(Exception):
    """Raised when a git command fails."""


def _run(args: list[str], cwd: Path | str | None = None) -> str:
    """Run a git command and return stdout, raising GitError on failure."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitError(result.stderr.strip() or f"git {args[0]} failed")
    return result.stdout.strip()


def is_git_repo(path: str | Path = ".") -> bool:
    try:
        _run(["rev-parse", "--git-dir"], cwd=path)
        return True
    except GitError:
        return False


def get_repo_root(path: str | Path = ".") -> Path:
    return Path(_run(["rev-parse", "--show-toplevel"], cwd=path))


def get_repo_name(path: str | Path = ".") -> str:
    """Derive repo name from the origin remote URL, falling back to directory name."""
    try:
        url = _run(["remote", "get-url", "origin"], cwd=path)
        # Handle both https://host/owner/repo.git and git@host:owner/repo.git
        name = url.rstrip("/").rsplit("/", 1)[-1]
        if name.endswith(".git"):
            name = name[:-4]
        return name
    except GitError:
        return Path(path).resolve().name


def get_current_branch(path: str | Path = ".") -> str:
    return _run(["rev-parse", "--abbrev-ref", "HEAD"], cwd=path)


def has_remote(path: str | Path, name: str) -> bool:
    try:
        _run(["remote", "get-url", name], cwd=path)
        return True
    except GitError:
        return False


def add_remote(path: str | Path, name: str, url: str) -> None:
    _run(["remote", "add", name, url], cwd=path)


def push_to_remote(path: str | Path, remote: str, branch: str) -> None:
    _run(["push", "-u", remote, branch], cwd=path)


def set_remote_url(path: str | Path, name: str, url: str) -> None:
    _run(["remote", "set-url", name, url], cwd=path)


def get_remote_url(path: str | Path, name: str) -> str:
    return _run(["remote", "get-url", name], cwd=path)
