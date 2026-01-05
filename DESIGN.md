# CC Forge - Design Document

## Project Vision

CC Forge is a local-first AI agents development system designed to create an autonomous software development pipeline. The system runs entirely on local hardware, using local LLMs, with the goal of creating a self-improving development team of AI agents.

### Core Principles

1. **Local-First**: All core operations run on local hardware with local models. External APIs (Claude, OpenAI) may be used for bootstrapping or oversight but are not required for operation.

2. **Self-Bootstrapping**: The system is used to develop itself. Once a minimal foundation exists, the agent teams work on improving and extending the system.

3. **Transparency**: All agent actions, decisions, and reasoning are logged and auditable. No black boxes.

4. **Defense in Depth**: Multiple teams with adversarial roles ensure quality through redundancy and challenge.

5. **Sustainable Learning**: The knowledge base grows organically without overwhelming the human operator.

---

## Team Architecture

The system consists of five specialized agent teams, each with distinct responsibilities and adversarial relationships designed to ensure quality.

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
 │Triage Team  │      │ Dev Team │        │ Knowledge    │
 │(Prioritize) │─────►│          │        │ Base System  │
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

## Knowledge Base System

The knowledge base is **foundational infrastructure**, not a separate product. It serves two audiences with one system:

```
┌─────────────────────────────────────────┐
│           Knowledge Base                │
│  (AI concepts, project context, docs)   │
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
- **Shared investment**: One system, two purposes, compounding value

### Goals

1. **Capture Current State**: Overview of the AI field as it exists
2. **Curated Learning Path**: Curriculum using excellent external sources
3. **Cutting Edge Tracking**: Follow new developments as they happen
4. **Digestible Updates**: Summarize the firehose into actionable insights
5. **Agent Context**: Provide retrieval for agent decision-making

### Components

- **Project Knowledge**: Architecture, conventions, decisions (for agents)
- **AI Concepts**: Key ideas agents and human need to understand
- **Foundational Curriculum**: Structured learning path for AI fundamentals
- **Research Tracker**: Monitor arXiv, major labs, key researchers
- **News Digest**: Regular summaries of significant developments
- **Reading Queue**: Prioritized list of papers/posts worth reading

### Implementation Strategy

Start simple, add complexity when proven valuable:

1. **Phase 1**: Markdown files, organized by topic, grep for search
2. **Phase 2**: Vector embeddings, semantic search, RAG API
3. **Phase 3**: Automated ingestion, summarization, curation

### Anti-Goals

- NOT trying to replace comprehensive resources like Papers With Code
- NOT trying to be an exhaustive database
- NOT fully automated — human curation remains important

---

## Operating Modes

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

### Hybrid Mode

The expected steady-state operation.

- Most routine work handled autonomously
- Significant decisions flagged for human review
- Human can intervene at any point
- Graceful degradation if local resources constrained

---

## Technical Architecture

### Local Infrastructure

```
┌─────────────────────────────────────────────────────┐
│                   Host System                        │
│  ┌─────────────────────────────────────────────┐   │
│  │            Docker Environment                │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────────┐ │   │
│  │  │ Ollama  │  │ Agent   │  │ Knowledge   │ │   │
│  │  │ (LLMs)  │  │ Runtime │  │ Base Store  │ │   │
│  │  └─────────┘  └─────────┘  └─────────────┘ │   │
│  └─────────────────────────────────────────────┘   │
│                                                      │
│  GPU: Intel ARC (via IPEX-LLM or similar)          │
│  Storage: Local persistent volumes                  │
└─────────────────────────────────────────────────────┘
```

### Model Strategy: Tiered Hybrid Approach

Local-first doesn't mean local-only. We use the right tool for the job:

| Tier | Runs On | Speed | Quality | Use Cases |
|------|---------|-------|---------|-----------|
| **Tier 1: GPU** | Intel ARC | Fast | Good | Classification, simple edits, summaries |
| **Tier 2: CPU** | System RAM | Slow | Better | Complex code gen, analysis, reasoning |
| **Tier 3: API** | External | Fast | Best | When local isn't good enough |

**Model Selection Logic**:
- Start with Tier 1 (GPU) for speed
- Escalate to Tier 2 (CPU) for quality-critical tasks
- Escalate to Tier 3 (API) only when necessary

**Constraints**:
- GPU VRAM limits model size (likely 7B-13B class)
- CPU can run larger models (70B) but slowly
- API has cost/privacy implications — use sparingly

**Key Insight**: Most agent tasks don't need the best model. Classification, routing, simple edits can use small fast models. Reserve heavyweight inference for where it matters.

### Data Flow

1. **Issues** → Dev Team → **PRs**
2. **PRs** → Test Team → **Test Coverage**
3. **PRs + Tests** → Red Team → **Review Feedback**
4. **Tests** → Blue Team → **Quality Reports**
5. **External Sources** → Knowledge Base → **Digests**

---

## Security Considerations

### Threat Model

- Agents should not be able to exfiltrate data
- Agents should not be able to make external network calls without explicit permission
- All agent actions are logged and auditable
- Destructive operations require human approval

### Sandboxing

- Agents run in isolated containers
- Network access is whitelist-only
- File system access is scoped to workspace
- Git operations are the primary external interface

### Secrets Management

- No secrets stored in repository
- System-specific configuration via environment variables
- GitHub secrets for CI/CD operations
- Local secrets file (gitignored) for development

---

## Success Metrics

### Development Quality

- PR acceptance rate after Red Team review
- Test coverage percentage
- Mutation testing survival rate (lower is better)
- Time from issue to merged PR

### Knowledge Base Effectiveness

- Time spent by human staying current (should decrease)
- Comprehension of new developments (subjective)
- Actionable insights surfaced

### System Health

- Agent uptime and reliability
- Resource utilization efficiency
- Self-improvement velocity (features added by agents)

---

## Open Questions

These are decisions to be made as the system evolves:

1. **Model Selection**: Which local models work best for each team's tasks?
2. **Agent Framework**: Build custom, or use existing (LangGraph, CrewAI, etc.)?
3. **Knowledge Base Storage**: Vector DB, graph DB, or simpler approach?
4. **Inter-Agent Communication**: Direct calls, message queue, or shared state?
5. **Human Interface**: CLI, web dashboard, or IDE integration?

---

## Appendix: Glossary

- **Agent**: An AI system that can take actions autonomously
- **Bootstrap Mode**: Human-assisted initial development phase
- **Local-First**: Prioritizing local computation over cloud APIs
- **Mutation Testing**: Intentionally breaking code to verify tests catch failures
- **Red Team**: Adversarial review focused on finding weaknesses
- **Blue Team**: Defensive verification focused on test quality
