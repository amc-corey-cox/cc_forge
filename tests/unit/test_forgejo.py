"""Tests for cc_forge.forgejo module."""

from __future__ import annotations

import httpx
import pytest

from cc_forge.config import ForgeConfig
from cc_forge.forgejo import ForgejoClient, ForgejoError


@pytest.fixture()
def config() -> ForgeConfig:
    return ForgeConfig(
        forgejo_url="http://localhost:3000",
        forgejo_token="test-token",
        ollama_cpu_url="http://localhost:11434",
        ollama_gpu_url="http://localhost:11435",
        agent_image="test:latest",
        compose_file="/dev/null",
    )


@pytest.fixture()
def client(config: ForgeConfig) -> ForgejoClient:
    return ForgejoClient(config)


def test_health_check_success(client: ForgejoClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://localhost:3000/api/v1/version",
        json={"version": "14.0.0"},
    )
    assert client.health_check() is True


def test_health_check_failure(client: ForgejoClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://localhost:3000/api/v1/version",
        status_code=500,
    )
    assert client.health_check() is False


def test_get_current_user(client: ForgejoClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://localhost:3000/api/v1/user",
        json={"login": "forge-admin", "id": 1},
    )
    assert client.get_current_user() == "forge-admin"


def test_repo_exists_true(client: ForgejoClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://localhost:3000/api/v1/repos/admin/myrepo",
        json={"name": "myrepo"},
    )
    assert client.repo_exists("admin", "myrepo") is True


def test_repo_exists_false(client: ForgejoClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://localhost:3000/api/v1/repos/admin/nope",
        status_code=404,
        text="not found",
    )
    assert client.repo_exists("admin", "nope") is False


def test_create_repo(client: ForgejoClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://localhost:3000/api/v1/user/repos",
        json={"name": "newrepo", "clone_url": "http://localhost:3000/admin/newrepo.git"},
        status_code=201,
    )
    result = client.create_repo("newrepo")
    assert result["name"] == "newrepo"


def test_get_repo_clone_url(client: ForgejoClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://localhost:3000/api/v1/repos/admin/myrepo",
        json={"name": "myrepo", "clone_url": "http://localhost:3000/admin/myrepo.git"},
    )
    assert client.get_repo_clone_url("admin", "myrepo") == "http://localhost:3000/admin/myrepo.git"


def test_error_on_auth_failure(client: ForgejoClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://localhost:3000/api/v1/user",
        status_code=401,
        text="unauthorized",
    )
    with pytest.raises(ForgejoError, match="401"):
        client.get_current_user()
