# CC Forge - Design Document

## Project Vision

CC Forge is a CLI tool that gives you a safe, containerized AI agent session for any git repository. Type `forge` in a repo and get an interactive Claude Code session backed by local Ollama, with all changes going through a local Forgejo instance as a review gate.

The agent can never touch your real repos or host filesystem.

### Core Principles

1. **Local-First**: All execution on local hardware with local models. No cloud dependencies.
2. **Safe by Default**: Agents clone from Forgejo, not bind-mounted. This is the safety boundary.
3. **Simple to Use**: One command (`forge`) does everything — starts infrastructure, syncs to Forgejo, launches agent.
4. **Transparent**: All agent work lands in Forgejo as commits/PRs. Review before pulling to your real repo.

---

## Architecture

```
User types `forge` in a git repo
       │
       ▼
  forge CLI (Python, installed via uv)
       │
       ├─ Auto-starts Forgejo + Ollama proxies if not running (docker compose)
       ├─ Detects git repo, extracts name and current branch
       ├─ Checks Forgejo API: does this repo exist?
       │    └─ If not: creates repo on Forgejo, adds `forgejo` remote, pushes
       ├─ Launches agent container on forge-network
       │    └─ Container clones from Forgejo (NOT host mount)
       │    └─ Has Claude Code + Aider installed
       │    └─ Can reach: Forgejo (port 3000), Ollama (ports 11434/11435)
       │    └─ Cannot reach: host filesystem
       └─ Attaches terminal → interactive Claude Code session
              │
              ▼
         Agent works, commits, pushes to Forgejo
              │
              ▼
         User reviews in Forgejo web UI (localhost:3000)
              │
              ▼
         Approved work pulled to real repo / pushed to GitHub
```

### Safety Model

The key security boundary is **no host mount**. The agent container:

- Clones from Forgejo, not your filesystem
- Runs on a dedicated Docker network (`forge-network`)
- Reaches Forgejo and Ollama via network proxies
- Has no access to host filesystem or host mounts
- All output is visible as git commits in Forgejo

### Network Access: Intent vs. Current State

Agents legitimately need some internet access — reading documentation, searching Stack Overflow,
checking language references. But they should not be making external API calls (cloud AI services,
webhooks, etc.) or exfiltrating repository contents.

**What we want to allow:**
- HTTP/HTTPS reads to documentation and reference sites
- DNS resolution

**What we want to prevent:**
- Calls to external AI APIs (OpenAI, Anthropic cloud, etc.)
- Pushing code to external git hosts (GitHub, GitLab)
- Arbitrary outbound connections (reverse shells, data exfiltration)

**Current state (Phase 1):** The bridge network has no egress restrictions. Agents can reach
anything. The primary safety boundary is the Forgejo review gate — all code changes are visible
as commits before they reach your real repo.

**Possible enforcement approaches (Phase 2+):**

| Approach | Pros | Cons |
|----------|------|------|
| Egress proxy (Squid/mitmproxy) with allowlist | Fine-grained URL control | Complex setup, TLS inspection is invasive |
| DNS-based filtering | Simple, blocks by domain | Easy to bypass, no path-level control |
| iptables/nftables rules | No extra services | Hard to maintain, protocol-unaware |
| `internal: true` network + explicit proxy | Strong isolation | Breaks legitimate web access entirely |
| Audit logging (no blocking) | Zero friction | Doesn't prevent, only detects |

The right answer likely involves a combination: audit logging first (know what agents are doing),
then a lightweight proxy if patterns emerge that need blocking. Premature lockdown risks making
agents useless for real work.

---

## Infrastructure

### Docker Services

| Service | Purpose | Port |
|---------|---------|------|
| `forge-forgejo` | Local git hosting + review UI | 3000 |
| `forge-ollama-proxy` | Forwards to host Ollama CPU | 11434 (internal) |
| `forge-ollama-gpu-proxy` | Forwards to host Ollama GPU | 11435 (internal) |

### Agent Container

Built from `docker/Dockerfile.agent`:
- Ubuntu 24.04 base
- Claude Code + Aider pre-installed
- Entrypoint clones from Forgejo, starts agent
- Runs as non-root `agent` user
- Joins `forge-network`

---

## Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| CLI framework | Click | Lightweight, explicit, well-tested |
| HTTP client | httpx | Modern async-capable Python HTTP client |
| Container management | Docker SDK (python-docker) | Better lifecycle control than subprocess |
| Git operations | subprocess | Simpler than GitPython for limited operations |
| Local git hosting | Forgejo | Open-source, lightweight, good API |
| AI agents | Claude Code + Aider | Both tested and working with local Ollama |

---

## Review Workflow

1. `forge` pushes your current branch to Forgejo
2. Agent works in a container, commits and pushes to Forgejo
3. You review changes in the Forgejo web UI (localhost:3000)
4. Approved changes: `git pull forgejo <branch>` to your real repo
5. Push to GitHub/upstream as usual

---

## External Knowledge Resources

| Repository | Purpose |
|------------|---------|
| [cc_ai_knowledge](https://github.com/amc-corey-cox/cc_ai_knowledge) | Curated AI/ML concepts and explanations |
| [cc_ai_model_ontology](https://github.com/amc-corey-cox/cc_ai_model_ontology) | Structured catalog of models and capabilities |

---

*Last updated: 2026-02-10 — Restructured for forge CLI architecture*
