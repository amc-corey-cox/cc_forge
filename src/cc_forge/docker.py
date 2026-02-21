"""Docker container lifecycle management for CC Forge."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import click
import docker
from docker.errors import NotFound, ImageNotFound

from cc_forge.config import ForgeConfig

CONTAINER_PREFIX = "forge-agent-"


def _rewrite_url(url: str, docker_host: str) -> str:
    """Rewrite localhost/127.0.0.1 URLs to use a Docker network hostname."""
    for local in ("localhost", "127.0.0.1"):
        url = url.replace(f"://{local}:", f"://{docker_host}:")
        url = url.replace(f"://{local}/", f"://{docker_host}/")
        # Handle URLs ending without port or trailing slash
        if url.endswith(f"://{local}"):
            url = url.replace(f"://{local}", f"://{docker_host}")
    return url


def _docker_client() -> docker.DockerClient:
    return docker.from_env()


def ensure_infrastructure_running(config: ForgeConfig) -> None:
    """Start Forgejo + Ollama proxies via docker compose if not already running."""
    client = _docker_client()
    try:
        forgejo = client.containers.get("forge-forgejo")
        if forgejo.status == "running":
            return
    except NotFound:
        pass  # Container doesn't exist yet — need to start infrastructure

    compose_file = config.compose_file
    if not Path(compose_file).is_file():
        raise RuntimeError(f"Compose file not found: {compose_file}")

    subprocess.run(
        ["docker", "compose", "-f", compose_file, "up", "-d"],
        check=True,
    )

    # Wait for Forgejo to become reachable
    for _ in range(30):
        try:
            forgejo = client.containers.get("forge-forgejo")
            if forgejo.status == "running":
                return
        except NotFound:
            pass  # Container not created yet — keep waiting
        time.sleep(1)

    raise RuntimeError("Forgejo container did not start within 30 seconds")


def ensure_agent_image_built(config: ForgeConfig) -> str:
    """Build the agent image if it doesn't exist. Returns the image tag."""
    client = _docker_client()
    image_tag = config.agent_image

    try:
        client.images.get(image_tag)
        return image_tag
    except ImageNotFound:
        pass

    dockerfile_dir = Path(config.compose_file).parent
    dockerfile = dockerfile_dir / "Dockerfile.agent"
    if not dockerfile.is_file():
        raise RuntimeError(f"Dockerfile.agent not found in {dockerfile_dir}")

    click.echo(f"Building agent image {image_tag}...")
    client.images.build(
        path=str(dockerfile_dir),
        dockerfile="Dockerfile.agent",
        tag=image_tag,
        rm=True,
    )
    return image_tag


def _ollama_environment(config: ForgeConfig) -> dict[str, str]:
    """Environment variables for local Ollama backend."""
    ollama_url = _rewrite_url(config.ollama_cpu_url, "host.docker.internal")
    return {
        "OLLAMA_HOST": ollama_url,
        "ANTHROPIC_AUTH_TOKEN": "ollama",
        "ANTHROPIC_BASE_URL": ollama_url,
        "DISABLE_PROMPT_CACHING": "true",
        "API_TIMEOUT_MS": "3600000",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1",
        "MAX_THINKING_TOKENS": "0",
    }


