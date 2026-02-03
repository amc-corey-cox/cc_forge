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

### OpenClaw (formerly Clawdbot/Moltbot)

**Overview**: Open-source autonomous personal AI assistant that went viral in early 2026. 100k+ GitHub stars. Runs locally and executes real actions via messaging apps.

**Ollama Support**: Yes, but demanding
- Native integration with auto-discovery of tool-capable models
- Set `OLLAMA_API_KEY="ollama-local"` in OpenClaw config (this is an OpenClaw convention; Ollama itself requires no API key)
- **Requires 48GB+ VRAM** for reliable operation — 72B models work best
- Smaller models (7B-13B) struggle with OpenClaw's complex system prompts

**Key Strengths**:
- **General-Purpose Agent**: Not just coding — handles any automation task
- **Messaging Integration**: Lives in WhatsApp, Telegram, Discord, iMessage
- **Dispatcher Architecture**: Can invoke other coding tools (Claude Code, Aider, Cursor)
- **Self-Improving**: Can write new skills to extend itself
- **Model-Agnostic**: Works with any provider (OpenAI, Anthropic, Ollama, etc.)

**Limitations**:
- **High VRAM requirements** for local-only operation
- Security is "an option, not built in" — documentation warns shell access is "spicy"
- Complex setup compared to simpler tools
- More infrastructure than coding assistant

**cc_forge Fit**: Promising for long-term multi-agent vision (Phase 8+). The dispatcher architecture aligns with Dev/Test/Red/Blue team concept. Overkill for MVP — adds complexity without clear benefit for Phase 1-3.

