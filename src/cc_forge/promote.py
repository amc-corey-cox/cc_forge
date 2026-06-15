"""Promote a Forgejo PR to a GitHub PR (the deliberate Forgejo→GitHub hop)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import click

from cc_forge.config import ForgeConfig
from cc_forge.forgejo import ForgejoClient
from cc_forge.git import (
    create_branch_from_ref,
    fetch_remote,
    get_remote_url,
    get_repo_name,
    get_repo_root,
    has_remote,
    push_to_remote,
)


def promote_pull_request(
    config: ForgeConfig,
    pr_number: int,
    repo_path: str = ".",
    remote: str = "origin",
) -> str:
    """Materialize a Forgejo PR's branch on the GitHub remote and open a GitHub PR.

    Returns the URL of the created GitHub PR.
    """
    repo_root = get_repo_root(repo_path)
    repo_name = get_repo_name(repo_root)
    github_repo = config.resolve_github_repo(repo_name)

    with ForgejoClient(config) as forgejo:
        owner = forgejo.get_current_user()
        pr = forgejo.get_pull_request(owner, repo_name, pr_number)

    head = pr["head"]["ref"]
    base = pr["base"]["ref"]
    title = pr["title"]
    body = pr.get("body") or ""

    if not has_remote(repo_root, "forgejo"):
        raise click.ClickException(
            "No 'forgejo' remote found. Run a forge session first "
            "(the workstation wrapper adds it)."
        )
    fetch_remote(repo_root, "forgejo")
    create_branch_from_ref(repo_root, head, f"forgejo/{head}")

    if not has_remote(repo_root, remote):
        raise click.ClickException(f"No '{remote}' remote to push to.")
    _warn_on_repo_mismatch(repo_root, remote, github_repo)
    push_to_remote(repo_root, remote, head)

    return _gh_pr_create(config, repo_root, github_repo, head, base, title, body)


def _warn_on_repo_mismatch(repo_root: Path, remote: str, github_repo: str) -> None:
    """Warn loudly if the push remote's URL doesn't match the resolved GitHub repo."""
    url = get_remote_url(repo_root, remote)
    if github_repo not in url:
        click.echo(
            f"Warning: remote '{remote}' ({url}) does not match the resolved "
            f"GitHub repo '{github_repo}'. Pushing there anyway.",
            err=True,
        )


def _gh_pr_create(
    config: ForgeConfig,
    repo_root: Path,
    github_repo: str,
    head: str,
    base: str,
    title: str,
    body: str,
) -> str:
    """Create a GitHub PR via the gh CLI; return its URL."""
    env = os.environ.copy()
    # Prefer the human's ambient gh auth; fall back to the configured token.
    if config.github_token and not _has_ambient_gh_auth(env):
        env["GH_TOKEN"] = config.github_token

    result = subprocess.run(
        ["gh", "pr", "create", "-R", github_repo,
         "--head", head, "--base", base,
         "--title", title, "--body", body],
        cwd=repo_root,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise click.ClickException(f"gh pr create failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _has_ambient_gh_auth(env: dict[str, str]) -> bool:
    result = subprocess.run(
        ["gh", "auth", "status"], capture_output=True, text=True, env=env
    )
    return result.returncode == 0
