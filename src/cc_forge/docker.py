"""Docker container lifecycle management for CC Forge."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import click
import docker
from docker.errors import NotFound, ImageNotFound

from cc_forge.config import ForgeConfig

CONTAINER_PREFIX = "forge-agent-"


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


def run_agent_container(
    config: ForgeConfig,
    repo_url: str,
    branch: str,
    repo_name: str,
    agent: str = "claude",
) -> str:
    """Launch an agent container on forge-network. Returns container ID."""
    client = _docker_client()
    image_tag = ensure_agent_image_built(config)

    container_name = f"{CONTAINER_PREFIX}{repo_name}-{int(time.time())}"

    # Rewrite clone URL for container network: localhost → forge-forgejo
    clone_url = repo_url.replace("://localhost:", "://forge-forgejo:")
    clone_url = clone_url.replace("://127.0.0.1:", "://forge-forgejo:")

    # Inject token into clone URL for auth
    if config.forgejo_token:
        clone_url = clone_url.replace(
            "://", f"://forge-agent:{config.forgejo_token}@"
        )

    # Rewrite Ollama URL for container network
    ollama_url = config.ollama_cpu_url
    ollama_url = ollama_url.replace("://localhost:", "://forge-ollama-proxy:")
    ollama_url = ollama_url.replace("://127.0.0.1:", "://forge-ollama-proxy:")

    container = client.containers.run(
        image_tag,
        detach=True,
        name=container_name,
        network="forge-network",
        environment={
            "FORGEJO_URL": config.forgejo_url,
            "FORGEJO_TOKEN": config.forgejo_token,
            "REPO_URL": clone_url,
            "REPO_BRANCH": branch,
            "FORGE_AGENT": agent,
            "OLLAMA_HOST": ollama_url,
            "ANTHROPIC_AUTH_TOKEN": "ollama",
            "ANTHROPIC_BASE_URL": ollama_url,
            "DISABLE_PROMPT_CACHING": "true",
            "API_TIMEOUT_MS": "3600000",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        },
        labels={"forge.role": "agent", "forge.repo": repo_name},
    )
    return container.id


def wait_for_ready(container_id: str, timeout: int = 60) -> None:
    """Wait for the entrypoint to finish cloning (repo dir exists)."""
    client = _docker_client()
    for _ in range(timeout):
        try:
            container = client.containers.get(container_id)
            if container.status != "running":
                logs = container.logs().decode(errors="replace")
                raise RuntimeError(
                    f"Agent container exited (status: {container.status}).\n"
                    f"Container logs:\n{logs}"
                )
            result = container.exec_run("test -d /workspace/repo/.git")
            if result.exit_code == 0:
                return
        except NotFound:
            raise RuntimeError("Agent container disappeared")
        time.sleep(1)
    raise RuntimeError("Timed out waiting for repo clone")


def exec_agent(container_id: str, agent: str = "claude", config: ForgeConfig | None = None) -> int:
    """Exec the agent interactively inside a running container. Returns exit code."""
    wait_for_ready(container_id)

    if agent == "claude":
        model = config.claude_model if config else "qwen2.5-coder:7b-instruct-q4_K_M"
        cmd = ["claude", "--dangerously-skip-permissions", "--model", model]
    elif agent == "aider":
        cmd = ["aider", "--model", "ollama/llama3.1"]
    else:
        cmd = ["/bin/bash"]

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
