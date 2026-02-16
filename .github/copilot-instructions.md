# GitHub Copilot Instructions for CC Forge

**Read AGENTS.md in the repository root for complete instructions.**

## Quick Summary

CC Forge is a CLI tool (`forge`) for safe, containerized AI agent sessions backed by local Ollama models. Changes go through a local Forgejo instance as a review gate.

### Critical Rules

1. **No System Info in Code**: Never embed hardware specs, IPs, usernames, or paths
2. **Local-First**: Prefer offline-capable solutions over external API dependencies
3. **Transparency**: All agent work should be logged and auditable
4. **Check AGENTS.md**: For complete coding conventions and project structure

### Key Documentation

| File | Purpose |
|------|---------|
| AGENTS.md | Complete agent instructions |
| DESIGN.md | Architecture and safety model |
| ROADMAP.md | Implementation phases |

### Code Conventions

- Primary language: Python
- CLI framework: Click
- HTTP client: httpx
- Container management: Docker SDK
- Use type hints for public interfaces
- Follow existing codebase patterns
- Never commit secrets or credentials
