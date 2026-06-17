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


def _forge_claude_state_dir() -> Path:
    return Path.home() / ".config" / "forge" / "claude-state"


def _claude_credentials_path() -> Path:
    """Return the path to Claude OAuth credentials (saved state preferred, then host)."""
    for candidate in (
        _forge_claude_state_dir() / ".credentials.json",
        Path.home() / ".claude" / ".credentials.json",
    ):
        if candidate.is_symlink():
            raise RuntimeError(f"Refusing to use symlinked credentials: {candidate}")
        if candidate.is_file():
            return candidate
    raise RuntimeError(
        "Claude credentials not found.\n"
        "Either set FORGE_CLAUDE_API_KEY or run 'claude' locally to authenticate."
    )


AGENT_UID = 1000  # Matches Dockerfile: useradd -u 1000 agent


def _add_tar_file(tar, name: str, data: bytes, mode: int = 0o644) -> None:
    """Add a file to a tar archive owned by the agent user."""
    import io
    import tarfile as _tarfile

    info = _tarfile.TarInfo(name=name)
    info.size = len(data)
    info.uid = AGENT_UID
    info.gid = AGENT_UID
    info.mode = mode
    tar.addfile(info, io.BytesIO(data))


def _add_tar_dir(tar, name: str) -> None:
    """Add a directory entry to a tar archive owned by the agent user."""
    import tarfile as _tarfile

    info = _tarfile.TarInfo(name=name)
    info.type = _tarfile.DIRTYPE
    info.uid = AGENT_UID
    info.gid = AGENT_UID
    info.mode = 0o755
    tar.addfile(info)


def _inject_agent_instructions(container, config: ForgeConfig) -> None:
    """Inject forge's agent instructions into the container, for any harness.

    Canonical source is docker/AGENTS.md (CLAUDE.md symlinks to it). The instructions
    describe the forge environment, so they live in the agent's home — not the cloned
    repo — and are surfaced where each supported harness reads them:
      - ~/.claude/CLAUDE.md     (Claude)
      - ~/AGENTS.md             (canonical; the cross-harness convention)
      - ~/.aider.conf.yml       (aider reads AGENTS.md as a read-only context file)
    """
    import io
    import tarfile

    docker_dir = Path(config.compose_file).parent
    agents_md = docker_dir / "AGENTS.md"
    if not agents_md.is_file():
        return
    data = agents_md.read_bytes()

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        _add_tar_dir(tar, ".claude/")
        _add_tar_file(tar, ".claude/CLAUDE.md", data)
        _add_tar_file(tar, "AGENTS.md", data)
        _add_tar_file(tar, ".aider.conf.yml", b"read:\n  - /home/agent/AGENTS.md\n")
    buf.seek(0)
    container.put_archive("/home/agent", buf)


def _copy_claude_config(container, config: ForgeConfig) -> None:
    """Copy Claude config into the container.

    When FORGE_CLAUDE_API_KEY is set, only injects onboarding bypass and CLAUDE.md.
    Otherwise, also injects OAuth credentials from host or saved state.
    """
    import io
    import tarfile

    need_credentials = not config.claude_api_key

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        _add_tar_dir(tar, ".claude/")

        if need_credentials:
            cred_path = _claude_credentials_path()
            state_dir = _forge_claude_state_dir()

            # Inject saved state as baseline (skip credentials — we'll add fresh ones)
            if state_dir.is_dir():
                for path in state_dir.rglob("*"):
                    rel = path.relative_to(state_dir)
                    if rel.name == ".credentials.json":
                        continue
                    arc_name = f".claude/{rel}"
                    if path.is_dir():
                        _add_tar_dir(tar, arc_name + "/")
                    else:
                        _add_tar_file(tar, arc_name, path.read_bytes())

            # Inject credentials once (saved-preferred, host fallback)
            _add_tar_file(tar, ".claude/.credentials.json",
                          cred_path.read_bytes(), mode=0o600)

        # $HOME/.claude.json — onboarding bypass + saved state
        # hasCompletedOnboarding lives here (NOT in settings.json)
        saved_claude_json = _forge_claude_state_dir() / ".claude.json"
        if saved_claude_json.is_file():
            _add_tar_file(tar, ".claude.json",
                          saved_claude_json.read_bytes(), mode=0o600)
        else:
            _add_tar_file(tar, ".claude.json",
                          b'{"hasCompletedOnboarding":true}', mode=0o600)
    buf.seek(0)

    container.put_archive("/home/agent", buf)