def _claude_environment() -> dict[str, str]:
    """Environment variables for Claude API pass-through."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Required for --claude pass-through mode.\n"
            "Set it in your shell environment before running this command."
        )
    return {
        "ANTHROPIC_API_KEY": api_key,
        # Override Dockerfile defaults that would route to Ollama
        "ANTHROPIC_BASE_URL": "",
        "ANTHROPIC_AUTH_TOKEN": "",
    }


def run_agent_container(
    config: ForgeConfig,
    repo_url: str,
    branch: str,
    repo_name: str,
    agent: str = "claude",
    claude_passthrough: bool = False,
) -> str:
    """Launch an agent container on forge-network. Returns container ID."""
    client = _docker_client()
    image_tag = ensure_agent_image_built(config)

    container_name = f"{CONTAINER_PREFIX}{repo_name}-{int(time.time())}"

    # Rewrite URLs for container network: localhost → Docker service names.
    clone_url = _rewrite_url(repo_url, "forge-forgejo")
    forgejo_url = _rewrite_url(config.forgejo_url, "forge-forgejo")

    environment = {
        "FORGEJO_URL": forgejo_url,
        "FORGEJO_TOKEN": config.forgejo_token,
        "REPO_URL": clone_url,
        "REPO_BRANCH": branch,
        "FORGE_AGENT": agent,
    }

    if claude_passthrough:
        environment.update(_claude_environment())
    else:
        environment.update(_ollama_environment(config))

    container = client.containers.run(
        image_tag,
        detach=True,
        name=container_name,
        network="forge-network",
        environment=environment,
        labels={"forge.role": "agent", "forge.repo": repo_name},
        extra_hosts={"host.docker.internal": "host-gateway"},
    )
    return container.id


def wait_for_ready(container_id: str, timeout: int = 60) -> None:
    """Wait for the entrypoint to finish cloning (repo dir exists)."""
    client = _docker_client()
    for _ in range(timeout):
        try:
            container = client.containers.get(container_id)
            if container.status in ("exited", "dead"):
                logs = container.logs().decode(errors="replace")
                raise RuntimeError(
                    f"Agent container exited (status: {container.status}).\n"
                    f"Container logs:\n{logs}"
                )
            if container.status == "running":
                result = container.exec_run("test -d /workspace/repo/.git")
                if result.exit_code == 0:
                    return
        except NotFound:
            raise RuntimeError("Agent container disappeared")
        time.sleep(1)
    # Include logs in timeout error for diagnosability
    try:
        container = client.containers.get(container_id)
        logs = container.logs().decode(errors="replace")
    except NotFound:
        logs = "(container not found)"
    raise RuntimeError(f"Timed out waiting for repo clone.\nContainer logs:\n{logs}")


def _build_agent_cmd(agent: str, config: ForgeConfig, claude_passthrough: bool = False) -> list[str]:
    """Build the command to run inside the agent container."""
    if agent == "claude":
        cmd = ["claude", "--dangerously-skip-permissions"]
        if not claude_passthrough:
            cmd += ["--model", config.claude_model]
    elif agent == "aider":
        cmd = ["aider", "--model", "ollama/llama3.1"]
    else:
        cmd = ["/bin/bash"]
    return cmd


def exec_agent(
    container_id: str,
    agent: str,
    config: ForgeConfig,
    claude_passthrough: bool = False,
) -> int:
    """Exec the agent interactively inside a running container. Returns exit code."""
    wait_for_ready(container_id)

    cmd = _build_agent_cmd(agent, config, claude_passthrough)

    docker_cmd = ["docker", "exec", "-w", "/workspace/repo"]
    if sys.stdin.isatty():
        docker_cmd += ["-it"]
    docker_cmd.append(container_id)
    docker_cmd += cmd

    result = subprocess.run(docker_cmd)
    return result.returncode


def cleanup_container(container_id: str) -> None:
    """Stop and remove a container."""
    client = _docker_client()
    try:
        container = client.containers.get(container_id)
        container.stop(timeout=5)
        container.remove()
    except NotFound:
        pass  # Already removed — nothing to clean up


def stop_container(container_id: str) -> None:
    """Stop and remove a forge container."""
    cleanup_container(container_id)


def list_forge_containers() -> list[dict]:
    """List all running forge agent containers."""
    client = _docker_client()
    containers = client.containers.list(
        filters={"label": "forge.role=agent"},
    )
    return [
        {
            "id": c.id,
            "name": c.name,
            "status": c.status,
            "repo": c.labels.get("forge.repo", "unknown"),
        }
        for c in containers
    ]
