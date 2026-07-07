"""Forgejo API client using httpx."""

from __future__ import annotations

from urllib.parse import quote

import httpx

from cc_forge.config import ForgeConfig


class ForgejoError(Exception):
    """Raised when a Forgejo API call fails."""


class ForgejoClient:
    """Thin wrapper around the Forgejo REST API."""

    def __init__(self, config: ForgeConfig) -> None:
        self.base_url = config.forgejo_url.rstrip("/")
        self.token = config.forgejo_token
        self._client = httpx.Client(
            base_url=f"{self.base_url}/api/v1",
            headers={"Authorization": f"token {self.token}"} if self.token else {},
            timeout=30.0,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ForgejoClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        resp = self._client.request(method, path, **kwargs)
        if resp.status_code >= 400:
            raise ForgejoError(
                f"{method} {path} returned {resp.status_code}: {resp.text}"
            )
        return resp

    def health_check(self) -> bool:
        """Check if Forgejo is reachable."""
        try:
            resp = self._request("GET", "/version")
            return "version" in resp.json()
        except (httpx.ConnectError, httpx.TimeoutException, ForgejoError):
            return False

    def get_current_user(self) -> str:
        """Return the username of the authenticated user."""
        resp = self._request("GET", "/user")
        return resp.json()["login"]

    def repo_exists(self, owner: str, repo: str) -> bool:
        """Check if a repository exists. Only treats 404 as 'not found'."""
        resp = self._client.request("GET", f"/repos/{owner}/{repo}")
        if resp.status_code == 404:
            return False
        if resp.status_code >= 400:
            raise ForgejoError(
                f"GET /repos/{owner}/{repo} returned {resp.status_code}: {resp.text}"
            )
        return True

    def create_repo(self, name: str, *, private: bool = False) -> dict:
        """Create a new repository for the authenticated user."""
        resp = self._request(
            "POST",
            "/user/repos",
            json={"name": name, "private": private, "auto_init": False},
        )
        return resp.json()

    def get_repo_clone_url(self, owner: str, repo: str) -> str:
        """Return the HTTP clone URL for a repository."""
        resp = self._request("GET", f"/repos/{owner}/{repo}")
        return resp.json()["clone_url"]

    def get_pull_request(self, owner: str, repo: str, index: int) -> dict:
        """Fetch a pull request's metadata (head/base refs, title, body, url)."""
        resp = self._request("GET", f"/repos/{owner}/{repo}/pulls/{index}")
        return resp.json()

    def _paginate(self, path: str, params: dict | None = None) -> list[dict]:
        """Fetch every page of a list endpoint (Forgejo caps a page at 50)."""
        query = dict(params or {})
        query["limit"] = 50
        items: list[dict] = []
        page = 1
        while True:
            query["page"] = page
            batch = self._request("GET", path, params=query).json()
            items.extend(batch)
            if len(batch) < 50:
                return items
            page += 1

    def get_repo(self, owner: str, repo: str) -> dict:
        """Fetch a repository's metadata (includes default_branch)."""
        return self._request("GET", f"/repos/{owner}/{repo}").json()

    def list_pull_requests(
        self, owner: str, repo: str, state: str = "all"
    ) -> list[dict]:
        """List pull requests (state: open, closed, all)."""
        return self._paginate(f"/repos/{owner}/{repo}/pulls", {"state": state})

    def list_branches(self, owner: str, repo: str) -> list[dict]:
        """List branches (each carries name + commit.timestamp)."""
        return self._paginate(f"/repos/{owner}/{repo}/branches")

    def delete_branch(self, owner: str, repo: str, branch: str) -> None:
        """Delete a branch by name.

        Slashes are kept literal — Forgejo's branch route is a catch-all that
        expects `feature/x` unencoded — while other URL-special characters that
        are still legal in a git ref (e.g. `#`, `%`) are percent-encoded.
        """
        path = f"/repos/{owner}/{repo}/branches/{quote(branch, safe='/')}"
        self._request("DELETE", path)

    def get_issue(self, owner: str, repo: str, index: int) -> dict:
        """Fetch an issue by index.

        In Forgejo, pull requests are issues too, so this resolves either — a
        PR carries a non-null ``pull_request`` field, an issue does not.
        """
        return self._request("GET", f"/repos/{owner}/{repo}/issues/{index}").json()

    def list_issues(self, owner: str, repo: str, state: str = "open") -> list[dict]:
        """List issues (state: open, closed, all), excluding pull requests.

        The Forgejo issues endpoint returns PRs mixed in; they carry a
        ``pull_request`` field, which we filter out so callers get issues only.
        """
        items = self._paginate(
            f"/repos/{owner}/{repo}/issues", {"state": state, "type": "issues"}
        )
        return [i for i in items if not i.get("pull_request")]

    def create_issue_comment(
        self, owner: str, repo: str, index: int, body: str
    ) -> dict:
        """Post a comment on an issue or PR (they share the issue comment API)."""
        return self._request(
            "POST",
            f"/repos/{owner}/{repo}/issues/{index}/comments",
            json={"body": body},
        ).json()

    def list_issue_comments(self, owner: str, repo: str, index: int) -> list[dict]:
        """List the comments on an issue or PR (each carries a body)."""
        return self._paginate(f"/repos/{owner}/{repo}/issues/{index}/comments")

    def close_issue(self, owner: str, repo: str, index: int) -> dict:
        """Close an issue or PR by index (both go through the issues endpoint)."""
        return self._request(
            "PATCH",
            f"/repos/{owner}/{repo}/issues/{index}",
            json={"state": "closed"},
        ).json()
