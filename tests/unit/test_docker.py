"""Tests for docker module helpers."""

from cc_forge.docker import _rewrite_url


class TestRewriteUrl:
    def test_localhost_with_port(self):
        assert _rewrite_url("http://localhost:11434", "forge-ollama-proxy") == \
            "http://forge-ollama-proxy:11434"

    def test_127_with_port(self):
        assert _rewrite_url("http://127.0.0.1:3000", "forge-forgejo") == \
            "http://forge-forgejo:3000"

    def test_localhost_with_path(self):
        assert _rewrite_url("http://localhost/api/v1", "forge-forgejo") == \
            "http://forge-forgejo/api/v1"

    def test_localhost_no_port_no_path(self):
        assert _rewrite_url("http://localhost", "forge-forgejo") == \
            "http://forge-forgejo"

    def test_non_local_unchanged(self):
        url = "http://remote-host:11434"
        assert _rewrite_url(url, "forge-ollama-proxy") == url

    def test_host_docker_internal(self):
        assert _rewrite_url("http://localhost:11434", "host.docker.internal") == \
            "http://host.docker.internal:11434"
