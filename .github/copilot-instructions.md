# GitHub Copilot Instructions for CC Forge

**Read AGENTS.md in the repository root for complete instructions.**

## Quick Summary

CC Forge is a local-first AI agents development system building an autonomous software development pipeline.

### Critical Rules

1. **No System Info in Code**: Never embed hardware specs, IPs, usernames, or paths
2. **Local-First**: Prefer offline-capable solutions over external API dependencies
3. **Transparency**: All agent work should be logged and auditable
4. **Check AGENTS.md**: For complete coding conventions and project structure

### Key Documentation

| File | Purpose |
|------|---------|
| AGENTS.md | Complete agent instructions |
| DESIGN.md | Architectural vision |
| ROADMAP.md | Implementation phases |

### Code Conventions

- Primary language: Python
- Use type hints for public interfaces
- Follow existing codebase patterns
- Never commit secrets or credentials

### Project Teams

- **Dev Team**: Issue processing and PR creation
- **Test Team**: Test generation and coverage
- **Red Team**: Adversarial code review
- **Blue Team**: Test suite validation

Understand which team's code you're modifying and respect the boundaries between them.
