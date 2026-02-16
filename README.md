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

### Usage

```bash
# In any git repo:
forge

# Use Aider instead of Claude Code:
forge run --agent aider

# Check running sessions:
forge status

# Stop all sessions:
forge stop --all
```

### Review Workflow

1. `forge` syncs your repo to local Forgejo and launches an agent container
2. The agent works, commits, and pushes to Forgejo
3. Review changes in Forgejo web UI (`http://localhost:3000`)
4. Pull approved work: `git pull forgejo <branch>`
5. Push to GitHub as usual

## Documentation

- [DESIGN.md](DESIGN.md) — Architecture and safety model
- [ROADMAP.md](ROADMAP.md) — Implementation phases
- [AGENTS.md](AGENTS.md) — Instructions for AI agents working in this repo
- [docs/](docs/) — Operational guides (Ollama setup, Docker, agent frameworks)

## Status

Phase 1: Foundation — `forge` CLI with end-to-end session flow.

See [ROADMAP.md](ROADMAP.md) for the full plan.

## License

TBD
