# CC Forge - Design Document

## Project Vision

CC Forge is a local-first AI coding assistant built on Ollama and open-source agent tools (Goose, Aider, etc.). The goal is to create a local alternative to cloud-based AI coding assistants like Claude Code, capable of autonomous software development tasks.

### Core Principles

1. **Local-First**: All core operations run on local hardware with local models. External APIs may be used for bootstrapping or fallback but are not required for operation.

2. **Tool Agnostic**: We integrate with existing tools (Goose, Aider, Continue) rather than building everything from scratch. The value is in configuration, orchestration, and local optimization.

3. **Transparency**: All agent actions, decisions, and reasoning are logged and auditable. No black boxes.

4. **Pragmatic**: Start with what works today. Iterate toward the grand vision.

---

## MVP: Local Coding Assistant

The immediate goal is a working local coding assistant that can handle common development tasks without cloud dependencies.

### Target Capabilities

- **Code Generation**: Write new code from descriptions
- **Code Modification**: Edit existing files based on instructions
- **Code Review**: Analyze code and suggest improvements
- **Debugging**: Help identify and fix bugs
- **Documentation**: Generate docs and comments
- **Git Operations**: Commit, branch, create PRs

### Technology Stack

```
┌─────────────────────────────────────────────────────┐
│                   User Interface                     │
│           (CLI / IDE Integration / Web)              │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              Agent Framework Layer                   │
│         (Goose / Aider / Custom Orchestration)       │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                 Ollama (LLM Server)                  │
│     ┌─────────────┬─────────────┬─────────────┐     │
│     │  Tier 1     │  Tier 2     │  Tier 3     │     │
│     │  GPU Fast   │  CPU Large  │  API Fallback│    │
│     │  (7-13B)    │  (70B)      │  (External)  │    │
│     └─────────────┴─────────────┴─────────────┘     │
└─────────────────────────────────────────────────────┘
```

### Agent Framework Evaluation

We'll evaluate existing tools before building custom:

| Tool | Strengths | Considerations |
|------|-----------|----------------|
| **Goose** | Block/Square backed, extensible, MCP support | Newer, evolving |
| **Aider** | Mature, git-aware, proven | Python-focused |
| **Continue** | IDE integration, multiple models | IDE-dependent |
| **Custom** | Full control | More work |

**Initial approach**: Start with Goose or Aider, extend as needed.

---

## Model Strategy: Tiered Hybrid Approach

Local-first doesn't mean local-only. We use the right tool for the job:

| Tier | Runs On | Speed | Quality | Use Cases |
|------|---------|-------|---------|-----------|
| **Tier 1: GPU** | Intel ARC / NVIDIA | Fast | Good | Quick edits, classification, simple tasks |
| **Tier 2: CPU** | System RAM (64GB+) | Slow | Better | Complex code gen, analysis, reasoning |
| **Tier 3: API** | External | Fast | Best | When local isn't good enough |

### Model Selection Logic

- Start with Tier 1 (GPU) for speed
- Escalate to Tier 2 (CPU) for quality-critical tasks
- Escalate to Tier 3 (API) only when necessary and explicitly permitted

### Constraints

- GPU VRAM limits model size (7B-13B class typical)
- CPU can run larger models (70B) but slowly
- API has cost/privacy implications — use sparingly

**Key Insight**: Most tasks don't need the best model. Classification, routing, simple edits can use small fast models. Reserve heavyweight inference for complex reasoning.

---

## Local Infrastructure

```
┌─────────────────────────────────────────────────────┐
│                   Host System                        │
│  ┌─────────────────────────────────────────────┐   │
│  │            Docker Environment                │   │
│  │  ┌─────────────┐  ┌─────────────────────┐   │   │
│  │  │   Ollama    │  │   Agent Runtime     │   │   │
│  │  │   (LLMs)    │  │   (Goose/Aider)     │   │   │
│  │  └─────────────┘  └─────────────────────┘   │   │
│  └─────────────────────────────────────────────┘   │
│                                                      │
│  GPU: Intel ARC / NVIDIA (via appropriate runtime)  │
│  Storage: Local persistent volumes                  │
└─────────────────────────────────────────────────────┘
```

