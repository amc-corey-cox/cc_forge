# CC Forge Roadmap

This document outlines the phased implementation plan for CC Forge.

**Philosophy**: Make it work, make it useful, make it grand. We validate assumptions early, build incrementally, and keep the grand vision as a north star — not a day-one requirement.

---

## Current Focus: Phases 0-3 (MVP)

These phases get us to a working, useful system.

---

## Phase 0: Foundation (Current)

**Goal**: Establish project structure, documentation, and conventions.

### Completed
- [x] Project vision defined
- [x] Team architecture documented (aspirational)
- [x] DESIGN.md created
- [x] AGENTS.md created (agent instructions)
- [x] ROADMAP.md created (this file)
- [x] Agent framework configuration files (CLAUDE.md, .cursorrules, etc.)
- [x] README.md rewritten for public consumption
- [x] Basic project structure created (src/, tests/, docker/, etc.)
- [x] Initial .gitignore configured
- [x] Old issues archived

### Remaining
- [ ] Commit and push foundation
- [ ] Set up SSH access to home server
- [ ] GitHub repository settings (branch protection, etc.) — defer until needed

---

## Phase 1: Hardware Validation

**Goal**: Prove local AI inference works and understand our constraints.

### Intel ARC GPU Testing
- [ ] Research current state of Ollama + Intel ARC support
- [ ] Test IPEX-LLM as alternative if needed
- [ ] Identify which models fit in available VRAM
- [ ] Document working configuration

### Model Benchmarking
- [ ] Test small models on GPU (7B, 13B class)
- [ ] Benchmark inference speed (tokens/sec)
- [ ] Evaluate quality for target tasks (code, summaries, classification)
- [ ] Compare GPU vs CPU performance for same models

### Hybrid Strategy Validation
- [ ] Confirm large model (70B) works on CPU (already done, document it)
- [ ] Test model switching between GPU and CPU
- [ ] Establish when to use which tier:
  - GPU (fast, small): Quick tasks, classification, simple edits
  - CPU (slow, large): Complex code generation, analysis
  - API (external): When local isn't good enough

### Deliverables
- [ ] `docs/hardware-setup.md` — What works, what doesn't
- [ ] `docs/model-selection.md` — Which models for which tasks
- [ ] Working Ollama setup on home server

---

## Phase 2: Knowledge Base Foundation

**Goal**: Create shared context infrastructure for both human learning and agent RAG.

### Why Early?
The knowledge base isn't a separate product — it's **foundational infrastructure**:
- Agents need context to work effectively (RAG)
- Human needs to stay current with AI field
- One system serves both purposes

### Simple Start (Markdown)
- [ ] Create `knowledge/` directory structure
- [ ] Define topic taxonomy (AI concepts, project docs, external resources)
- [ ] Seed with initial content:
  - Project architecture and conventions
  - Key AI concepts agents need to understand
  - Links to foundational learning resources
- [ ] Create simple search/browse tooling

### Semantic Search (When Needed)
- [ ] Evaluate vector DB options (ChromaDB, Qdrant, simple FAISS)
- [ ] Implement embeddings pipeline
- [ ] Create retrieval API for agents
- [ ] Build simple query interface for human

### Content Pipeline (Gradual)
- [ ] RSS/Atom feed monitoring for AI news
- [ ] ArXiv paper tracking (AI/ML categories)
- [ ] Summarization for new content
- [ ] Relevance scoring and filtering

### Deliverables
- [ ] Working knowledge base with initial content
- [ ] Retrieval mechanism agents can use
- [ ] Human-browsable interface (even if just markdown + grep)

---

## Phase 3: Single Agent MVP

**Goal**: One agent doing one useful thing end-to-end.

### The "Dev Assistant" Agent
Not a full Dev Team — just one agent that can:
- Read a GitHub issue
- Understand the codebase (using knowledge base)
- Propose a solution
- Create a PR

### Core Capabilities
- [ ] GitHub issue reading and parsing
- [ ] Codebase indexing/understanding
- [ ] Knowledge base querying for context
- [ ] Code generation (using appropriate model tier)
- [ ] Git operations (branch, commit, push)
- [ ] PR creation via GitHub API

### Agent Infrastructure
- [ ] Basic agent loop (receive task → think → act → report)
- [ ] Model selection logic (which tier for which task)
- [ ] Logging and audit trail
- [ ] Error handling and recovery

### Human Oversight
- [ ] Clear reporting of what agent is doing
- [ ] Approval gates for destructive actions
- [ ] Easy way to intervene or cancel

### Deliverables
- [ ] Working agent that can handle simple issues
- [ ] Documentation of what it can/can't do
- [ ] Baseline for iteration

---

## Success Criteria for MVP

Before moving to team architecture, the MVP should demonstrate:

1. **Hardware works**: Local inference runs reliably
2. **Knowledge base works**: Agents can retrieve relevant context
3. **Agent works**: At least one successful issue → PR cycle
4. **Hybrid works**: Appropriate model selection for task complexity

---

# Future Vision: Team Architecture

