"""Promote Forgejo PRs and issues to GitHub (the deliberate Forgejo→GitHub hop).

A promote marks the source Forgejo item with a comment *before* creating the
GitHub item, then records the resulting URL and closes it. That marker is a lock:
once present, promote refuses to create a duplicate — no matter where a run
broke — until a human deletes it. So a marked+closed item is a clean success; a
marked-but-open item means a run failed partway and needs a look.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import click
import httpx

from cc_forge.config import ForgeConfig
from cc_forge.forgejo import ForgejoClient, ForgejoError
from cc_forge.git import (
    GitError,
    create_branch_from_ref,
    fetch_remote,
    get_current_branch,
    get_remote_url,
    get_repo_name,
    get_repo_root,
    has_remote,
    is_git_repo,
    push_to_remote,
)


def _resolve_github_repo(config: ForgeConfig, repo_name: str) -> str:
    """Resolve the GitHub destination, surfacing config errors as clean CLI messages."""
    try:
        return config.resolve_github_repo(repo_name)
    except ValueError as e:
        raise click.ClickException(str(e))


def promote_pull_request(
    config: ForgeConfig,
    pr_number: int,
    repo_path: str = ".",
    remote: str = "origin",
) -> str:
    """Materialize a Forgejo PR's branch on the GitHub remote and open a GitHub PR.

    Returns the URL of the created GitHub PR.
    """
    if not is_git_repo(repo_path):
        raise click.ClickException(f"{repo_path} is not a git repository.")

    repo_root = get_repo_root(repo_path)
    repo_name = get_repo_name(repo_root)
    github_repo = _resolve_github_repo(config, repo_name)

    meta = pr_metadata(config, pr_number, repo_name)
    head, base, title, body = meta["head"], meta["base"], meta["title"], meta["body"]

    _guard_not_promoted(config, repo_name, pr_number)

    if not has_remote(repo_root, "forgejo"):
        raise click.ClickException(
            "No 'forgejo' remote found. Run a forge session first "
            "(the workstation wrapper adds it)."
        )
    try:
        fetch_remote(repo_root, "forgejo")
    except GitError as e:
        raise click.ClickException(
            f"Could not fetch the 'forgejo' remote (is Forgejo reachable?): {e}"
        )
    if get_current_branch(repo_root) == head:
        raise click.ClickException(
            f"Branch '{head}' is currently checked out; switch to another branch "
            "before promoting."
        )
    try:
        create_branch_from_ref(repo_root, head, f"forgejo/{head}")
    except GitError as e:
        raise click.ClickException(f"Could not materialize branch '{head}': {e}")

    if not has_remote(repo_root, remote):
        raise click.ClickException(f"No '{remote}' remote to push to.")
    _warn_on_repo_mismatch(repo_root, remote, github_repo)
    try:
        push_to_remote(repo_root, remote, head, set_upstream=False)
    except GitError as e:
        raise click.ClickException(f"Could not push '{head}' to '{remote}': {e}")

    _post_lock(config, repo_name, pr_number, f"https://github.com/{github_repo}")
    body = body + _provenance_footer("PR", pr_number, meta["url"])
    try:
        url = _gh_pr_create(config, repo_root, github_repo, head, base, title, body)
    except click.ClickException as e:
        raise click.ClickException(
            f"{e.message} Forgejo #{pr_number} was marked as promoted — "
            "delete the marker comment before retrying."
        )
    _finalize_forgejo_item(config, repo_name, pr_number, url)
    return url


def promote_issue(config: ForgeConfig, issue_number: int, repo_path: str = ".") -> str:
    """Open a GitHub issue mirroring a Forgejo issue; return the GitHub URL.

    Unlike a PR, an issue carries no branch — this is purely a metadata copy
    plus the back-link/close bookkeeping.
    """
    if not is_git_repo(repo_path):
        raise click.ClickException(f"{repo_path} is not a git repository.")

    repo_root = get_repo_root(repo_path)
    repo_name = get_repo_name(repo_root)
    github_repo = _resolve_github_repo(config, repo_name)

    meta = issue_metadata(config, issue_number, repo_name)
    if meta["is_pr"]:
        raise click.ClickException(
            f"#{issue_number} is a pull request, not an issue — use promote-pr."
        )

    _guard_not_promoted(config, repo_name, issue_number)
    _post_lock(config, repo_name, issue_number, f"https://github.com/{github_repo}")
    body = meta["body"] + _provenance_footer("issue", issue_number, meta["url"])
    try:
        url = _gh_issue_create(config, repo_root, github_repo, meta["title"], body)
    except click.ClickException as e:
        raise click.ClickException(
            f"{e.message} Forgejo #{issue_number} was marked as promoted — "
            "delete the marker comment before retrying."
        )
    _finalize_forgejo_item(config, repo_name, issue_number, url)
    return url


def promote_by_number(
    config: ForgeConfig, number: int, repo_path: str = ".", remote: str = "origin"
) -> str:
    """Promote whichever of PR-or-issue carries this number (they share a space)."""
    if not is_git_repo(repo_path):
        raise click.ClickException(f"{repo_path} is not a git repository.")
    repo_name = get_repo_name(get_repo_root(repo_path))
    if issue_metadata(config, number, repo_name)["is_pr"]:
        return promote_pull_request(config, number, repo_path=repo_path, remote=remote)
    return promote_issue(config, number, repo_path=repo_path)


def pr_metadata(config: ForgeConfig, pr_number: int, repo_name: str) -> dict:
    """Read a Forgejo PR's metadata: {head, base, title, body}.

    Raises a ClickException on an unreachable Forgejo or an API error.
    """
    try:
        with ForgejoClient(config) as forgejo:
            owner = forgejo.get_current_user()
            pr = forgejo.get_pull_request(owner, repo_name, pr_number)
    except httpx.RequestError as e:
        raise click.ClickException(f"Forgejo unreachable at {config.forgejo_url}: {e}")
    except ForgejoError as e:
        raise click.ClickException(f"Forgejo: {e}")
    return {
        "head": pr["head"]["ref"],
        "base": pr["base"]["ref"],
        "title": pr["title"],
        "body": pr.get("body") or "",
        "url": pr.get("html_url", ""),
    }


def issue_metadata(config: ForgeConfig, index: int, repo_name: str) -> dict:
    """Read a Forgejo issue/PR: {title, body, url, is_pr}.

    Works for either kind (PRs are issues in Forgejo); ``is_pr`` distinguishes
    them so callers can route to the right promote path.
    """
    try:
        with ForgejoClient(config) as forgejo:
            owner = forgejo.get_current_user()
            item = forgejo.get_issue(owner, repo_name, index)
    except httpx.RequestError as e:
        raise click.ClickException(f"Forgejo unreachable at {config.forgejo_url}: {e}")
    except ForgejoError as e:
        raise click.ClickException(f"Forgejo: {e}")
    return {
        "title": item["title"],
        "body": item.get("body") or "",
        "url": item.get("html_url", ""),
        "is_pr": item.get("pull_request") is not None,
    }


def list_promotable(config: ForgeConfig, repo_name: str) -> list[dict]:
    """Open issues and PRs as rich dicts (kind, number, title, body, url, dates,
    and head/base for PRs) for a context-rich promote walk.

    Open == not-yet-promoted, since promoting closes the source item. Sorted by
    number so the walk order is stable.
    """
    try:
        with ForgejoClient(config) as forgejo:
            owner = forgejo.get_current_user()
            prs = forgejo.list_pull_requests(owner, repo_name, state="open")
            issues = forgejo.list_issues(owner, repo_name, state="open")
    except httpx.RequestError as e:
        raise click.ClickException(f"Forgejo unreachable at {config.forgejo_url}: {e}")
    except ForgejoError as e:
        raise click.ClickException(f"Forgejo: {e}")
    items = [
        {
            "kind": "issue",
            "number": i["number"],
            "title": i["title"],
            "body": i.get("body") or "",
            "url": i.get("html_url", ""),
            "created_at": i.get("created_at", ""),
        }
        for i in issues
    ]
    items += [
        {
            "kind": "pr",
            "number": p["number"],
            "title": p["title"],
            "body": p.get("body") or "",
            "url": p.get("html_url", ""),
            "created_at": p.get("created_at", ""),
            "head": (p.get("head") or {}).get("ref", ""),
            "base": (p.get("base") or {}).get("ref", ""),
        }
        for p in prs
    ]
    return sorted(items, key=lambda it: it["number"])


def _first_paragraph(body: str, limit: int = 200) -> str:
    """First real text paragraph of a body: skip leading markdown headings and
    blanks, collect until the next blank line or heading, collapse whitespace,
    and cap the length (even a heading directly above text, no blank line)."""
    picked: list[str] = []
    for line in body.strip().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            if picked:
                break  # a blank line or heading ends the first paragraph
            continue   # still skipping leading blanks/headings
        picked.append(stripped)
    text = " ".join(picked)
    if len(text) <= limit:
        return text
    if limit < 3:  # no room for the "..." — hard-cut so we never exceed limit
        return text[:limit]
    return text[: limit - 3].rstrip() + "..."


def _promotable_summary(it: dict) -> str:
    """Context block for one promotable item: title, branch/opened-date, a
    first-paragraph excerpt, and the Forgejo URL."""
    lines = [f"{it['kind'].upper()} #{it['number']}: {it['title']}"]
    meta = []
    if it.get("head") and it.get("base"):
        meta.append(f"{it['head']} -> {it['base']}")
    if it.get("created_at"):
        meta.append(f"opened {it['created_at'][:10]}")
    if meta:
        lines.append("   " + " | ".join(meta))
    excerpt = _first_paragraph(it.get("body", ""))
    if excerpt:
        lines.append("   " + excerpt)
    if it.get("url"):
        lines.append("   " + it["url"])
    return "\n".join(lines)


def walk_promotable(
    config: ForgeConfig,
    repo_path: str,
    remote: str,
    kinds: tuple[str, ...],
    *,
    confirm,
    echo,
) -> list[tuple[int, str]]:
    """Walk promotable items of the given kinds, promoting the ones confirmed.

    ``confirm(prompt) -> bool`` and ``echo(msg)`` are injected so the loop is
    testable without a live terminal. Returns (number, github_url) per promotion.
    """
    repo_name = _derive_repo_name(repo_path)
    items = [it for it in list_promotable(config, repo_name) if it["kind"] in kinds]
    if not items:
        echo("Nothing to promote.")
        return []

    promoted: list[tuple[int, str]] = []
    for it in items:
        echo(f"\n{_promotable_summary(it)}")
        if not confirm(f"Promote {it['kind']} #{it['number']}?"):
            continue
        try:
            if it["kind"] == "pr":
                url = promote_pull_request(config, it["number"], repo_path=repo_path, remote=remote)
            else:
                url = promote_issue(config, it["number"], repo_path=repo_path)
        except click.ClickException as e:
            # One item's failure (already-marked, gh error) shouldn't abort the walk.
            echo(f"  skipped: {e.message}")
            continue
        echo(f"  -> {url}")
        promoted.append((it["number"], url))
    return promoted


def _derive_repo_name(repo_path: str) -> str:
    if not is_git_repo(repo_path):
        raise click.ClickException(f"{repo_path} is not a git repository.")
    return get_repo_name(get_repo_root(repo_path))


def _provenance_footer(kind: str, index: int, url: str) -> str:
    """A one-line trailer linking the GitHub item back to its Forgejo source."""
    ref = f"Forgejo {kind} #{index}"
    link = f"[{ref}]({url})" if url else ref
    return f"\n\n---\n_Promoted from {link}_"


# A hidden token embedded in every forge-authored promotion comment. It, not the
# human-readable text, is what the guard matches — so wording can change freely.
_MARKER = "<!-- forge-promote -->"


def _marked_comments(comments: list[dict]) -> list[dict]:
    return [c for c in comments if _MARKER in (c.get("body") or "")]


def _promoted_url(marked: list[dict]) -> str | None:
    """Best URL evidence from marker comments: the result's item URL if present,
    else any URL (e.g. the lock's repo URL)."""
    for c in marked:
        m = re.search(r"Promoted to GitHub:\s*(\S+)", c.get("body") or "")
        if m:
            return m.group(1)
    for c in marked:
        m = re.search(r"https?://\S+", c.get("body") or "")
        if m:
            return m.group(0)
    return None


def _guard_not_promoted(config: ForgeConfig, repo_name: str, number: int) -> None:
    """Raise if the Forgejo item already carries a promotion marker.

    A marker means a promote was at least started, so we never auto-create a
    duplicate — the human clears the marker to (re-)promote. Marked+closed reads
    as a clean success; marked+open means a prior run broke partway.
    """
    try:
        with ForgejoClient(config) as forgejo:
            owner = forgejo.get_current_user()
            marked = _marked_comments(
                forgejo.list_issue_comments(owner, repo_name, number)
            )
            if not marked:
                return
            closed = forgejo.get_issue(owner, repo_name, number).get("state") == "closed"
    except httpx.RequestError as e:
        raise click.ClickException(f"Forgejo unreachable at {config.forgejo_url}: {e}")
    except ForgejoError as e:
        raise click.ClickException(f"Forgejo: {e}")

    url = _promoted_url(marked)
    if closed:
        raise click.ClickException(
            f"Forgejo #{number} is already promoted"
            + (f" → {url}" if url else "")
            + ". Delete the marker comment to re-promote."
        )
    raise click.ClickException(
        f"Forgejo #{number} is marked as promoted but still open — a prior run "
        "may have failed partway. Verify it isn't already on GitHub"
        + (f" ({url})" if url else "")
        + ", then delete the marker comment and re-run."
    )


def _post_lock(
    config: ForgeConfig, repo_name: str, number: int, repo_url: str
) -> None:
    """Mark the item as being promoted *before* the transfer (the dedup lock).

    Fatal on failure: without the lock there's no duplicate protection, so we
    refuse to create the GitHub item.
    """
    try:
        with ForgejoClient(config) as forgejo:
            owner = forgejo.get_current_user()
            forgejo.create_issue_comment(
                owner, repo_name, number,
                f"{_MARKER}\nPromoting to {repo_url} — "
                "delete this comment to re-promote.",
            )
    except httpx.RequestError as e:
        raise click.ClickException(f"Forgejo unreachable at {config.forgejo_url}: {e}")
    except ForgejoError as e:
        raise click.ClickException(f"Forgejo: {e}")


def _finalize_forgejo_item(
    config: ForgeConfig, repo_name: str, index: int, github_url: str
) -> None:
    """Best-effort: record the GitHub URL on the Forgejo item and close it.

    Non-fatal — the GitHub item already exists and the lock is already in place,
    so a Forgejo hiccup here should warn, not fail the promote.
    """
    try:
        with ForgejoClient(config) as forgejo:
            owner = forgejo.get_current_user()
            forgejo.create_issue_comment(
                owner, repo_name, index, f"{_MARKER}\nPromoted to GitHub: {github_url}"
            )
            forgejo.close_issue(owner, repo_name, index)
    except (httpx.RequestError, ForgejoError) as e:
        click.echo(
            f"Warning: promoted to {github_url}, but could not close "
            f"Forgejo #{index}: {e}",
            err=True,
        )


def _remote_owner_repo(url: str) -> str | None:
    """Extract 'owner/repo' from an https or ssh git remote URL."""
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    # https://host/owner/repo and ssh://git@host/owner/repo carry "://";
    # the scp form git@host:owner/repo does not.
    tail = url.split("://", 1)[1] if "://" in url else url.split(":", 1)[-1]
    segments = tail.split("/")
    if len(segments) >= 2 and segments[-1] and segments[-2]:
        return f"{segments[-2]}/{segments[-1]}"
    return None


def _warn_on_repo_mismatch(repo_root: Path, remote: str, github_repo: str) -> None:
    """Warn loudly if the push remote's URL doesn't match the resolved GitHub repo."""
    url = get_remote_url(repo_root, remote)
    actual = _remote_owner_repo(url)
    if actual is None or actual.lower() != github_repo.lower():
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
    result = _run_gh(
        ["pr", "create", "-R", github_repo,
         "--head", head, "--base", base,
         "--title", title, "--body", body],
        cwd=repo_root,
        env=_gh_env(config),
    )
    if result.returncode != 0:
        raise click.ClickException(f"gh pr create failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _gh_issue_create(
    config: ForgeConfig,
    repo_root: Path,
    github_repo: str,
    title: str,
    body: str,
) -> str:
    """Create a GitHub issue via the gh CLI; return its URL."""
    result = _run_gh(
        ["issue", "create", "-R", github_repo, "--title", title, "--body", body],
        cwd=repo_root,
        env=_gh_env(config),
    )
    if result.returncode != 0:
        raise click.ClickException(f"gh issue create failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _gh_env(config: ForgeConfig) -> dict[str, str]:
    """Env for gh: prefer the human's ambient auth, fall back to the config token."""
    env = os.environ.copy()
    if config.github_token and not _has_ambient_gh_auth(env):
        env["GH_TOKEN"] = config.github_token
    return env


def _run_gh(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a gh command, surfacing a clean error if gh isn't installed."""
    try:
        return subprocess.run(
            ["gh", *args], capture_output=True, text=True, **kwargs
        )
    except FileNotFoundError:
        raise click.ClickException(
            "gh CLI not found. Install GitHub CLI (https://cli.github.com) "
            "and authenticate with 'gh auth login'."
        )


def _has_ambient_gh_auth(env: dict[str, str]) -> bool:
    return _run_gh(["auth", "status"], env=env).returncode == 0
