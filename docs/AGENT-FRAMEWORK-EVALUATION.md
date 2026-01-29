# Agent Framework Evaluation

Evaluation of AI coding assistant frameworks for cc_forge's local-first MVP.

---

## Executive Summary

**Recommendation: Aider** as the primary framework for cc_forge's local-first MVP.

After hands-on testing, Goose's MCP architecture—while promising for future extensibility—has fundamental issues with local Ollama models. Tool calling fails consistently across multiple models tested. Aider's diff-based editing approach works reliably with local models, making it the practical choice for now.

**Secondary Option: Goose** for when cloud APIs are acceptable or local model tool-calling improves.

**Not Recommended: SERA** — Requires 80GB VRAM (A100/H100), no Ollama support.

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
- **Tool calling fails with local models** — tested with qwen2.5-coder, llama3.1, llama3-groq-tool-use
- Git integration less mature than Aider
- CLI configuration requires manual `goose configure` setup
- Desktop app separate from CLI installation

**cc_forge Fit**: Poor for local-first MVP (tool calling issues). Promising for future when local models improve or when cloud APIs are acceptable.

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

**cc_forge Fit**: Excellent for local-first MVP. Works reliably with local Ollama models. Extensibility limitations acceptable for Phase 1-3.

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

## Hands-On Testing Results (2026-01-29)

### Goose + Local Ollama: FAILED

**Setup**: Goose installed to `/usr/local/bin`, configured with Ollama endpoint.

**Models Tested**:
- `qwen2.5-coder:7b-instruct-q4_K_M`
- `llama3.1:latest`
- `llama3-groq-tool-use:8b`

**Results**: Tool calling fails with all local models tested.
- Models acknowledge tools exist but don't execute them
- File creation tasks resulted in only todo tool invocations, no actual files
- This is a known community issue with Goose + local models

**Root Cause**: Goose relies heavily on function/tool calling, which requires specific model training. Most local models lack robust tool-calling capabilities, causing the agent loop to fail.

### Aider + Local Ollama: SUCCESS

**Setup**: Aider installed via pipx to `/usr/local/bin`.

**Models Tested**:
- `qwen2.5-coder:7b-instruct-q4_K_M`

**Results**: Works reliably.
- File creation: ✓ Successfully created hello_world function
- Edit application: ✓ Diff-based edits applied correctly
- Performance: 607 tokens sent, 68 received — fast response

**Why It Works**: Aider uses diff-based editing (whole file or unified diff format) rather than tool calling. The model outputs code directly, and Aider parses and applies the diff. This approach is model-agnostic and works with any instruction-following model.

### SERA (AI2): NOT SUITABLE

**Overview**: AI2's new open-source coding agent family (8B-32B parameters).

**Performance**: SERA-32B achieves 54.2% on SWE-Bench Verified.

**Why Not Suitable**:
- Requires 80GB VRAM (A100/H100 GPUs)
- No GGUF files or Ollama support
- Recommended deployment is Modal (cloud), not local
- Great for cloud deployment and codebase fine-tuning, not local-first

---

## Recommendation

### Primary: Aider

Aider is the practical choice for cc_forge's local-first MVP because:

1. **Actually Works with Local Models**: Diff-based editing doesn't require tool calling, which local models struggle with.

2. **Excellent Git Integration**: Auto-commits with descriptive messages, easy undo — critical for iterative development.

3. **Terminal-First**: Matches the CLI-focused workflow.

4. **Simple Setup**: `pipx install aider-chat` and configure Ollama endpoint.

5. **Active Development**: Regular updates, responsive maintainers, strong community.

### Secondary: Goose

Consider Goose when:
- Using cloud APIs (Claude, GPT-4) with reliable tool calling
- MCP extensibility is required for custom tooling
- Local model tool-calling improves in the future

Goose's MCP architecture remains compelling for the long-term multi-agent vision. Revisit when local models support tool calling reliably.

### Future Considerations

- **Cline**: Consider for Phase 6 (IDE Integration) due to MCP support and VS Code presence.
- **SERA**: Watch for Ollama/GGUF support — good performance if hardware requirements drop.

---

## Next Steps

### Completed Testing

- [x] Goose installed and configured with Ollama
- [x] Goose tested with multiple local models (failed — tool calling issues)
- [x] Aider installed via pipx
- [x] Aider tested with qwen2.5-coder (success)
- [x] SERA evaluated (not suitable for local deployment)

### Remaining for MVP

- [ ] Extended Aider testing with real coding tasks
- [ ] Test Aider git integration workflow
- [ ] Document Aider configuration best practices
- [ ] Evaluate Aider with larger CPU-tier models (32B/70B)

### Success Criteria

- [x] Framework connects to local Ollama
- [x] Basic coding tasks complete successfully
- [x] Performance acceptable for daily use (response < 30s for simple tasks)
- [x] Clear understanding of limitations with local models

### Model Recommendations

See deployment guides for hardware-specific model details:
- GPU models: `models-intel-arc.md` (qwen2.5-coder-7b, deepseek-r1-7b)
- CPU models: `models-cpu-tier.md` (qwen2.5-coder-32b, llama-3.3-70b)
- Model registry: `models/` (tracking our local testing status)

---

## References

- [Goose GitHub](https://github.com/block/goose)
- [Aider GitHub](https://github.com/paul-gauthier/aider)
- [Continue.dev](https://continue.dev)
- [Cline](https://cline.bot)
- [Ollama Integrations](https://docs.ollama.com/integrations)
- [MCP Specification](https://modelcontextprotocol.io)

---

*Last updated: 2026-01-29 — Updated with hands-on testing results*