def _claude_environment(config: ForgeConfig) -> dict[str, str]:
    """Environment variables for Claude API pass-through."""
    env = {
        # Override Dockerfile defaults that would route to Ollama
        "ANTHROPIC_BASE_URL": "",
        "ANTHROPIC_AUTH_TOKEN": "",
        # Container agent can't write to npm global; skip auto-update
        "CLAUDE_CODE_SKIP_UPDATE": "1",
    }
    if config.claude_api_key:
        env["ANTHROPIC_API_KEY"] = config.claude_api_key
    return env


def _inject_git_credentials(container, config: ForgeConfig) -> None:
    """Inject git credentials into the container without exposing the token as an env var."""
    import io
    import tarfile
    from urllib.parse import quote, urlsplit

    if not config.forgejo_token or not config.forgejo_url:
        return

    forgejo_url = _rewrite_url(config.forgejo_url, "forge-forgejo")
    parts = urlsplit(forgejo_url)
    # git's store helper matches on scheme + host:port; drop any path/query.
    # Percent-encode the token so reserved chars (@ : /) don't corrupt the URL.
    token = quote(config.forgejo_token, safe="")
    cred_line = f"{parts.scheme}://forge-agent:{token}@{parts.netloc}\n"

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        _add_tar_file(tar, ".git-credentials", cred_line.encode(), mode=0o600)
    buf.seek(0)
    container.put_archive("/home/agent", buf)


# Path the gh shim sources its credentials from. Must match the value in
# docker/gh-shim.sh. Documented as a constant so the producer and consumer of
# the file reference the same location.
SHIM_CREDENTIALS_PATH = "/home/agent/.config/forge-shim/credentials"


def _inject_shim_credentials(container, config: ForgeConfig) -> None:
    """Write the gh-shim credentials file into the container.

    The shim sources this file at startup. Tokens go into a 0600 file rather
    than env vars so they are not visible to `docker inspect` or sibling
    processes inside the container.
    """
    import io
    import shlex
    import tarfile

    # Each pair: (env var name the shim expects, config value to write)
    pairs: list[tuple[str, str]] = []
    if config.forgejo_url:
        pairs.append(("FORGEJO_URL", _rewrite_url(config.forgejo_url, "forge-forgejo")))
    if config.forgejo_token:
        pairs.append(("FORGEJO_TOKEN", config.forgejo_token))
    if config.github_token:
        pairs.append(("FORGE_GITHUB_TOKEN", config.github_token))
    if config.github_repo:
        pairs.append(("FORGE_GITHUB_REPO", config.github_repo))
    if config.github_owner:
        pairs.append(("FORGE_GITHUB_OWNER", config.github_owner))

    if not pairs:
        return

    lines = [f"{key}={shlex.quote(value)}\n" for key, value in pairs]
    content = "".join(lines).encode()

    # SHIM_CREDENTIALS_PATH = /home/agent/.config/forge-shim/credentials.
    # We need to create the .config and forge-shim directories, then the file.
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        _add_tar_dir(tar, ".config/")
        _add_tar_dir(tar, ".config/forge-shim/")
        _add_tar_file(tar, ".config/forge-shim/credentials", content, mode=0o600)
    buf.seek(0)
    container.put_archive("/home/agent", buf)


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

    # Tokens (Forgejo + GitHub) are injected via files, not env vars, so they
    # are not visible to `docker inspect`. See _inject_git_credentials and
    # _inject_shim_credentials.
    environment = {
        "REPO_URL": clone_url,
        "REPO_BRANCH": branch,
        "FORGE_AGENT": agent,
    }

    if claude_passthrough:
        environment.update(_claude_environment(config))
    else:
        environment.update(_ollama_environment(config))

    # Only expose host gateway when the agent reaches Ollama on the host.
    ollama_url = _rewrite_url(config.ollama_cpu_url, "host.docker.internal")
    needs_gateway = (not claude_passthrough) and "host.docker.internal" in ollama_url
    extra_hosts = {"host.docker.internal": "host-gateway"} if needs_gateway else {}

    container = client.containers.create(
        image_tag,
        name=container_name,
        network="forge-network",
        environment=environment,
        labels={"forge.role": "agent", "forge.repo": repo_name},
        extra_hosts=extra_hosts or None,
        stdin_open=True,
        tty=True,
        mem_limit=config.agent_mem_limit,
        pids_limit=config.agent_pids_limit,
    )

    try:
        _inject_git_credentials(container, config)
        _inject_shim_credentials(container, config)
        if claude_passthrough:
            _copy_claude_config(container, config)
        # After the Claude state restore, so the canonical instructions always win
        # (restored state can carry a stale ~/.claude/CLAUDE.md from a prior session).
        _inject_agent_instructions(container, config)
        container.start()
    except Exception:
        try:
            container.remove(force=True)
        except docker.errors.APIError:
            pass
        raise

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


