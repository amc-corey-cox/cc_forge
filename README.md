# CC Forge

A CLI tool for safe, containerized AI agent sessions backed by local models.

## What is this?

Type `forge` in any git repository to get an interactive AI coding session where:

- The agent works in an isolated Docker container
- Changes go through a local Forgejo instance (not your filesystem)
- You review and approve work before pulling it to your real repo
- Everything runs on local hardware via Ollama — no cloud APIs needed

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

1. Forgejo and Ollama proxies start automatically if they aren't running.
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

**Why promote runs on the workstation:** The agent container can talk to Forgejo
but not to GitHub. Promotion is the deliberate step where reviewed work crosses
that boundary — your `gh` credentials stay on your machine, never inside the
container. You'll need `gh` authenticated and `FORGE_GITHUB_REPO` (or
`FORGE_GITHUB_OWNER`) in your config — see
[docs/FORGE-USAGE.md](docs/FORGE-USAGE.md) for details.

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
- [DESIGN.md](DESIGN.md) — Architecture and safety model
- [ROADMAP.md](ROADMAP.md) — Implementation phases
- [AGENTS.md](AGENTS.md) — Instructions for AI agents working in this repo
- [docs/](docs/) — Operational guides (Ollama setup, Docker, agent frameworks)

## Status

Phase 1 — the human-driven single-issue loop. An agent takes a task, works in
isolation, self-reviews, and hands back a promotable PR.

See [ROADMAP.md](ROADMAP.md) for the full plan.

## License

TBD
