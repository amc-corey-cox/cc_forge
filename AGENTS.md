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
├── AGENTS.md           # This file (CLAUDE.md symlinks here)
├── DESIGN.md           # Architectural vision
├── ROADMAP.md          # Implementation phases
├── README.md           # Public-facing description
├── src/                # Source code
│   ├── agents/         # Agent implementations
│   └── teams/          # Team-specific logic
├── tests/              # Test suites
├── docker/             # Container definitions
├── docs/               # Operational documentation (setup guides, model registry)
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

## Related Repositories

This project has companion repositories that provide context and reference material:

### cc_ai_knowledge (Reference)

**Repository**: `cc_ai_knowledge`

A curated knowledge base explaining AI/ML concepts. Use this to understand:
- What is quantization? How do transformers work?
- How do different approaches compare? What are the tradeoffs?
- Curated insights from papers, blogs, and community experience

When working in cc_forge, reference this knowledge base to ensure understanding aligns with documented concepts. Every claim in the knowledge base is traceable to primary sources.

### cc_ai_model_ontology (Reference)

**Repository**: `cc_ai_model_ontology`

A LinkML ontology cataloging AI models, capabilities, and deployment constraints. Use this for:
- Structured information about model families and variants
- Capability hierarchies (code generation, reasoning, etc.)
- Hardware tier definitions and deployment constraints
- Cross-references to Ollama, HuggingFace, etc.

When implementing model selection or discussing model capabilities, reference this ontology for consistent terminology and accurate specifications.

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
| `docs/` | Operational documentation, model registry |
| `docker/` | Container configurations (when created) |
| `src/agents/` | Agent implementations (when created) |

### External References

| Repository | Purpose |
|------------|---------|
| `cc_ai_knowledge` | AI concepts and curated understanding |
| `cc_ai_model_ontology` | Structured model catalog (LinkML) |

---

## Updates to This Document

This document should evolve as the project evolves. If you identify:
- Missing guidance
- Contradictions
- Outdated information

...flag it for human review rather than modifying unilaterally.

---

*Last updated: Repository restructure - knowledge base and ontology split to separate repos*
