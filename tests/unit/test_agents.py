"""Tests for the agent adapter interface and registry."""
from __future__ import annotations

from cc_forge.agents import (
    REGISTRY,
    AgentAdapter,
    AiderAdapter,
    ClaudeAdapter,
)
from cc_forge.config import AGENT_MODEL_DEFAULT, ForgeConfig


def _make_config(**kwargs) -> ForgeConfig:
    defaults = dict(
        ollama_cpu_url="http://localhost:11434",
        forgejo_url="http://localhost:3000",
        forgejo_token="test-token",
        agent_image="test",
        agent_model="test-model",
        agent_api_key="",
        compose_file="",
        github_token="",
        github_repo="",
        github_owner="",
        agent_mem_limit="4g",
        agent_pids_limit=4096,
    )
    defaults.update(kwargs)
    return ForgeConfig(**defaults)


class TestRegistry:
    def test_contains_expected_adapters(self):
        assert isinstance(REGISTRY["claude"], ClaudeAdapter)
        assert isinstance(REGISTRY["aider"], AiderAdapter)


class TestClaudeAdapter:
    def setup_method(self):
        self.adapter = ClaudeAdapter()

    def test_supports_passthrough(self):
        assert self.adapter.supports_passthrough is True

    def test_build_cmd_ollama(self):
        config = _make_config(agent_model="qwen3-coder-32k")
        cmd = self.adapter.build_cmd(config, passthrough=False)
        assert cmd == ["claude", "--dangerously-skip-permissions", "--model", "qwen3-coder-32k"]

    def test_build_cmd_default_model(self):
        config = _make_config(agent_model=AGENT_MODEL_DEFAULT)
        cmd = self.adapter.build_cmd(config, passthrough=False)
        assert cmd == ["claude", "--dangerously-skip-permissions", "--model", "qwen3-coder-32k"]

    def test_build_cmd_passthrough(self):
        config = _make_config(agent_model="qwen3-coder-32k")
        cmd = self.adapter.build_cmd(config, passthrough=True)
        assert cmd == ["claude", "--dangerously-skip-permissions"]
        assert "--model" not in cmd

    def test_container_env_ollama(self):
        config = _make_config()
        env = self.adapter.container_env(config, passthrough=False)
        assert env["ANTHROPIC_AUTH_TOKEN"] == "ollama"
        assert "host.docker.internal" in env["ANTHROPIC_BASE_URL"]
        assert env["DISABLE_PROMPT_CACHING"] == "true"
        assert env["MAX_THINKING_TOKENS"] == "0"
        assert "ANTHROPIC_API_KEY" not in env

    def test_container_env_passthrough(self):
        config = _make_config()
        env = self.adapter.container_env(config, passthrough=True)
        assert env["ANTHROPIC_BASE_URL"] == ""
        assert env["ANTHROPIC_AUTH_TOKEN"] == ""
        assert "ANTHROPIC_API_KEY" not in env

    def test_container_env_passthrough_with_api_key(self):
        config = _make_config(agent_api_key="sk-test-key")
        env = self.adapter.container_env(config, passthrough=True)
        assert env["ANTHROPIC_API_KEY"] == "sk-test-key"


class TestAiderAdapter:
    def setup_method(self):
        self.adapter = AiderAdapter()

    def test_does_not_support_passthrough(self):
        assert self.adapter.supports_passthrough is False

    def test_build_cmd_uses_config_model(self):
        config = _make_config(agent_model="ollama/deepseek-coder")
        cmd = self.adapter.build_cmd(config, passthrough=False)
        assert cmd == ["aider", "--model", "ollama/deepseek-coder"]

    def test_build_cmd_default_model(self):
        config = _make_config(agent_model=AGENT_MODEL_DEFAULT)
        cmd = self.adapter.build_cmd(config, passthrough=False)
        assert cmd == ["aider", "--model", "ollama/qwen3-coder-32k"]

    def test_container_env_is_ollama(self):
        config = _make_config()
        env = self.adapter.container_env(config, passthrough=False)
        assert env["ANTHROPIC_AUTH_TOKEN"] == "ollama"
        assert "host.docker.internal" in env["ANTHROPIC_BASE_URL"]