---

## External Knowledge Resources

Understanding AI concepts and model capabilities is maintained in separate repositories:

| Repository | Purpose |
|------------|---------|
| **cc_ai_knowledge** | Curated AI/ML concepts, explanations, learning resources |
| **cc_ai_model_ontology** | Structured catalog of models, capabilities, deployment constraints |

These provide context for decision-making but are not runtime dependencies.

---

## Security Considerations

### Threat Model

- Agents should not exfiltrate data
- Agents should not make external network calls without explicit permission
- All agent actions are logged and auditable
- Destructive operations require human approval (configurable)

### Sandboxing

- Agents run in isolated containers (when using Docker)
- Network access is whitelist-only
- File system access is scoped to workspace
- Git operations are the primary external interface

### Secrets Management

- No secrets stored in repository
- System-specific configuration via environment variables
- Local secrets file (gitignored) for development

---

## Success Metrics (MVP)

1. **Works offline**: Core functionality without internet
2. **Useful daily**: Handles common coding tasks reliably
3. **Fast enough**: Tier 1 tasks complete in seconds, not minutes
4. **Quality sufficient**: Output quality acceptable for real work
5. **Easy to use**: Setup and operation are straightforward

---

# Future Vision: Multi-Agent Team Architecture

The following describes the long-term vision for CC Forge. This is **aspirational** — we build toward it as the MVP matures. The system is designed to be self-improving: agents working here build the tools that agents (including themselves) will use.

---

## Team Architecture

The full system envisions five specialized agent teams with adversarial relationships designed to ensure quality through defense in depth.

```
                    ┌─────────────────┐
                    │   Human Owner   │
                    │   (Oversight)   │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
 ┌─────────────┐      ┌──────────┐        ┌──────────────┐
 │Triage Team  │      │ Dev Team │        │  External    │
 │(Prioritize) │─────►│          │        │  Knowledge   │
 └─────────────┘      └────┬─────┘        └──────────────┘
        ▲                  │
        │                  ▼
        │            ┌──────────┐
        │            │Test Team │
        │            └────┬─────┘
        │                 │
   ┌────┴────┐            ▼
   │ Issues  │      ┌──────────┐   ┌──────────┐
   │ Created │◄─────│ Red Team │   │ Blue Team│
   └─────────┘      │ (Attack) │   │ (Verify) │
        ▲           └──────────┘   └────┬─────┘
        │                               │
        └───────────────────────────────┘
```

### Dev Team

**Purpose**: Take issues and create PRs to fix bugs or add new functionality.

**Responsibilities**:
- Monitor issue queue for actionable work items
- Analyze requirements and design solutions
- Implement changes following project conventions
- Create well-formed PRs with clear descriptions
- Respond to feedback from other teams

**Inputs**: GitHub issues, feedback from Red Team
**Outputs**: Pull requests, implementation notes

### Test Team

**Purpose**: Create comprehensive tests ensuring all code is tested and logic is verified.

**Responsibilities**:
- Write unit tests for new and existing code
- Create integration tests for system interactions
- Ensure test coverage meets thresholds
- Verify that tests actually test meaningful behavior (not just coverage gaming)
- Document testing strategy and gaps

**Inputs**: Codebase, PRs from Dev Team
**Outputs**: Test suites, coverage reports, testing documentation

### Red Team

**Purpose**: Adversarial review of PRs and tests to find weaknesses.

**Responsibilities**:
- Review PRs for logic errors, edge cases, and poor design
- Attempt to break new functionality
- Identify security vulnerabilities
- Challenge assumptions in implementations
- Find cases where tests pass but behavior is wrong
- Propose concrete failure scenarios
- **Create GitHub issues** for problems found that require Dev Team action

**Inputs**: PRs from Dev Team, test suites from Test Team
**Outputs**: Review comments, failure cases, blocking concerns, **new issues**

### Blue Team

**Purpose**: Verify test suite comprehensiveness through intentional breakage.