These phases represent the full vision. They're **aspirational** — we build toward them as the MVP matures, not all at once.

---

## Phase 4: Agent Framework Formalization

**Goal**: Generalize the MVP agent into a reusable framework.

### Agent Runtime
- [ ] Define agent interface/protocol
- [ ] Implement base agent class
- [ ] Create agent lifecycle management (start, stop, health check)
- [ ] Build configuration system for agent parameters

### Communication
- [ ] Define inter-agent message format
- [ ] Implement message passing mechanism
- [ ] Create shared state management (if needed)
- [ ] Extend logging and audit trail

### Integration
- [ ] Formalize Ollama integration
- [ ] Implement retry and fallback logic
- [ ] Create agent testing harness
- [ ] Document agent development patterns

---

## Phase 5: Triage Team

**Goal**: Automate issue management and prioritization.

### Issue Management
- [ ] Read and parse ROADMAP.md phases
- [ ] Generate GitHub issues from roadmap items
- [ ] Apply labels and priorities
- [ ] Set dependencies between issues

### Backlog Maintenance
- [ ] Monitor issue queue health
- [ ] Re-prioritize based on team feedback
- [ ] Close stale or duplicate issues
- [ ] Ensure issues have clear acceptance criteria

---

## Phase 6: Dev Team

**Goal**: Graduate the MVP agent into a full Dev Team.

### Enhanced Capabilities
- [ ] Multiple concurrent issue handling
- [ ] More sophisticated code understanding
- [ ] Self-review before submission
- [ ] Learning from PR feedback

---

## Phase 7: Test Team

**Goal**: Automated test generation and coverage analysis.

### Test Generation
- [ ] Identify untested code
- [ ] Generate unit tests
- [ ] Generate integration tests
- [ ] Validate test quality (not just coverage)

### Coverage Analysis
- [ ] Integrate coverage tooling
- [ ] Generate coverage reports
- [ ] Identify coverage gaps
- [ ] Track coverage trends

---

## Phase 8: Red Team

**Goal**: Adversarial review of PRs and implementations.

### Code Review
- [ ] Automated PR review trigger
- [ ] Logic error detection
- [ ] Edge case identification
- [ ] Security vulnerability scanning
- [ ] Create GitHub issues for problems found

### Attack Simulation
- [ ] Generate failure scenarios
- [ ] Test boundary conditions
- [ ] Attempt to break new features

---

## Phase 9: Blue Team

**Goal**: Test suite validation through mutation testing.

### Mutation Testing
- [ ] Integrate mutation testing framework
- [ ] Run mutation testing on PRs
- [ ] Report survival rates
- [ ] Create GitHub issues for test gaps

### Quality Metrics
- [ ] Define test quality thresholds
- [ ] Generate quality reports
- [ ] Track improvement over time

---

## Phase 10: Knowledge Base Enhancement

**Goal**: Full-featured knowledge system with curation.

### Curriculum
- [ ] Define learning paths
- [ ] Curate foundational resources
- [ ] Create progression structure

### Digests
- [ ] Daily/weekly summary generation
- [ ] Priority ranking of new content
- [ ] Filter noise from signal

### Interface
- [ ] Reading queue management
- [ ] Progress tracking
- [ ] Search and discovery

---

## Phase 11: Integration and Polish

**Goal**: Connect all systems and refine the experience.

### Orchestration
- [ ] Unified control plane for all teams
- [ ] Dashboard for system status
- [ ] Alert system for issues
- [ ] Resource management

### Self-Improvement
- [ ] Agents can file issues on themselves
- [ ] Automated performance monitoring
- [ ] Documentation auto-updates

### Human Interface
- [ ] CLI for common operations
- [ ] Web dashboard (optional)
- [ ] Notification system

---

## Far Future Considerations

Ideas for post-v1 development:

- **Model Fine-tuning**: Fine-tune local models on project-specific patterns
- **Multi-Project Support**: Run agents across multiple repositories
- **Collaboration Features**: Multiple humans working with the agent teams
- **External Integrations**: Slack, Discord, email notifications
- **Metrics Dashboard**: Historical trends and analytics

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-01-02 | Local-first architecture | Privacy, cost, learning opportunity |
| 2025-01-02 | Five-team structure (aspirational) | Defense in depth, quality assurance |
| 2025-01-02 | Docker-based infrastructure | Portability, isolation, reproducibility |
| 2025-01-02 | Pragmatic MVP-first approach | Validate assumptions before building grand vision |
| 2025-01-02 | Hybrid model strategy | GPU for fast/small, CPU for slow/large, API for complex |
| 2025-01-02 | Knowledge base as infrastructure | Serves both human learning and agent RAG |

---

## Notes

- **Phases 0-3 are the focus** — everything else is future vision
- Validate assumptions early; don't build on unproven foundations
- The goal is working software, not perfect plans
- Teams are added incrementally as the MVP proves itself
- Off-ramps exist: if local-only doesn't work well enough, we adapt

---

*Last updated: 2025-01-02 — Restructured for pragmatic MVP-first approach*
