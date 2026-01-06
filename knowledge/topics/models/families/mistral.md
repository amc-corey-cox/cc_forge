---
id: kb-2026-006
title: "Mistral AI Model Family"
created: 2026-01-06
updated: 2026-01-06

author: human
curation_type: ai_assisted

model_info:
  type: family
  family: mistral
  developer: "Mistral AI"
  license: "Apache 2.0 (open models), Proprietary (commercial)"
  release_date: 2023-09-27

  parameter_sizes: [7B, 8B, 12B, 22B, 24B, 8x7B, 8x22B]
  context_lengths: [8192, 32768, 131072, 262144]

  primary_capabilities:
    - chat
    - instruction-following
    - code-generation
    - code-completion

  ollama_available: true
  ollama_tags:
    - "mistral:7b"
    - "mistral-nemo:12b"
    - "mixtral:8x7b"
    - "mixtral:8x22b"
    - "codestral:22b"

sources:
  - id: src-001
    type: primary
    title: "Codestral Announcement - Mistral AI"
    url: "https://mistral.ai/news/codestral"
    accessed: 2026-01-06
  - id: src-002
    type: primary
    title: "Codestral 25.01 Announcement"
    url: "https://mistral.ai/news/codestral-2501"
    accessed: 2026-01-06
  - id: src-003
    type: secondary
    title: "Mistral Codestral 25.01: Is it the best model for coding?"
    url: "https://blog.getbind.co/2025/01/15/mistral-codestral-25-01-is-it-the-best-model-for-coding/"
    accessed: 2026-01-06
  - id: src-004
    type: secondary
    title: "Mistral AI Codestral Review 2025"
    url: "https://www.index.dev/blog/mistral-ai-coding-challenges-tests"
    accessed: 2026-01-06
  - id: src-005
    type: primary
    title: "Devstral Announcement"
    url: "https://mistral.ai/news/devstral"
    accessed: 2026-01-06

topics:
  - models
  - models/family/mistral
  - coding
  - efficiency

confidence: high
verified: true
verified_by: human
verification_date: 2026-01-06
verification_notes: "Verified against official Mistral announcements"

ai_metadata:
  model: claude-opus-4-5-20251101
  generation_date: 2026-01-06
  reviewed_by: human
  review_date: 2026-01-06
---

# Mistral AI Model Family

## Overview

Mistral AI is a French AI company founded by former Google DeepMind and Meta researchers. They focus on efficient, high-performance models and have pioneered techniques like sliding window attention. Mistral models are known for punching above their weight class.

**Why it matters for CC Forge:** Mistral's Codestral offers best-in-class Fill-in-Middle (FIM) capability with a massive 256K context window. If you need code completion or working with very large codebases, Codestral is worth considering.

## Lineage

```
Mistral 7B (September 2023) ─ Foundation, efficient architecture
├── Mistral 7B v0.2 (December 2023) ─ Improved
│   └── Mistral 7B v0.3 (May 2024) ─ Function calling
│
├── Mixtral 8x7B (December 2023) ─ MoE architecture
│   └── Mixtral 8x22B (April 2024) ─ Larger MoE
│
├── Mistral Nemo (July 2024) ─ 12B, Nvidia collaboration
│
├── Mistral Small/Medium/Large (2024) ─ Commercial tiers
│
├── Codestral (May 2024) ─ Code specialized
│   ├── Codestral 22B ─ Original
│   ├── Codestral 25.01 (January 2025) ─ Improved
│   └── Codestral 25.08 (August 2025) ─ Latest
│
└── Devstral (2025) ─ Agentic coding (24B)
```

## Key Models

### Mistral 7B

The original efficient model that put Mistral on the map.

| Aspect | Specification |
|--------|---------------|
| Parameters | 7B |
| Context | 8K (v0.1), 32K (v0.2+) |
| Architecture | Sliding Window Attention |

**Strengths:**
- Very efficient for its size
- Good baseline model
- Apache 2.0 license

**Current Status:** Somewhat superseded by newer models but still useful for constrained environments.

### Mistral Nemo

12B model developed in collaboration with Nvidia.

| Aspect | Specification |
|--------|---------------|
| Parameters | 12B |
| Context | 128K |
| License | Apache 2.0 |

**Strengths:**
- Good balance of size and capability
- 128K context
- Function calling support

### Mixtral (MoE Models)

Mixture of Experts models with high capability.

| Model | Total Params | Active Params | Context |
|-------|--------------|---------------|---------|
| Mixtral 8x7B | 47B | 13B | 32K |
| Mixtral 8x22B | 176B | 44B | 64K |

