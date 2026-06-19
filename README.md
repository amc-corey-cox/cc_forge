# CC Forge

A CLI tool for safe, containerized AI agent sessions backed by local models.

## What is this?

Type `forge` in any git repository to get an interactive AI coding session where:

- The agent works in an isolated Docker container
- Changes go through a local Forgejo instance (not your filesystem)
- You review and approve work before pulling it to your real repo
- Everything runs on local hardware via Ollama — no cloud APIs needed

## What it protects against — and what it doesn't

forge exists to let an agent run with `--dangerously-skip-permissions` without that
being reckless. Be precise about what that buys you — over-trusting it is the real risk.

**What the isolation gives you (Phase 1):**

- **No host filesystem access.** The agent runs in a container with no host mount — it
  can't read your SSH keys, reach files outside its workspace, or `rm -rf` your machine.
  It only ever sees a clone pulled from Forgejo.
- **A review gate.** All its work lands as commits on a Forgejo PR; nothing reaches your
  real repo until *you* promote it. The agent has no GitHub remote and isn't handed your
  credentials, so it won't reach your upstream on its own.
- Non-root container user, plus memory/PID limits.

**What it does *not* give you (yet):**

- **No network egress control.** The container can reach the whole internet. A malicious
  or prompt-injected agent in dangerous mode can still exfiltrate your repo, call external
  APIs, or download and run arbitrary code. Network lockdown is on the roadmap (Phase 2+),
  not in v0.1.0.

In short: the isolation makes dangerous mode **safe against accidents and bad commits** —
an agent going off the rails can't wreck your host or your upstream — but **not** against a
*determined adversary* who controls the agent. Treat it as a guardrail for
trusted-but-fallible agents, not a sandbox for hostile code. (One nuance: forge never
hands the agent your GitHub credentials — any configured `FORGE_GITHUB_TOKEN` sits in a
shim-only `0600` file and GitHub access goes through the controlled `gh` shim — but since
the network is open, scope that token read-only so even a determined agent can't do much
with it.) See [DESIGN.md](DESIGN.md) for the full model and the egress-control options
under consideration.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Ollama running locally (see [docs/LOCAL-OLLAMA-SETUP.md](docs/LOCAL-OLLAMA-SETUP.md))
- Python 3.11+ and [uv](https://docs.astral.sh/uv/)

### Install

```bash
git clone https://github.com/amc-corey-cox/cc_forge.git
cd cc_forge
uv sync
```

### First-Time Setup

1. Start the forge infrastructure:
   ```bash
   docker compose -f docker/docker-compose.yml up -d
   ```

2. Open Forgejo at `http://localhost:3000` and create an admin account

3. Generate an API token in Forgejo (Settings > Applications > Generate Token)

4. Configure forge:
   ```bash
   mkdir -p ~/.config/forge
   cat > ~/.config/forge/config.env << 'EOF'
   FORGE_FORGEJO_TOKEN=your-token-here
   EOF
   ```

### Run a Session

```bash
# In any git repo — launches Claude Code with local Ollama:
forge

# Or use your Claude API key instead of local models:
forge run --claude

# Use Aider instead of Claude Code:
forge run --agent aider

# Check running sessions:
forge status

# Stop all sessions:
forge stop --all
```

What happens when you type `forge`:

1. The forge infrastructure (Forgejo + Ollama proxies) starts if Forgejo isn't already up.
2. Your repo is pushed to the local Forgejo instance.
3. An isolated container clones from Forgejo and drops you into an interactive
   Claude Code session.
4. The agent works, commits, and opens a PR — all inside Forgejo.

When the session ends you're back in your original shell. The agent's work lives
in Forgejo until you're ready to bring it over.

### Review and Promote

The agent's PR lands in Forgejo (`http://localhost:3000`). Read the diff there,
then promote it to GitHub when you're satisfied:

```bash
# From the same repo, on your workstation:
forge promote <forgejo-pr-number>
```

`forge promote` fetches the agent's branch from Forgejo, pushes it to your
GitHub remote, and opens a GitHub PR with the same title and description.

**Why promote runs on your machine:** The agent container can talk to Forgejo
but not to GitHub. Promotion is the deliberate step where reviewed work crosses
that boundary — your `gh` credentials stay with you, never inside the container.
You'll need `gh` authenticated. On a single machine, also set `FORGE_GITHUB_REPO`
(or `FORGE_GITHUB_OWNER`) in your config; if forge runs on a separate server, you
promote from your workstation and it infers the repo from `origin`. See
[docs/FORGE-USAGE.md](docs/FORGE-USAGE.md) for both setups.

### The Full Loop

A typical issue-to-PR cycle looks like this:

```
forge run --claude          # start a session
  ↳ agent works on the task
  ↳ agent runs /self-review and /complexity-audit
  ↳ agent opens a Forgejo PR
                            # session ends, you're back in your shell
forge promote 1             # push the PR to GitHub
```

See [docs/FORGE-USAGE.md](docs/FORGE-USAGE.md) for the detailed walkthrough.

## Documentation

- [docs/FORGE-USAGE.md](docs/FORGE-USAGE.md) — Running a session end-to-end
- [docs/WORKSTATION-SETUP.md](docs/WORKSTATION-SETUP.md) — Running forge against a remote server
- [DESIGN.md](DESIGN.md) — Architecture and safety model
- [ROADMAP.md](ROADMAP.md) — Implementation phases
- [AGENTS.md](AGENTS.md) — Instructions for AI agents working in this repo
- [docs/](docs/) — Operational guides (Ollama setup, Docker, agent frameworks)

## Status

**v0.1.0 — Phase 1 (proof of concept).** The human-driven single-issue loop: an agent
takes a task, works in isolation, self-reviews, and hands back a promotable PR. Validated
end-to-end, but exercised primarily on the maintainer's own setup — expect rough edges on
first adoption.

Not yet in v0.1.0: network egress control (see "What it protects against" above),
headless/batch runs, and automated multi-agent review. See [ROADMAP.md](ROADMAP.md).

## License

[AGPL-3.0-or-later](LICENSE). Commercial use, hosting, and support are welcome;
the copyleft just keeps derivatives — including hosted/SaaS modifications — open.
The open release will always remain available under AGPL-3.0. Contributions are
accepted under the DCO — see [CONTRIBUTING.md](CONTRIBUTING.md).
