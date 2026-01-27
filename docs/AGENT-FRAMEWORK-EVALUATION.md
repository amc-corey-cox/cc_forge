# Agent Framework Evaluation

Evaluation of AI coding assistant frameworks for cc_forge's local-first MVP.

---

## Executive Summary

**Recommendation: Goose** as the primary framework for cc_forge.

Goose's MCP (Model Context Protocol) architecture aligns with cc_forge's vision of extensible, self-improving agent systems. The framework allows building custom tools that agents can discover dynamically—essential for the planned multi-team architecture.

**Secondary Option: Aider** for git-focused workflows where MCP extensibility isn't needed.

---

## Evaluation Criteria

Based on cc_forge's requirements (see DESIGN.md):

| Criterion | Weight | Why It Matters |
|-----------|--------|----------------|
| **Ollama Support** | High | Local-first requires native local model integration |
| **Extensibility** | High | Multi-team system needs custom tool creation |
| **Terminal-First** | Medium | Primary interface is CLI |
| **Git Integration** | Medium | Code changes should integrate with version control |
| **Maturity** | Medium | Stable enough for daily use |
| **Active Development** | Low | Nice to have, not critical |

---

## Framework Profiles

### Goose (block/goose)

**Overview**: Open-source AI agent from Block with native MCP support and Ollama integration.

**Ollama Support**: Excellent
- Native integration with official documentation
- Multi-model configuration for cost/performance optimization
- CLI and desktop versions available

**Key Strengths**:
- **MCP Architecture**: Core feature enabling custom tool creation via MCP servers
- **Full Autonomy**: Can build projects, execute code, debug, orchestrate workflows
- **Active Development**: 29k+ GitHub stars, 100+ releases, regular updates
- **Rust Core**: Performance-focused architecture (59% Rust, 33% TypeScript)

**Limitations**:
- Git integration less mature than Aider
- CLI configuration requires manual `goose configure` setup
- Desktop app separate from CLI installation

**cc_forge Fit**: Excellent. MCP enables the planned Dev/Test/Red/Blue team tools to be exposed as discoverable services that Goose instances can use.