**Notes:**
- MoE means fast inference for the capability level
- Requires memory for full parameters but only computes with active portion
- 8x7B is popular for local deployment

### Codestral (Code Specialized)

Mistral's flagship coding model. Key differentiator: **256K context window** (largest among coding models).

| Version | Parameters | Context | HumanEval |
|---------|------------|---------|-----------|
| Codestral 22B | 22B | 256K | ~85% |
| Codestral 25.01 | 22B | 256K | 86.6% |
| Codestral 25.08 | 22B | 256K | Higher |

**Key Features:**
- 256K context window - can see entire large codebases [src-001]
- Fill-in-Middle (FIM) - native code completion support [src-001]
- 80+ programming languages [src-001]
- "#1 on LMsys copilot arena leaderboard" at launch [src-003]

**Benchmark Performance:**
- HumanEval: 86.6% [src-004]
- "Excels at scaffolding, test generation, and refactoring" [src-004]
- "Struggles with multi-file coordination" [src-004]

**Licensing Complexity:**
- **Codestral base:** Available through API, self-deployment for enterprises [src-003]
- **Not fully open-weight** - cannot freely download and run locally in all cases [src-003]
- Check current licensing before deploying

### Devstral (Agentic Coding)

Announced in 2025, specifically designed for agentic software development workflows.

| Aspect | Specification |
|--------|---------------|
| Parameters | 24B |
| Focus | Agentic coding tasks |
| License | Open weights |

**Key Features:**
- Optimized for GitHub issue handling across entire codebases
- Designed for agentic workflows (multi-step, tool use)
- Open weights unlike Codestral [src-005]

## Local Deployment

### Tier 1: Intel Arc (~8GB VRAM)

**Recommended:** Mistral 7B

```bash
ollama pull mistral:7b-instruct-v0.3-q8_0
ollama pull mistral:7b-instruct-v0.3-q4_K_M
```

- Q8_0: ~7GB, good quality
- Q4_K_M: ~4GB, acceptable quality

**Notes:**
- Good general-purpose option
- For coding specifically, Qwen2.5-Coder-7B likely better

### Codestral Considerations

**Availability:**
- Codestral is in Ollama but check licensing terms
- May require API access or enterprise agreement for full local deployment

```bash
# If available and licensed
ollama pull codestral:22b-v0.1-q4_K_M
```

**Hardware:**
- 22B at Q4_K_M: ~12-14GB - too large for 8GB VRAM
- Would need Tier 2 (CPU) or larger GPU

### Tier 2: CPU (64GB+ RAM)

**Options:**
- Mixtral 8x7B at Q4_K_M (~26GB)
- Codestral 22B at Q4_K_M (~14GB)

```bash
ollama pull mixtral:8x7b-instruct-v0.1-q4_K_M
```

## Strengths

1. **Efficient architectures** - Sliding window attention, MoE
2. **Codestral's 256K context** - See entire codebases
3. **Fill-in-Middle** - Native code completion
4. **French/European** - Data sovereignty considerations
5. **Devstral for agents** - Purpose-built for agentic coding

## Limitations

1. **Codestral licensing** - Not fully open, check terms
2. **Less active open development** - Compared to Qwen, DeepSeek
3. **7B showing age** - Other 7B models have caught up
4. **MoE memory requirements** - Full params need full memory
5. **No dedicated reasoning model** - Unlike QwQ, R1

## CC Forge Recommendations

| Use Case | Model | Tier | Notes |
|----------|-------|------|-------|
| Code completion (FIM) | Codestral | 2+ | If licensing allows |
| Large codebase work | Codestral | 2+ | 256K context |
| General (constrained) | Mistral 7B | 1 (GPU) | Good baseline |
| Agentic coding | Devstral | 2 (CPU) | When available |

**Primary Role in CC Forge:** Codestral is compelling for its FIM capability and huge context window, but licensing complexity makes it secondary to Qwen-Coder for most uses. Monitor Devstral for agentic applications.

## FIM (Fill-in-Middle) Example

Codestral's FIM format for code completion:

```
[PREFIX]def calculate_total(items):
    total = 0
    for item in items:
[SUFFIX]
    return total
[MIDDLE]
```

The model fills in the middle section - useful for IDE-style code completion.

## Further Reading

- [Mistral AI Official](https://mistral.ai/)
- [Mistral Documentation](https://docs.mistral.ai/)
- [Codestral Announcement](https://mistral.ai/news/codestral)
- [Ollama Mistral Models](https://ollama.com/library/mistral)
- [Mixtral Paper](https://arxiv.org/abs/2401.04088)