**Links**: [Website](https://openclaw.ai) | [Docs](https://docs.openclaw.ai) | [GitHub](https://github.com/openclaw/openclaw) | [Ollama Config](https://docs.openclaw.ai/providers/ollama)

---

### Claude Code + Ollama (TESTED)

**Overview**: Anthropic's Claude Code CLI can connect to local Ollama models via Ollama's Anthropic Messages API compatibility layer (added in Ollama 0.14+).

**Ollama Support**: Works with caveats
- Requires Ollama 0.14+ for Anthropic API compatibility
- Configure via environment variables pointing to local Ollama endpoint
- Same Claude Code interface, but with local model execution

**Setup**:
```bash
# CPU service (default, recommended)
ANTHROPIC_BASE_URL=http://localhost:11434 claude --model llama3.1

# GPU via shim (required workaround - see Known Issues)
ANTHROPIC_BASE_URL=http://localhost:4001 claude --model llama3.1
```

**Key Strengths**:
- **Familiar Interface**: Same Claude Code experience used with cloud models
- **No Subscription**: Local execution eliminates API costs
- **Existing Workflow**: No new tool to learn
- **Full Claude Code Features**: All tools, MCP support, git integration

**Limitations**:
- **Large System Prompt**: Claude Code sends ~18KB system prompts, causing slow first requests (60-90s) and sometimes confusing smaller models
- **Model Quality**: Local models won't match Claude Opus/Sonnet capabilities
- **Vulkan GPU Bug**: Ollama's Anthropic API (`/v1/messages`) crashes with Vulkan backend — requires shim workaround (see `LOCAL-OLLAMA-SETUP.md`)
- Article notes you "lose the capabilities of Anthropic's very top models"

**Known Issues**:
- **Anthropic API + Vulkan = Crash**: Direct connection to Vulkan GPU service crashes. Use [ollama-anthropic-shim](https://github.com/hilyin/ollama-anthropic-shim) to translate Anthropic API → native Ollama API
- **Slow First Request**: Claude Code's large system prompt takes 60-90s on first request with local models

**cc_forge Fit**: **Works but has rough edges.** Familiar interface is a major benefit. Best for users already comfortable with Claude Code who want to experiment with local models. For pure local-first work, Aider may still be more practical due to smaller prompts and diff-based approach.

**Links**: [Towards Data Science Guide](https://towardsdatascience.com/run-claude-code-for-free-with-local-and-cloud-models-from-ollama/) | [Setup Guide](LOCAL-OLLAMA-SETUP.md#claude-code-integration)

---

## Comparison Matrix

| Feature | Goose | Aider | Continue | Cline | OpenClaw | Claude Code + Ollama |
|---------|-------|-------|----------|-------|----------|-------------------|
| **Ollama Support** | Excellent | Excellent | Good | Good | Yes (48GB+) | Works* |
| **MCP/Extensibility** | Excellent | None | Limited | Good | Excellent | Full |
| **Git Integration** | Basic | Excellent | Good | Good | Via skills | Excellent |
| **Terminal-First** | Yes | Yes | No | No | No (messaging) | Yes |
| **Local-First** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Agent Autonomy** | Full | Full | Full | Full | Full | Full |
| **Maturity** | High | High | High | High | Medium | Tested |
| **Min Local VRAM** | 8GB | 8GB | 8GB | 8GB | 48GB | 8GB |

*\* Claude Code + Ollama works but requires shim for GPU acceleration due to Anthropic API bug with Vulkan backend*
| **GitHub Stars** | 29k+ | 25k+ | 20k+ | 15k+ | 100k+ | N/A |

---

## Hands-On Testing Results

### Goose + Local Ollama: FAILED

**Setup**: Goose installed to `/usr/local/bin`, configured with Ollama endpoint.

**Configuration** (`~/.config/goose/config.yaml`):
```yaml
GOOSE_PROVIDER: ollama
GOOSE_MODEL: llama3-groq-tool-use:8b
OLLAMA_HOST: http://localhost:11434
OLLAMA_CONTEXT_LENGTH: 32768
extensions:
  developer:
    bundled: true
    enabled: true
    name: developer
    timeout: 300
    type: builtin
```

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

### Claude Code + Local Ollama: WORKS (with caveats)

**Setup**: Ollama 0.15.4 with Anthropic Messages API compatibility. Tested on tesseract server with Intel Arc GPU.

**Services Tested**:
- CPU service (port 11434): Works directly
- Vulkan GPU service (port 11435): Crashes with Anthropic API — requires shim

**Results**:
- **CPU Direct**: ✓ Works, but slow (~60-90s first request due to 18KB system prompt)
- **GPU Direct**: ✗ Crashes — Ollama's `/v1/messages` endpoint fails with Vulkan backend
- **GPU via Shim**: ✓ Works — [ollama-anthropic-shim](https://github.com/hilyin/ollama-anthropic-shim) translates Anthropic API → native Ollama API

**Why the Shim Works**: The shim converts Claude Code's Anthropic API calls to Ollama's native chat API, bypassing the buggy `/v1/messages` endpoint. See [Ollama Issue #13949](https://github.com/ollama/ollama/issues/13949).

**Practical Assessment**: Claude Code's large system prompt (~18KB) is designed for Claude models. Local 7B models sometimes get confused by the complexity. Aider's smaller, focused prompts work better with limited-capability models.

---

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

- **Claude Code + Ollama**: Tested and working. Viable option for users familiar with Claude Code, but Aider remains more practical for local-only use due to simpler prompts.
- **OpenClaw**: Consider for Phase 8+ (multi-agent orchestration). Dispatcher architecture fits the Dev/Test/Red/Blue team vision, but overkill for MVP.
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
- [x] Claude Code + Ollama tested (works with CPU; GPU requires shim workaround)
- [x] Ollama upgraded to 0.15.4 for Anthropic API compatibility
- [x] Dual-service architecture deployed (CPU port 11434, Vulkan GPU port 11435)

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
- [OpenClaw](https://openclaw.ai) | [Docs](https://docs.openclaw.ai) | [GitHub](https://github.com/openclaw/openclaw)
- [Claude Code + Ollama Guide](https://towardsdatascience.com/run-claude-code-for-free-with-local-and-cloud-models-from-ollama/)
- [Ollama Integrations](https://docs.ollama.com/integrations)
- [MCP Specification](https://modelcontextprotocol.io)

---

*Last updated: 2026-02-03 — Added Claude Code + Ollama hands-on testing results*
