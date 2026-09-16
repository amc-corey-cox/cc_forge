"""Tests for the agent adapter interface and registry."""
from __future__ import annotations

import json

from cc_forge.agents import (
    REGISTRY,
    AgentAdapter,
    AiderAdapter,
    ClaudeAdapter,
    OpenCodeAdapter,
    _opencode_config,
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
        assert isinstance(REGISTRY["opencode"], OpenCodeAdapter)


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
        assert cmd == ["claude", "--dangerously-skip-permissions", "--model", "qwen3-coder-64k"]

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
        assert env["CLAUDE_CODE_SKIP_UPDATE"] == "1"
        assert "ANTHROPIC_API_KEY" not in env

    def test_container_env_passthrough(self):
        config = _make_config()
        env = self.adapter.container_env(config, passthrough=True)
        assert env["ANTHROPIC_BASE_URL"] == ""
        assert env["ANTHROPIC_AUTH_TOKEN"] == ""
        assert env["CLAUDE_CODE_SKIP_UPDATE"] == "1"
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
        assert cmd == ["aider", "--model", "ollama/qwen3-coder-64k"]

    def test_container_env_is_ollama(self):
        config = _make_config()
        env = self.adapter.container_env(config, passthrough=False)
        assert env["ANTHROPIC_AUTH_TOKEN"] == "ollama"
        assert "host.docker.internal" in env["ANTHROPIC_BASE_URL"]
        assert env["CLAUDE_CODE_SKIP_UPDATE"] == "1"

    def test_container_env_sets_ollama_api_base_for_aider(self):
        """litellm (aider's backend) reads OLLAMA_API_BASE and ignores
        OLLAMA_HOST; without it aider falls back to localhost in the container."""
        config = _make_config()
        env = self.adapter.container_env(config, passthrough=False)
        assert env["OLLAMA_API_BASE"] == env["OLLAMA_HOST"]
        assert "host.docker.internal" in env["OLLAMA_API_BASE"]


class TestOpenCodeAdapter:
    def setup_method(self):
        self.adapter = OpenCodeAdapter()

    def test_does_not_support_passthrough(self):
        assert self.adapter.supports_passthrough is False

    def test_build_cmd_qualifies_model_with_provider(self):
        """OpenCode addresses models as provider/model, unlike Claude Code."""
        config = _make_config(agent_model=AGENT_MODEL_DEFAULT)
        cmd = self.adapter.build_cmd(config, passthrough=False)
        assert cmd == ["opencode", "-m", f"ollama/{AGENT_MODEL_DEFAULT}", "--auto"]

    def test_build_cmd_uses_config_model(self):
        config = _make_config(agent_model="deepseek-coder")
        cmd = self.adapter.build_cmd(config, passthrough=False)
        assert cmd == ["opencode", "-m", "ollama/deepseek-coder", "--auto"]

    def test_build_cmd_does_not_double_qualify(self):
        """A model copied from aider's convention already carries the prefix."""
        config = _make_config(agent_model="ollama/deepseek-coder")
        cmd = self.adapter.build_cmd(config, passthrough=False)
        assert cmd == ["opencode", "-m", "ollama/deepseek-coder", "--auto"]

    def test_config_points_at_ollama_openai_endpoint(self):
        """OpenCode speaks the OpenAI-compatible API, not Anthropic's."""
        config = _make_config()
        doc = json.loads(_opencode_config(config, "ollama/qwen3-coder-64k"))
        opts = doc["provider"]["ollama"]["options"]
        assert opts["baseURL"].endswith("/v1")
        assert "host.docker.internal" in opts["baseURL"]
        assert "qwen3-coder-64k" in doc["provider"]["ollama"]["models"]

    def test_config_preapproves_permissions(self):
        """The container session is unattended; prompting would hang it."""
        config = _make_config()
        doc = json.loads(_opencode_config(config, "ollama/qwen3-coder-64k"))
        assert doc["permission"]["bash"] == "allow"
        assert doc["permission"]["edit"] == "allow"
