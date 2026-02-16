# Agent Instructions for CC Forge

This document is the source of truth for AI agents working in this repository. Whether you are Claude, Copilot, Cursor, a local LLM, or any other AI assistant, these instructions apply to you.

**Read DESIGN.md first** to understand the project vision and architecture.

---

## Your Role

You are working on CC Forge, a CLI tool (`forge`) that creates safe, containerized AI agent sessions backed by local Ollama models. The safety boundary is Forgejo — agents clone from Forgejo, work in containers, and push changes back. No host filesystem access.

---

## Core Principles

### 1. Local-First Mindset

This project prioritizes local execution. When suggesting solutions:
- Prefer approaches that work offline
- Avoid dependencies on external APIs where local alternatives exist
- Consider resource constraints (this runs on consumer hardware)
- Never assume unlimited compute or API budgets

### 2. No Sensitive System Information

**Intent**: Prevent exposure of information that could enable attacks or identify the system owner.

**Avoid** (security-sensitive):
- IP addresses and network topology
- Absolute paths with usernames
- Specific hardware model numbers
- Credentials, API keys, tokens

**Acceptable** (not security-sensitive):
- Hostnames without network context (e.g., `ssh myserver`)
- Relative paths using `~` (e.g., `~/Code/cc_forge`)
- Generic hardware tiers (e.g., "GPU tier", "CPU tier", "fast/slow")
- Operational documentation showing how to use project infrastructure

**Runtime configuration** (secrets, IPs, etc.) belongs in:
- Environment variables
- `.env` files (gitignored)
- `~/.config/forge/config.env`

### 3. Transparency and Auditability

All work should be traceable:
- Write clear commit messages
- Document non-obvious decisions
- Prefer explicit over implicit
- Log actions when building agent systems

### 4. Defense in Depth

The forge architecture itself enforces this: agents work in isolated containers and can only interact through Forgejo. Future multi-agent teams will add review layers.

---

## Code Conventions

### Language and Style

- **Primary Language**: Python (for CLI and modules)
- **Style**: Follow existing patterns in the codebase
- **Typing**: Use type hints for public interfaces
- **Documentation**: Docstrings for public functions, inline comments only when non-obvious

### Project Structure

```
cc_forge/
├── pyproject.toml              # uv project, forge entry point
├── .python-version             # For mise
├── AGENTS.md                   # This file (CLAUDE.md symlinks here)
├── DESIGN.md                   # Architecture and safety model
├── ROADMAP.md                  # Implementation phases
├── README.md                   # Quick start and usage
├── src/
│   └── cc_forge/               # Python package
│       ├── __init__.py         # Version string
│       ├── cli.py              # Click CLI entry point
│       ├── config.py           # Configuration loading
│       ├── git.py              # Git operations (subprocess)
│       ├── forgejo.py          # Forgejo API client (httpx)
│       ├── docker.py           # Container lifecycle (Docker SDK)
│       └── session.py          # Session orchestration
├── tests/
│   ├── unit/                   # Unit tests (mocked dependencies)
│   └── integration/            # Integration tests (real Docker/Forgejo)
├── docker/
│   ├── docker-compose.yml      # Forgejo + Ollama proxies
│   ├── Dockerfile.agent        # Agent container image
│   ├── entrypoint.sh           # Clone + start agent
│   └── README.md               # Docker stack documentation
├── archive/                    # Historical reference
├── docs/                       # Operational documentation
├── scripts/                    # Utility scripts
└── .github/
    └── copilot-instructions.md
```

### Git Workflow

- Branch from `main` for all work
- Use descriptive branch names: `feature/add-red-team`, `fix/ollama-connection`
- **Commit messages**: One line only, concise and descriptive (no multi-line bodies)
- PRs require description of changes and testing done
- Squash commits when merging (keep history clean)

---

## What You're Allowed To Do

### Always OK

- Read any file in the repository
- Suggest code changes
- Run tests (`pytest`)
- Analyze and explain code
- Create new files in appropriate locations
- Modify files you've been asked to modify

### Ask First

- Installing new dependencies
- Changing project structure
- Modifying CI/CD configuration
- Anything touching security-sensitive code
- Changes that affect the Docker infrastructure

### Never Do

- Commit secrets, credentials, or API keys
- Make external network calls without explicit permission
- Modify `.gitignore` to hide files that should be tracked
- Delete files without explicit permission
- Push directly to `main` (use PRs)
- Embed sensitive system information (see above)

---

## Working with Teams (Future)

The multi-agent team structure is planned for Phase 5+:

- **Dev Team**: Takes issues, creates PRs
- **Test Team**: Generates tests, verifies code
- **Red Team**: Adversarial review of PRs
- **Blue Team**: Mutation testing, test quality validation

All inter-agent coordination will happen through Forgejo issues and PRs.

---

## Related Repositories

| Repository | Purpose |
|------------|---------|
| [cc_ai_knowledge](https://github.com/amc-corey-cox/cc_ai_knowledge) | Curated AI/ML concepts and explanations |
| [cc_ai_model_ontology](https://github.com/amc-corey-cox/cc_ai_model_ontology) | Structured model catalog (LinkML) |

---

## Communication Style

When working in this repository:

- Be concise and direct
- Focus on what you're doing and why
- Flag uncertainties explicitly
- Ask clarifying questions rather than assuming
- Propose options when multiple approaches exist

---

## Updates to This Document

This document should evolve as the project evolves. If you identify missing guidance, contradictions, or outdated information, flag it for human review rather than modifying unilaterally.

---

*Last updated: 2026-02-10 — Updated for forge CLI architecture*
