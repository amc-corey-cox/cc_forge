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
    except OSError:
        # cwd doesn't exist -- not a repo, rather than a crash
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


def push_to_remote(path: str | Path, remote: str, branch: str, set_upstream: bool = True) -> None:
    args = ["push", "-u", remote, branch] if set_upstream else ["push", remote, branch]
    _run(args, cwd=path)


def set_remote_url(path: str | Path, name: str, url: str) -> None:
    _run(["remote", "set-url", name, url], cwd=path)


def get_remote_url(path: str | Path, name: str) -> str:
    return _run(["remote", "get-url", name], cwd=path)


def fetch_remote(path: str | Path, remote: str) -> None:
    _run(["fetch", remote], cwd=path)


def create_branch_from_ref(path: str | Path, branch: str, start_ref: str) -> None:
    """Create (or reset) a local branch pointing at start_ref."""
    _run(["branch", "-f", branch, start_ref], cwd=path)


def init_repo(path: str | Path) -> None:
    """Initialize a new git repo at *path* (must already exist)."""
    _run(["init"], cwd=path)
    # Managed repos are forge-owned, so give them a local identity rather than
    # relying on the host having a global one configured.
    _run(["config", "user.name", "Forge"], cwd=path)
    _run(["config", "user.email", "forge@forge.local"], cwd=path)


def add_all(path: str | Path) -> None:
    """Stage all changes in the working tree, including deletions."""
    _run(["add", "-A"], cwd=path)


def commit(path: str | Path, message: str) -> None:
    """Create a commit with the given message.  No-op if the index is clean."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=path,
        capture_output=True,
    )
    if result.returncode == 0:
        return  # Nothing staged
    if result.returncode > 1:
        # 1 means "there are staged changes"; anything higher is a real error.
        raise GitError(
            f"git diff --cached failed: {result.stderr.decode(errors='replace').strip()}"
        )
    _run(["commit", "-m", message], cwd=path)


def archive_ref(path: str | Path, ref: str, out_file: str | Path) -> None:
    """Write the tree at *ref* to *out_file* as a tar, leaving the repo untouched."""
    _run(["archive", "--format=tar", "-o", str(out_file), ref], cwd=path)


def list_tree(path: str | Path, ref: str = "HEAD") -> list[str]:
    """Paths tracked at *ref*, relative to the repo root."""
    out = _run(["ls-tree", "-r", "--name-only", ref], cwd=path)
    return [line for line in out.splitlines() if line]
