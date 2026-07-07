"""Tests for cc_forge.forgejo module."""

from __future__ import annotations

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


def test_repo_exists_raises_on_auth_error(client: ForgejoClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://localhost:3000/api/v1/repos/admin/secret",
        status_code=401,
        text="unauthorized",
    )
    with pytest.raises(ForgejoError, match="401"):
        client.repo_exists("admin", "secret")


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


def test_get_pull_request(client: ForgejoClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://localhost:3000/api/v1/repos/admin/myrepo/pulls/7",
        json={
            "title": "Add feature",
            "body": "Does the thing.",
            "head": {"ref": "agent/feature"},
            "base": {"ref": "main"},
        },
    )
    pr = client.get_pull_request("admin", "myrepo", 7)
    assert pr["head"]["ref"] == "agent/feature"
    assert pr["base"]["ref"] == "main"
    assert pr["title"] == "Add feature"


def test_get_repo(client: ForgejoClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://localhost:3000/api/v1/repos/admin/myrepo",
        json={"name": "myrepo", "default_branch": "main"},
    )
    assert client.get_repo("admin", "myrepo")["default_branch"] == "main"


def test_delete_branch(client: ForgejoClient, httpx_mock) -> None:
    import re

    httpx_mock.add_response(
        url=re.compile(r".*/repos/admin/myrepo/branches/stale$"),
        method="DELETE",
        status_code=204,
    )
    client.delete_branch("admin", "myrepo", "stale")
    assert httpx_mock.get_requests()[0].method == "DELETE"


def test_delete_branch_keeps_slashes_encodes_specials(
    client: ForgejoClient, httpx_mock
) -> None:
    import re

    httpx_mock.add_response(
        url=re.compile(r".*/branches/.*"), method="DELETE", status_code=204
    )
    client.delete_branch("admin", "myrepo", "feature/x#1")
    path = httpx_mock.get_requests()[0].url.raw_path.decode()
    # Slash stays literal (catch-all route); '#' is percent-encoded.
    assert path.endswith("/branches/feature/x%231")


def test_list_branches_paginates(client: ForgejoClient, httpx_mock) -> None:
    import re

    page1 = [{"name": f"b{i}"} for i in range(50)]
    page2 = [{"name": "b50"}]
    httpx_mock.add_response(url=re.compile(r".*/branches\?.*page=1.*"), json=page1)
    httpx_mock.add_response(url=re.compile(r".*/branches\?.*page=2.*"), json=page2)
    branches = client.list_branches("admin", "myrepo")
    assert len(branches) == 51
    assert branches[-1]["name"] == "b50"


def test_list_pull_requests_paginates(client: ForgejoClient, httpx_mock) -> None:
    import re

    page1 = [{"number": i} for i in range(50)]
    page2 = [{"number": 50}]
    httpx_mock.add_response(
        url=re.compile(r".*/pulls\?.*state=all.*page=1.*"), json=page1
    )
    httpx_mock.add_response(
        url=re.compile(r".*/pulls\?.*state=all.*page=2.*"), json=page2
    )
    prs = client.list_pull_requests("admin", "myrepo", state="all")
    assert len(prs) == 51
    assert prs[-1]["number"] == 50


def test_get_issue(client: ForgejoClient, httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://localhost:3000/api/v1/repos/admin/myrepo/issues/12",
        json={"title": "Bug", "body": "b", "number": 12},
    )
    assert client.get_issue("admin", "myrepo", 12)["number"] == 12


def test_list_issues_filters_out_prs(client: ForgejoClient, httpx_mock) -> None:
    import re

    httpx_mock.add_response(
        url=re.compile(r".*/issues\?.*"),
        json=[
            {"number": 3, "title": "real issue"},
            {"number": 7, "title": "a pr", "pull_request": {"merged": False}},
        ],
    )
    issues = client.list_issues("admin", "myrepo")
    assert [i["number"] for i in issues] == [3]


def test_create_issue_comment(client: ForgejoClient, httpx_mock) -> None:
    import re

    httpx_mock.add_response(
        url=re.compile(r".*/issues/12/comments$"),
        method="POST",
        json={"id": 1, "body": "hi"},
        status_code=201,
    )
    assert client.create_issue_comment("admin", "myrepo", 12, "hi")["id"] == 1


def test_close_issue(client: ForgejoClient, httpx_mock) -> None:
    import re

    httpx_mock.add_response(
        url=re.compile(r".*/issues/12$"),
        method="PATCH",
        json={"number": 12, "state": "closed"},
    )
    assert client.close_issue("admin", "myrepo", 12)["state"] == "closed"