**Links**: [GitHub](https://github.com/block/goose) | [Ollama Docs](https://docs.ollama.com/integrations/goose)

---

### Aider (paul-gauthier/aider)

**Overview**: AI pair programming tool with best-in-class git integration.

**Ollama Support**: Excellent
- Full support with dedicated documentation
- Automatic context window management
- Recommends qwen2.5-coder or deepseek-coder models

**Key Strengths**:
- **Git Integration**: Every change auto-commits with descriptive messages; easy undo
- **Terminal-First**: Designed for efficient command-line workflows
- **Privacy-First**: Open-source, no external API calls required
- **Mature**: Stable, well-documented, strong community

**Limitations**:
- No MCP support—limited extensibility
- Less suitable for building custom tool ecosystems
- Model capability varies significantly (check Aider's leaderboard)

**cc_forge Fit**: Good for straightforward coding tasks, but lacks extensibility for the multi-agent vision.

**Links**: [GitHub](https://github.com/paul-gauthier/aider) | [Ollama Docs](https://aider.chat/docs/llms/ollama.html)

---

### Continue.dev

**Overview**: Open-source AI code assistant with deep IDE integration.

**Ollama Support**: Good
- Local-first capable, fully air-gapped operation
- Configurable prompts, tools, and workflows

**Key Strengths**:
- **IDE Integration**: Native VS Code experience similar to Cursor/Windsurf
- **Configurable**: Extensive customization options
- **Local-First**: Can run completely offline

**Limitations**:
- IDE-dependent (not terminal-first)
- Limited MCP support compared to Goose
- Different paradigm than CLI-focused workflows

**cc_forge Fit**: Consider later for IDE integration (Phase 6) but not primary framework.

**Links**: [Website](https://continue.dev) | [GitHub](https://github.com/continuedev/continue)

---

### Cline (VS Code Extension)

**Overview**: VS Code extension with deep agentic capabilities and MCP support.

**Ollama Support**: Good
- Works with Ollama and LM Studio
- Model-agnostic architecture

**Key Strengths**:
- **MCP Support**: Native integration, can extend via MCP servers
- **Plan Mode**: Can design before executing
- **Permissioned Operations**: Controlled terminal/file access
- **Full Autonomy**: Deep agentic workflows

**Limitations**:
- VS Code dependent
- Free extension but pay-as-you-go for cloud models (or use local)
- Different interaction model than terminal CLI

**cc_forge Fit**: Strong alternative if VS Code becomes primary interface. Good MCP support.

**Links**: [Website](https://cline.bot) | [GitHub](https://github.com/clinebot/cline)

---

## Comparison Matrix

| Feature | Goose | Aider | Continue | Cline |
|---------|-------|-------|----------|-------|
| **Ollama Support** | Excellent | Excellent | Good | Good |
| **MCP/Extensibility** | Excellent | None | Limited | Good |
| **Git Integration** | Basic | Excellent | Good | Good |
| **Terminal-First** | Yes | Yes | No | No |
| **Local-First** | Yes | Yes | Yes | Yes |
| **Agent Autonomy** | Full | Full | Full | Full |
| **Maturity** | High | High | High | High |
| **GitHub Stars** | 29k+ | 25k+ | 20k+ | 15k+ |

---

## Recommendation

### Primary: Goose

Goose is the best fit for cc_forge because:

1. **Extensibility via MCP**: The planned multi-team system (Dev, Test, Red, Blue) can expose capabilities as MCP servers. Goose instances discover and use these tools dynamically.

2. **Architecture Alignment**: cc_forge aims to be self-improving—agents build tools for agents. MCP enables this pattern without modifying the core framework.

3. **Local-First Design**: Native Ollama support, no cloud dependencies required.

4. **Terminal-First**: Matches the CLI-focused workflow.

5. **Active Development**: Regular releases, responsive maintainers, growing ecosystem.

### Secondary: Aider

Use Aider when:
- Primary task is git-aware code modification
- MCP extensibility isn't needed
- Simpler setup is preferred

### Future: Cline

Consider Cline for Phase 6 (IDE Integration) due to its MCP support and VS Code presence.

---

## Next Steps: Hands-On Testing

### Phase 1: Goose Evaluation

1. **Install**
   ```bash
   # Via pipx (recommended)
   pipx install goose-ai

   # Or via Homebrew
   brew install goose
   ```

2. **Configure Ollama**
   ```bash
   goose configure
   # Select Ollama provider
   # Set endpoint: http://localhost:11434
   ```

3. **Test Scenarios**
   - [ ] Create a new Python file from description
   - [ ] Edit an existing file
   - [ ] Run and debug code
   - [ ] Git commit workflow
   - [ ] Multi-file changes

4. **Document Findings**
   - Response quality with local models
   - Latency and performance
   - Failure modes and recovery

### Phase 2: Aider Comparison (Optional)

1. **Install**
   ```bash
   pipx install aider-chat
   ```

2. **Configure**
   ```bash
   # Set Ollama as provider
   export OLLAMA_API_BASE=http://localhost:11434
   aider --model ollama/qwen2.5-coder
   ```

3. **Same test scenarios** as Goose for comparison

### Success Criteria

- [ ] Framework connects to local Ollama
- [ ] Basic coding tasks complete successfully
- [ ] Performance acceptable for daily use (response < 30s for simple tasks)
- [ ] Clear understanding of limitations with local models

### Model Recommendations

See `docs/models/` for coding model evaluation. Key models to test:
- qwen2.5-coder (7B/14B)
- deepseek-coder-v2
- codellama

---

## References

- [Goose GitHub](https://github.com/block/goose)
- [Aider GitHub](https://github.com/paul-gauthier/aider)
- [Continue.dev](https://continue.dev)
- [Cline](https://cline.bot)
- [Ollama Integrations](https://docs.ollama.com/integrations)
- [MCP Specification](https://modelcontextprotocol.io)

---

*Last updated: 2026-01-27 — Initial evaluation*
