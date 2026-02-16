# CC Forge Roadmap

## Phase 1: Foundation (current)

**Goal**: `forge` CLI works end-to-end for interactive sessions.

- [x] Python package with `forge` entry point (Click CLI)
- [x] Git module for repo detection and remote management
- [x] Forgejo API client (httpx)
- [x] Docker module for container lifecycle (Docker SDK)
- [x] Docker compose stack: Forgejo + Ollama proxies
- [x] Agent container with Claude Code + Aider
- [x] Entrypoint: clone from Forgejo, start agent
- [x] Session orchestration: `forge` wires it all together
- [x] Unit tests for git and Forgejo modules
- [ ] End-to-end testing on real repos
- [ ] First-time Forgejo setup documentation

## Phase 2: Polish & Robustness

**Goal**: Reliable for daily use.

- [ ] `forge setup` — automated Forgejo first-time config (create admin, get token)
- [ ] Error handling and recovery (container cleanup on crash)
- [ ] Multiple concurrent sessions
- [ ] `forge status` / `forge stop` — full implementation
- [ ] Container cleanup (stale containers, dangling images)
- [ ] Integration tests
- [ ] Configuration validation and helpful error messages

## Phase 3: Remote Access

**Goal**: Use forge from any device on your network.

- [ ] Server install script (clone + install = ready)
- [ ] Client install for laptops
- [ ] Tailscale-based secure access
- [ ] `forge` works the same from laptop using server resources

## Phase 4: Autonomous Mode

**Goal**: Agents work unattended on issues.

- [ ] `forge auto <issue>` — agent works on a Forgejo issue, creates PR when done
- [ ] Forgejo Actions (CI/CD in forge)
- [ ] Background job management
- [ ] Notification on completion

## Phase 5+: Multi-Agent Teams

**Goal**: Specialized agent teams with adversarial quality checks.

- [ ] Dev Team: takes issues, creates PRs
- [ ] Test Team: generates and runs tests
- [ ] Red Team: adversarial review of PRs
- [ ] Blue Team: mutation testing, test quality validation
- [ ] Inter-agent coordination via Forgejo issues and PRs

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-01-02 | Local-first architecture | Privacy, cost, learning opportunity |
| 2026-01-29 | Aider over Goose for local models | Goose tool-calling fails with local models |
| 2026-02-02 | Claude Code + Ollama works with shim | Ollama Anthropic API + shim for GPU |
| 2026-02-02 | Dual-service Ollama architecture | CPU (11434) + Vulkan GPU (11435) |
| 2026-02-10 | Forge CLI with Forgejo review gate | Safety boundary: no host mount, all work via Forgejo |
| 2026-02-10 | Click + httpx + Docker SDK | Lightweight, modern, reliable |

---

*Last updated: 2026-02-10 — Restructured for forge CLI*
