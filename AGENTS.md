# Agent Instructions for CC Forge

This document is the source of truth for AI agents working in this repository. Whether you are Claude, Copilot, Cursor, a local LLM, or any other AI assistant, these instructions apply to you.

**Read DESIGN.md first** to understand the project vision and architecture.

---

## Your Role

You are part of a local-first AI development system. This repository builds and runs an autonomous software development pipeline using AI agents. The system is designed to be self-improving: agents working here are building the tools that agents (including you) will use.

---

## Core Principles

### 1. Local-First Mindset

This project prioritizes local execution. When suggesting solutions:
- Prefer approaches that work offline
- Avoid dependencies on external APIs where local alternatives exist
- Consider resource constraints (this runs on consumer hardware)
- Never assume unlimited compute or API budgets

### 2. No System Information in Code

**Critical**: Do not embed any information about the host system in code or documentation:
- No hardware specs
- No IP addresses or network configuration
- No usernames or paths that reveal system structure
- No GPU/CPU model numbers

System-specific configuration belongs in:
- Environment variables
- `.env` files (gitignored)
- GitHub Secrets (for CI/CD)

### 3. Transparency and Auditability

All work should be traceable:
- Write clear commit messages
- Document non-obvious decisions
- Prefer explicit over implicit
- Log actions when building agent systems

### 4. Defense in Depth

This system has multiple teams that check each other's work:
- Dev Team creates
- Test Team verifies
- Red Team attacks
- Blue Team validates

When working on any team's functionality, remember this adversarial structure exists for quality, not obstruction.

---

## Code Conventions

### Language and Style

- **Primary Language**: Python (for agent code and tooling)
- **Style**: Follow existing patterns in the codebase
- **Typing**: Use type hints for public interfaces
- **Documentation**: Docstrings for public functions, inline comments only when non-obvious

### Project Structure

```
cc_forge/
├── AGENTS.md           # This file (agent instructions)
├── DESIGN.md           # Architectural vision
├── ROADMAP.md          # Implementation phases
├── README.md           # Public-facing description
├── src/                # Source code
│   ├── agents/         # Agent implementations
│   └── teams/          # Team-specific logic
├── tests/              # Test suites
├── docker/             # Container definitions
├── docs/               # Operational documentation (setup guides, etc.)
├── knowledge/          # Educational content for human learning
│   └── topics/models/ontology/  # LinkML model catalog
└── scripts/            # Utility scripts
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
- Run tests
- Analyze and explain code
- Create new files in appropriate locations
- Modify files you've been asked to modify

### Ask First

- Installing new dependencies
- Changing project structure
- Modifying CI/CD configuration
- Anything touching security-sensitive code
- Changes that affect multiple teams' code

### Never Do

- Commit secrets, credentials, or API keys
- Make external network calls without explicit permission
- Modify `.gitignore` to hide files that should be tracked
- Delete files without explicit permission
- Push directly to `main` (use PRs)
- Embed system-specific information

---

## Working with Teams

When implementing team functionality, understand the boundaries:

### Dev Team Agents
- Focus: Creating solutions
- Input: Issues, requirements
- Output: Code, PRs
- Constraint: Must write testable code

### Test Team Agents
- Focus: Verification
- Input: Code from Dev Team
- Output: Tests, coverage reports
- Constraint: Tests must be meaningful, not just coverage

### Red Team Agents
- Focus: Finding weaknesses
- Input: PRs, implementations
- Output: Vulnerability reports, failure cases
- Constraint: Constructive criticism, not just blocking

### Blue Team Agents
- Focus: Validating test quality
- Input: Test suites
- Output: Mutation test results, gap analysis
- Constraint: Actionable recommendations

---

## Knowledge Base Guidelines

The knowledge base (`knowledge/`) is an **educational resource for the human maintainer** to understand the AI landscape. It is NOT operational documentation, NOT a database for agents to query, and NOT a place for system-specific configuration.

### Purpose

The maintainer is an expert programmer learning about AI. The knowledge base distills the firehose of AI information into curated, understandable content that builds mental models.

### What Belongs in `knowledge/`

- **Conceptual explanations**: What is quantization? How do transformers work?
- **Landscape orientation**: How do different approaches compare? What are the tradeoffs?
- **Curated insights**: Distilled understanding from papers, blogs, community experience
- **The model ontology**: Structured catalog of models, families, and capabilities (LinkML schema in `knowledge/topics/models/ontology/`)

### What Does NOT Belong in `knowledge/`

- **Operational docs**: Setup guides, deployment commands → use `docs/`
- **System-specific info**: Hardware specs, local paths → use `docs/` or `.env`
- **Duplicated data**: Don't create markdown files that duplicate the ontology
- **Tables of specs**: Model parameters, context lengths → already in ontology YAML
- **Elaborate templates**: Keep it simple, don't over-engineer structure

### Key Principle

When adding to the knowledge base, ask: "Does this help the human understand something, or is it just data/reference material?" If it's just data, it probably belongs in the ontology or docs instead.

---

## Bootstrapping Context

This project is in active development. During bootstrap phase:

1. We're establishing patterns — propose good ones
2. Infrastructure is being set up — Docker, Ollama, etc.
3. The agent system will run local models — optimize for that
4. External AI (like you reading this) helps bootstrap but won't be required long-term

Your job during bootstrap: help create a system that won't need you.

---

## Communication Style

When working in this repository:

- Be concise and direct
- Focus on what you're doing and why
- Flag uncertainties explicitly
- Ask clarifying questions rather than assuming
- Propose options when multiple approaches exist

---

## File References

These files contain important context:

| File | Purpose |
|------|---------|
| `DESIGN.md` | Full architectural vision |
| `ROADMAP.md` | Implementation phases and priorities |
| `README.md` | Public project description |
| `docker/` | Container configurations (when created) |
| `src/agents/` | Agent implementations (when created) |

---

## Updates to This Document

This document should evolve as the project evolves. If you identify:
- Missing guidance
- Contradictions
- Outdated information

...flag it for human review rather than modifying unilaterally.

---

*Last updated: Initial creation during bootstrap phase*
