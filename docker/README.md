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

## Network Isolation

All containers run on `forge-network`. Agent containers can only reach:
- Forgejo (for git clone/push)
- Ollama proxies (for AI inference)

They cannot reach the host filesystem, internet, or other services.
