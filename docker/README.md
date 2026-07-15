# CC Forge Docker Stack

Docker infrastructure for CC Forge: Forgejo (local git hosting) + Ollama proxies + agent containers.

## Architecture

```
Host System
│
├─ Ollama (:11434) — schedules across GPU, spills over to CPU
│
└─ forge-network (Docker bridge)
   ├─ ollama-proxy (:11434)  ──▶  host Ollama
   ├─ Forgejo (:3000)
   └─ Agent Container  ──▶  clones from Forgejo; reaches Ollama via ollama-proxy
```

## Services

### `forge-forgejo` — Local Git Hosting

- Image: `codeberg.org/forgejo/forgejo:14`
- Port 3000: Web UI and HTTP git
- Port 222: SSH git
- Persistent volume: `forgejo-data`

### `forge-ollama-proxy` — Ollama Proxy

Forwards container traffic to the host Ollama service (port 11434), which schedules
across the GPU and spills over to CPU on its own.

### `forge-runner` — CI Runner (Forgejo Actions)

Runs your existing `.github/workflows/ci.yml` on pull requests targeting `main` (and pushes
to `main`), so agent PRs get the same CI they'd hit on GitHub. See [CI (Forgejo Actions)](#ci-forgejo-actions)
below for setup.

## Quick Start

Run these from the `docker/` directory (there's no top-level compose file). First set
`FORGE_DOCKER_GID` in `docker/.env` — the `runner` service requires it (see
[CI (Forgejo Actions)](#ci-forgejo-actions)), so `docker compose` errors without it:

```bash
# Start infrastructure
docker compose up -d

# Check services
docker compose ps
```

Then open `http://localhost:3000` to set up Forgejo (create admin, generate API token).

> **Note:** `docker compose up -d` also starts the `runner` service (container `forge-runner`),
> which will restart until it's registered — see [First-time runner registration](#first-time-runner-registration).
> Automating this bootstrap (so the runner self-registers) is tracked in #98.

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

Forgejo also reads `.github/workflows`, so it runs your existing `.github/workflows/ci.yml` —
one workflow for both systems, no separate Forgejo copy to maintain. It runs on every pull
request targeting `main`, and on pushes to `main` itself; a feature-branch push alone doesn't
trigger CI — the PR is the gate. This gives agent PRs the same test gate they'd get on GitHub,
and makes CI/PR events the entry point for future review agents.

The workflow used for a PR is read from the *base* branch, so `.github/workflows/ci.yml` must
be on Forgejo `main` for PRs to be gated (it already is, mirrored from GitHub).

Resolving `uses:` steps (`actions/checkout`, `setup-uv`) fetches them from `github.com`
(`FORGEJO__actions__DEFAULT_ACTIONS_URL`), so the runner host needs outbound GitHub access —
or point `FORGE_FORGEJO_ACTIONS_URL` at a local action mirror.

### Trust boundary

The `runner` service (container `forge-runner`) mounts the host Docker socket
(`/var/run/docker.sock`) so it can spawn job containers via the host daemon. This is a **deliberate, accepted trade-off**: a
container with the Docker socket can control the host, so the runner is a different trust
domain than the untrusted *agent* container. It's justified because agents must run real CI,
and it stays isolated on `forge-network`. Job containers it spawns are unprivileged.

### First-time runner registration

The daemon needs a registered `/data/.runner` file before it will start. Generate a
registration token, then register once into the `runner-data` volume. Generate the token as
the `git` user — Forgejo refuses to run its CLI as root:

```bash
TOKEN=$(docker exec -u git forge-forgejo forgejo actions generate-runner-token)

docker compose run --rm --entrypoint forgejo-runner runner \
  register --no-interactive \
  --instance http://forge-forgejo:3000 \
  --token "$TOKEN" \
  --name forge-runner \
  --labels "ubuntu-latest:docker://catthehacker/ubuntu:act-latest"

docker compose up -d runner
```

The runner needs the host's `docker` group to use the mounted socket, so set `FORGE_DOCKER_GID`
in `docker/.env` to the gid from `getent group docker` on the host. It's required and
host-specific — there's no default, so a mismatch fails fast rather than silently breaking
socket access. Enabling Actions on Forgejo restarts the `forge-forgejo` container, so do this
when no agent session is running.

### Addressing: ROOT_URL vs. the runner's clone URL

Two Forgejo addresses matter, and they're separate. Job containers clone via the runner's
registered `--instance` URL (`http://forge-forgejo:3000`) — they share `forge-network` and
reach Forgejo by that container name, so checkout works regardless of `ROOT_URL`. `ROOT_URL`
(set via `FORGE_FORGEJO_ROOT_URL` in `docker/.env`) only governs the links Forgejo shows
humans; point it at the host's name so browsing from other devices isn't redirected to
`localhost`. The compose default is `http://localhost:3000/` (works only on the host itself) —
e.g. set `FORGE_FORGEJO_ROOT_URL=http://myhost:3000/` and `FORGE_FORGEJO_DOMAIN=myhost`.
