# CC Forge Docker Stack

Docker infrastructure for CC Forge: Forgejo (local git hosting) + Ollama proxies + agent containers.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│ Host System                                                  │
│                                                              │
│  Ollama CPU (:11434)    Ollama GPU (:11435)                 │
│       │                       │                              │
│  ┌────┼───────────────────────┼──────────────────────────┐  │
│  │    │   forge-network       │                          │  │
│  │    ▼                       ▼                          │  │
│  │  ollama-proxy         ollama-gpu-proxy                │  │
│  │  (:11434)             (:11435)                        │  │
│  │    │                       │                          │  │
│  │    └───────────┬───────────┘                          │  │
│  │                │                                      │  │
│  │    ┌───────────▼───────────────┐   ┌──────────────┐  │  │
│  │    │  Agent Container          │   │   Forgejo    │  │  │
│  │    │  (clones from Forgejo)    │──▶│   (:3000)    │  │  │
│  │    │  Claude Code / Aider      │   │              │  │  │
│  │    └───────────────────────────┘   └──────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## Services

### `forge-forgejo` — Local Git Hosting

- Image: `codeberg.org/forgejo/forgejo:14`
- Port 3000: Web UI and HTTP git
- Port 222: SSH git
- Persistent volume: `forgejo-data`

### `forge-ollama-proxy` — CPU Ollama Proxy

Forwards container traffic to host Ollama CPU service (port 11434).

### `forge-ollama-gpu-proxy` — GPU Ollama Proxy

Forwards container traffic to host Ollama GPU/Vulkan service (port 11435).

### `forge-runner` — CI Runner (Forgejo Actions)

Runs `.forgejo/workflows/` on push and PR, so agent PRs get the same CI they'd hit on
GitHub. See [CI (Forgejo Actions)](#ci-forgejo-actions) below for setup.

## Quick Start

```bash
# Start infrastructure
docker compose up -d

# Check services
docker compose ps
```

Then open `http://localhost:3000` to set up Forgejo (create admin, generate API token).

## Agent Container

The agent container (`Dockerfile.agent`) is built and managed by the `forge` CLI. It:

1. Clones a repo from Forgejo (no host mount)
2. Configures git credentials for push access
3. Starts Claude Code or Aider
4. Connects to Ollama via the proxy containers

### Manual Build (if needed)

```bash
docker build -f Dockerfile.agent -t cc-forge-agent:latest .
```

## Network

All containers run on `forge-network` (a Docker bridge network). Agent containers interact with:
- Forgejo (for git clone/push)
- Ollama proxies (for AI inference)

The primary isolation boundary is **no host filesystem mount** — agents clone from Forgejo rather
than bind-mounting your working directory. The current bridge network does not block outbound
internet access; egress restrictions are planned for Phase 2.

## CI (Forgejo Actions)

Forgejo Actions runs `.forgejo/workflows/ci.yml` (a near-verbatim mirror of the GitHub
Actions workflow) whenever a branch is pushed or a PR is opened. This gives agent PRs the
same test gate they'd get on GitHub — and makes CI/PR events the entry point for future
review agents.

### Trust boundary

The `forge-runner` service mounts the host Docker socket (`/var/run/docker.sock`) so it can
spawn job containers via the host daemon. This is a **deliberate, accepted trade-off**: a
container with the Docker socket can control the host, so the runner is a different trust
domain than the untrusted *agent* container. It's justified because agents must run real CI,
and it stays isolated on `forge-network`. Job containers it spawns are unprivileged.

### First-time runner registration

The daemon needs a registered `/data/.runner` file before it will start. On the Forgejo host,
generate a registration token (Forgejo → Site Administration → Actions → Runners, or the CLI),
then register once into the `runner-data` volume:

```bash
docker compose run --rm --entrypoint forgejo-runner runner \
  register --no-interactive \
  --instance http://forgejo:3000 \
  --token <REGISTRATION_TOKEN> \
  --name forge-runner \
  --labels "ubuntu-latest:docker://catthehacker/ubuntu:act-latest"

docker compose up -d runner
```

Enabling Actions on Forgejo restarts the `forge-forgejo` container, so do this when no agent
session is running.

### Known gotcha: clone URL

Job containers clone via Forgejo's `ROOT_URL`. If that resolves to `localhost` or a LAN
hostname the job container can't reach, checkout fails — the containers share `forge-network`
and reach Forgejo as `forge-forgejo:3000`. Expect to reconcile `ROOT_URL` (or the runner's
fetch URL) with what a job container can actually resolve when bringing the runner up.