def save_claude_credentials(container_id: str) -> None:
    """Save full Claude state from container back to host for reuse."""
    import io
    import shutil
    import tarfile
    import tempfile

    client = _docker_client()
    state_dir = _forge_claude_state_dir()
    _SKIP_PATTERNS = {"debug", "session-env", "file-history", "shell-snapshots"}

    try:
        container = client.containers.get(container_id)
    except NotFound:
        return

    try:
        bits, _ = container.get_archive("/home/agent/.claude/.")
    except docker.errors.APIError:
        click.echo("Warning: could not read Claude state from container.", err=True)
        return

    buf = io.BytesIO()
    for chunk in bits:
        buf.write(chunk)
    buf.seek(0)

    state_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        dir=state_dir.parent, prefix="claude-state-tmp-"
    ) as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        with tarfile.open(fileobj=buf, mode="r") as tar:
            for member in tar.getmembers():
                parts = Path(member.name).parts
                if any(p in _SKIP_PATTERNS for p in parts):
                    continue
                if ".git" in parts:
                    continue
                tar.extract(member, tmp_dir, filter="data")

        extracted = tmp_dir / ".claude" if (tmp_dir / ".claude").exists() else tmp_dir
        if state_dir.exists():
            shutil.rmtree(state_dir)
        shutil.move(str(extracted), str(state_dir))

    state_dir.chmod(0o700)
    cred_file = state_dir / ".credentials.json"
    if cred_file.is_file():
        cred_file.chmod(0o600)

    # Also save ~/.claude.json (onboarding/account state)
    try:
        bits2, _ = container.get_archive("/home/agent/.claude.json")
    except docker.errors.APIError:
        return

    buf2 = io.BytesIO()
    for chunk in bits2:
        buf2.write(chunk)
    buf2.seek(0)
    with tarfile.open(fileobj=buf2, mode="r") as tar:
        for member in tar.getmembers():
            if member.isreg():
                f = tar.extractfile(member)
                if f:
                    state_dir.mkdir(parents=True, exist_ok=True)
                    target = state_dir / ".claude.json"
                    tmp = state_dir / ".claude.json.tmp"
                    tmp.write_bytes(f.read())
                    tmp.chmod(0o600)
                    tmp.replace(target)
                break


def cleanup_container(container_id: str) -> None:
    """Stop and remove a container."""
    client = _docker_client()
    try:
        container = client.containers.get(container_id)
        container.stop(timeout=5)
        container.remove()
    except NotFound:
        pass  # Already removed — nothing to clean up
    except docker.errors.APIError:
        pass  # Removal already in progress or other transient error


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
