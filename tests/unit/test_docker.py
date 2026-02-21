"""Tests for docker module helpers."""
from __future__ import annotations

import os
import pytest

from cc_forge.docker import _rewrite_url, _ollama_environment, _claude_environment


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

    def test_https_preserved(self):
        assert _rewrite_url("https://localhost:11434", "forge-ollama-proxy") == \
            "https://forge-ollama-proxy:11434"

    def test_query_params_preserved(self):
        assert _rewrite_url("http://localhost:3000/api?token=abc", "forge-forgejo") == \
            "http://forge-forgejo:3000/api?token=abc"


class TestOllamaEnvironment:
    def test_sets_ollama_vars(self):
        from cc_forge.config import ForgeConfig
        config = ForgeConfig(
            ollama_cpu_url="http://localhost:11434",
            forgejo_url="http://localhost:3000",
            forgejo_token="test",
            agent_image="test",
            claude_model="test-model",
            compose_file="",
        )
        env = _ollama_environment(config)
        assert env["ANTHROPIC_AUTH_TOKEN"] == "ollama"
        assert "host.docker.internal" in env["ANTHROPIC_BASE_URL"]
        assert env["DISABLE_PROMPT_CACHING"] == "true"
        assert env["MAX_THINKING_TOKENS"] == "0"
        assert "ANTHROPIC_API_KEY" not in env


class TestClaudeEnvironment:
    def test_passes_api_key(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key-123")
        env = _claude_environment()
        assert env["ANTHROPIC_API_KEY"] == "sk-test-key-123"
        assert "ANTHROPIC_BASE_URL" not in env
        assert "ANTHROPIC_AUTH_TOKEN" not in env
        assert "DISABLE_PROMPT_CACHING" not in env

    def test_raises_without_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY not set"):
            _claude_environment()