**Responsibilities**:
- Mutation testing: intentionally break code, verify tests catch it
- Identify untested code paths
- Verify error handling works correctly
- Ensure test suite catches real failure modes
- Report on test suite health and gaps
- **Create GitHub issues** for test coverage gaps that require Test Team action

**Inputs**: Test suites, codebase
**Outputs**: Mutation test results, gap analysis, improvement recommendations, **new issues**

### Triage Team

**Purpose**: Convert roadmap items and feature requests into actionable issues, prioritize work.

**Responsibilities**:
- Break down ROADMAP.md phases into specific, actionable GitHub issues
- Prioritize issue backlog based on dependencies and importance
- Ensure issues have clear acceptance criteria
- Re-prioritize based on Red/Blue team findings
- Archive or close stale issues
- Maintain issue labels and organization

**Inputs**: ROADMAP.md, feature requests, team feedback
**Outputs**: Well-formed GitHub issues, prioritized backlog

**Note**: This team bridges human intent (roadmap, ideas) with agent execution (issues). It ensures the Dev Team always has clear, actionable work.

---

## Knowledge Base Integration (Future)

While the knowledge base now lives in separate repositories (cc_ai_knowledge, cc_ai_model_ontology), it remains **foundational infrastructure** for the multi-agent system:

```
┌─────────────────────────────────────────┐
│     External Knowledge Repositories     │
│  (AI concepts, model catalog, docs)     │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴───────┐
       │               │
       ▼               ▼
   ┌───────┐       ┌───────┐
   │ Human │       │Agents │
   │(learn)│       │ (RAG) │
   └───────┘       └───────┘
```

### Why It's Foundational

- **Agents need context**: RAG (retrieval-augmented generation) makes small models punch above their weight
- **Human needs learning**: Stay current with AI without drowning in the firehose
- **Shared investment**: Separate repos, shared value, compounding returns

### Future RAG Integration

- Agents query cc_ai_knowledge for concept understanding
- Agents query cc_ai_model_ontology for model selection decisions
- Project-specific knowledge stays local in cc_forge

---

## Data Flow (Future Multi-Agent)

1. **ROADMAP** → Triage Team → **Issues**
2. **Issues** → Dev Team → **PRs**
3. **PRs** → Test Team → **Test Coverage**
4. **PRs + Tests** → Red Team → **Review Feedback / New Issues**
5. **Tests** → Blue Team → **Quality Reports / New Issues**
6. **External Knowledge** → All Teams → **Context for Decisions**

---

## Operating Modes (Future)

### Bootstrap Mode

Used during initial development and when making significant changes to the agent system itself.

- Human-in-the-loop for most decisions
- External AI (Claude Code, etc.) may assist
- Focus on establishing patterns and conventions
- Agents run with training wheels / extra validation

### Production Mode

Used once the system is stable and self-maintaining.

- Agents operate autonomously within defined bounds
- Human oversight through dashboards and alerts
- Automated PR creation and review cycles
- Knowledge base updates flow automatically

### Hybrid Mode (Expected Steady State)

The expected long-term operation mode.

- Most routine work handled autonomously
- Significant decisions flagged for human review
- Human can intervene at any point
- Graceful degradation if local resources constrained

---

## Open Questions

1. **Agent Framework**: Goose, Aider, or custom?
2. **Model Selection**: Which models work best for each task type?
3. **Context Management**: How to give agents enough context without overwhelming them?
4. **Inter-Agent Communication**: How do teams coordinate in the future vision?
5. **Human Interface**: CLI primary, with web dashboard later?

---

## Appendix: Glossary

- **Agent**: An AI system that can take actions autonomously
- **Goose**: Open-source AI agent framework from Block
- **Aider**: AI pair programming tool
- **Local-First**: Prioritizing local computation over cloud APIs
- **Mutation Testing**: Intentionally breaking code to verify tests catch failures
- **Ollama**: Local LLM server
- **RAG**: Retrieval-Augmented Generation
- **Red Team**: Adversarial review focused on finding weaknesses
- **Blue Team**: Defensive verification focused on test quality
- **Tier**: Hardware/model category in our hybrid strategy

---

*Last updated: 2025-01-27 — Restructured for local coding assistant MVP*
