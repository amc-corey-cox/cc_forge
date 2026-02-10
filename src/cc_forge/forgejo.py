"""Forgejo API client using httpx."""

from __future__ import annotations

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
        """Check if a repository exists."""
        try:
            self._request("GET", f"/repos/{owner}/{repo}")
            return True
        except ForgejoError:
            return False

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
