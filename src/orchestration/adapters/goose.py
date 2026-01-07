"""
Goose orchestration adapter.

Wraps Block's Goose framework to implement the CC Forge Orchestrator protocol.
Goose provides MCP integration and subagent orchestration out of the box.

See: https://github.com/block/goose
"""

import asyncio
import json
import shutil
import subprocess
from typing import Any

from ..base import (
    AgentConfig,
    AgentResult,
    BaseOrchestrator,
    OrchestratorError,
    TeamConfig,
)


class GooseOrchestrator(BaseOrchestrator):
    """
    Orchestrator implementation using Block's Goose framework.

    Goose is a local-first AI agent that supports:
    - Multiple LLM providers (including Ollama for local models)
    - MCP (Model Context Protocol) for tool integration
    - Subagent orchestration for multi-agent workflows
    """

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._goose_path: str | None = None
        self._provider: str = config.get("provider", "ollama") if config else "ollama"
        self._model: str = config.get("model", "qwen2.5:14b") if config else "qwen2.5:14b"
        self._goose_version: str = "unknown"

    @property
    def name(self) -> str:
        return "Goose"

    @property
    def version(self) -> str:
        return self._goose_version

    async def _do_initialize(self) -> None:
        """Initialize Goose - verify it's installed and configured."""
        # Check if goose CLI is available
        self._goose_path = shutil.which("goose")
        if not self._goose_path:
            raise OrchestratorError(
                "Goose CLI not found. Install from: https://github.com/block/goose\n"
                "Quick install: curl -fsSL https://github.com/block/goose/releases/download/stable/install.sh | bash"
            )

        # Get version
        try:
            result = await asyncio.create_subprocess_exec(
                self._goose_path,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()
            self._goose_version = stdout.decode().strip()
        except Exception as e:
            self._log(f"Warning: Could not get Goose version: {e}")

        # Verify provider is configured
        await self._verify_provider()

        self._log(f"Initialized with provider={self._provider}, model={self._model}")

    async def _verify_provider(self) -> None:
        """Verify the configured LLM provider is available."""
        if self._provider == "ollama":
            # Check if Ollama is running
            ollama_path = shutil.which("ollama")
            if not ollama_path:
                raise OrchestratorError(
                    "Ollama not found but configured as provider. "
                    "Install from: https://ollama.ai"
                )
            # Check if model is available
            try:
                result = await asyncio.create_subprocess_exec(
                    ollama_path,
                    "list",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await result.communicate()
                if self._model.split(":")[0] not in stdout.decode():
                    self._log(
                        f"Warning: Model {self._model} not found in Ollama. "
                        f"Run: ollama pull {self._model}"
                    )
            except Exception as e:
                self._log(f"Warning: Could not verify Ollama model: {e}")

    async def run_agent(
        self,
        config: AgentConfig,
        task: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResult:
        """
        Run a single agent task using Goose.

        Uses Goose's CLI in non-interactive mode for programmatic execution.
        """
        if not self._initialized:
            await self.initialize()

        model = config.model or self._model
        logs: list[str] = []
        errors: list[str] = []

        # Build the prompt with system context
        full_prompt = self._build_prompt(config, task, context)

        try:
            # Run goose in non-interactive mode
            # Note: This uses goose run which executes a single task
            result = await asyncio.create_subprocess_exec(
                self._goose_path,
                "run",
                "--provider",
                self._provider,
                "--model",
                model,
                "--text",
                full_prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()

            output = stdout.decode()
            if stderr:
                errors.append(stderr.decode())

            success = result.returncode == 0
            logs.append(f"Goose exit code: {result.returncode}")

            return AgentResult(
                success=success,
                output=output,
                agent_name=config.name,
                iterations=1,
                logs=logs,
                errors=errors,
                metadata={
                    "model": model,
                    "provider": self._provider,
                    "role": config.role.value,
                },
            )

        except Exception as e:
            return AgentResult(
                success=False,
                output=None,
                agent_name=config.name,
                errors=[str(e)],
                metadata={"exception": type(e).__name__},
            )

    async def run_team(
        self,
        config: TeamConfig,
        task: str,
        context: dict[str, Any] | None = None,
    ) -> list[AgentResult]:
        """
        Run a team of agents using Goose's subagent orchestration.

        Supports sequential, parallel, and hierarchical workflows.
        """
        if not self._initialized:
            await self.initialize()

        results: list[AgentResult] = []
        shared_context = dict(context) if context else {}

        if config.workflow == "parallel":
            # Run all agents concurrently
            tasks = [
                self.run_agent(agent_config, task, shared_context)
                for agent_config in config.agents
            ]
            results = await asyncio.gather(*tasks)

        elif config.workflow == "hierarchical":
            # First agent is coordinator, others are workers
            if not config.agents:
                return results

            coordinator = config.agents[0]
            workers = config.agents[1:]

            # Run coordinator first to break down task
            coord_result = await self.run_agent(coordinator, task, shared_context)
            results.append(coord_result)

            if coord_result.success and workers:
                # Parse subtasks from coordinator output (simplified)
                subtasks = self._parse_subtasks(coord_result.output)
                worker_tasks = []
                for i, subtask in enumerate(subtasks):
                    worker = workers[i % len(workers)]
                    worker_tasks.append(
                        self.run_agent(worker, subtask, shared_context)
                    )
                if worker_tasks:
                    worker_results = await asyncio.gather(*worker_tasks)
                    results.extend(worker_results)

        else:  # sequential (default)
            # Run agents one after another, passing context forward
            for agent_config in config.agents:
                result = await self.run_agent(agent_config, task, shared_context)
                results.append(result)

                # Add output to shared context for next agent
                if result.success and result.output:
                    shared_context[f"{agent_config.name}_output"] = result.output

        return results

    def get_available_models(self) -> list[str]:
        """Get models available through configured provider."""
        if self._provider == "ollama":
            try:
                result = subprocess.run(
                    ["ollama", "list"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split("\n")[1:]  # Skip header
                    return [line.split()[0] for line in lines if line]
            except Exception:
                pass
        return [self._model]  # Fallback to configured model

    def get_available_tools(self) -> list[str]:
        """Get tools available through Goose MCP integration."""
        # Goose tools are configured via MCP servers
        # This returns a basic list; full list depends on installed MCP servers
        return [
            "file_read",
            "file_write",
            "shell_execute",
            "git_operations",
            "web_fetch",
            # Add MCP server tools dynamically based on config
        ]

    def _build_prompt(
        self,
        config: AgentConfig,
        task: str,
        context: dict[str, Any] | None,
    ) -> str:
        """Build the full prompt including system instructions and context."""
        parts = [config.system_prompt, "", f"Task: {task}"]

        if context:
            parts.append("")
            parts.append("Context:")
            for key, value in context.items():
                if isinstance(value, dict):
                    parts.append(f"  {key}: {json.dumps(value, indent=2)}")
                else:
                    parts.append(f"  {key}: {value}")

        return "\n".join(parts)

    def _parse_subtasks(self, coordinator_output: str) -> list[str]:
        """Parse subtasks from coordinator output (simplified)."""
        # Simple heuristic: look for numbered or bulleted items
        lines = coordinator_output.split("\n")
        subtasks = []
        for line in lines:
            line = line.strip()
            if line and (
                line[0].isdigit()
                or line.startswith("-")
                or line.startswith("*")
            ):
                # Remove bullet/number prefix
                task = line.lstrip("0123456789.-*) ").strip()
                if task:
                    subtasks.append(task)
        return subtasks if subtasks else [coordinator_output]
