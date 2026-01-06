---
id: kb-2026-004
title: "DeepSeek Model Family"
created: 2026-01-06
updated: 2026-01-06

author: human
curation_type: ai_assisted

model_info:
  type: family
  family: deepseek
  developer: "DeepSeek AI"
  license: "MIT (R1), DeepSeek License (others)"
  release_date: 2023-11-01

  parameter_sizes: [1.5B, 7B, 8B, 14B, 16B, 32B, 33B, 70B, 236B, 671B]
  context_lengths: [16384, 32768, 65536, 131072]

  primary_capabilities:
    - code-generation
    - code-completion
    - reasoning
    - reasoning-cot
    - reasoning-math

  ollama_available: true
  ollama_tags:
    - "deepseek-coder-v2:16b"
    - "deepseek-coder-v2:236b"
    - "deepseek-r1:7b"
    - "deepseek-r1:14b"
    - "deepseek-r1:32b"
    - "deepseek-r1:70b"

sources:
  - id: src-001
    type: primary
    title: "DeepSeek-R1 GitHub Repository"
    url: "https://github.com/deepseek-ai/DeepSeek-R1"
    accessed: 2026-01-06
  - id: src-002
    type: primary
    title: "DeepSeek-R1 arXiv Paper"
    url: "https://arxiv.org/abs/2501.12948"
    accessed: 2026-01-06
  - id: src-003
    type: primary
    title: "DeepSeek-Coder-V2 GitHub Repository"
    url: "https://github.com/deepseek-ai/DeepSeek-Coder-V2"
    accessed: 2026-01-06
  - id: src-004
    type: secondary
    title: "DeepSeek Coder V2 Review: Features & Performance"
    url: "https://www.byteplus.com/en/topic/375605"
    accessed: 2026-01-06
  - id: src-005
    type: secondary
    title: "Deploying DeepSeek Coder Locally"
    url: "https://medium.com/@howard.zhang/deploying-deepseek-coder-locally-guided-by-deepseek-r1-part-1-2b9fea09138b"
    accessed: 2026-01-06

topics:
  - models
  - models/family/deepseek
  - coding
  - reasoning

confidence: high
verified: true
verified_by: human
verification_date: 2026-01-06
verification_notes: "Verified against official repos and papers"

ai_metadata:
  model: claude-opus-4-5-20251101
  generation_date: 2026-01-06
  reviewed_by: human
  review_date: 2026-01-06
---

# DeepSeek Model Family

## Overview

DeepSeek is a Chinese AI company that has produced some of the most impressive open-source models, particularly for coding and reasoning. Their models use innovative Mixture of Experts (MoE) architectures that provide high capability with relatively low compute requirements (fewer active parameters per inference).

**Why it matters for CC Forge:** DeepSeek models, especially DeepSeek-R1 distillations, offer state-of-the-art reasoning capabilities that can run locally. The coding models are among the best available.

## Lineage

```
DeepSeek (2024) ─ Foundation models
├── DeepSeek-V2 (May 2024) ─ MoE architecture
│   └── DeepSeek-V3 (December 2024) ─ Current flagship
│
├── DeepSeek-Coder (November 2023) ─ Code specialized
│   └── DeepSeek-Coder-V2 (June 2024) ─ MoE coder
│       ├── 16B (Lite) ─ Local-friendly
│       └── 236B ─ Full model
│
└── DeepSeek-R1 (January 2025) ─ Reasoning model
    ├── R1-Full (671B) ─ Full model
    └── R1-Distill ─ Distilled to smaller models
        ├── 1.5B (Qwen-based)
        ├── 7B (Qwen/Llama-based)
        ├── 8B (Llama-based)
        ├── 14B (Qwen-based)
        ├── 32B (Qwen-based)
        └── 70B (Llama-based)
```

## Key Models

### DeepSeek-Coder-V2

The coding-specialized model using Mixture of Experts architecture.

| Model | Total Params | Active Params | Context |
|-------|--------------|---------------|---------|
| DeepSeek-Coder-V2-Lite | 16B | 2.4B | 128K |
| DeepSeek-Coder-V2 | 236B | 21B | 128K |

**Benchmarks:**
- HumanEval: 90.2% accuracy [src-004]
- MBPP+: 76.2% accuracy [src-004]
- "Performance comparable to GPT4-Turbo in code-specific tasks" [src-003]

**Key Features:**
- MoE means fast inference despite large total parameters
- Fill-in-Middle (FIM) support
- 338 programming languages supported

**Hardware Requirements:**
- Full 236B model: "80GB x 8 GPUs required for BF16" [src-003]
- 16B Lite: Runs on consumer hardware with quantization

**Real-World Performance:**
- "Coding performance improved by roughly 20% and cut documentation searches by 40%" in local deployment [src-005]
- "Basic tasks like boilerplate code generation, helper function creation, or quick debugging suggestions run smoothly" [src-005]

### DeepSeek-R1

The reasoning-focused model that rivals OpenAI's o1. Released January 2025 and immediately made waves for its open-source availability.

| Model | Total Params | Active Params | Context |
|-------|--------------|---------------|---------|
| DeepSeek-R1 (Full) | 671B | 37B | 128K |
| DeepSeek-R1-Distill-1.5B | 1.5B | 1.5B | 64K |
| DeepSeek-R1-Distill-7B | 7B | 7B | 64K |
| DeepSeek-R1-Distill-8B | 8B | 8B | 64K |
| DeepSeek-R1-Distill-14B | 14B | 14B | 64K |
| DeepSeek-R1-Distill-32B | 32B | 32B | 64K |
| DeepSeek-R1-Distill-70B | 70B | 70B | 64K |

**Benchmarks:**
- AIME 2024: 79.8% pass@1 [src-002]
- MATH-500: 97.3% pass@1 [src-002]
- Codeforces: 2,029 Elo rating [src-002]
- "Performance comparable to OpenAI-o1 across math, code, and reasoning" [src-002]

**Key Features:**
- Chain-of-thought reasoning built into the model
- Shows its reasoning process (like o1)
- MIT License - fully open for commercial use [src-001]
- Distilled versions based on Qwen2.5 and Llama3 architectures

**R1-0528 Update (May 2025):**
- AIME 2025 accuracy improved from 70% to 87.5% [src-001]
- "Performance approaching O3 and Gemini 2.5 Pro" [src-001]

### DeepSeek-V3

The current flagship general-purpose model (December 2024).

- 671B total parameters, 37B active
- Strong general performance
- Not as focused on reasoning as R1

## Local Deployment

### Tier 1: Intel Arc (~8GB VRAM)

**Recommended:** DeepSeek-R1-Distill-7B (Qwen-based)

```bash
ollama pull deepseek-r1:7b
```

- Provides reasoning capabilities at 7B size
- Q4_K_M fits comfortably in 8GB VRAM
- Good for step-by-step problem solving

**Alternative:** DeepSeek-Coder-V2-Lite (16B) at Q4_K_M may fit with tight memory.

### Tier 2: CPU (64GB+ RAM)

**Options:**
- DeepSeek-R1-Distill-32B (~18GB at Q4_K_M)
- DeepSeek-R1-Distill-70B (~40GB at Q4_K_M)
- DeepSeek-Coder-V2-Lite-16B (high quality)

```bash
ollama pull deepseek-r1:32b-q4_K_M
ollama pull deepseek-r1:70b-q4_K_M
```

**Performance Note:** "The distilled 14B model outperforms QwQ-32B-Preview by a large margin" [src-001]. Even smaller distillations are highly capable.

### MoE Considerations

DeepSeek's MoE models (Coder-V2, R1-Full, V3) have:
- **Large total parameters** but **few active parameters**
- This means they need memory for the full model but compute only uses active portion
- Good for fast inference if you can fit the model

## Strengths

1. **Best open-source reasoning** - R1 rivals o1 in benchmarks
2. **MoE efficiency** - High capability with lower compute
3. **MIT License** - R1 is fully open, commercial use allowed
4. **Excellent distillations** - Small models retain much of the capability
5. **Strong coding** - Coder-V2 is among the best

## Limitations

1. **Memory requirements** - MoE models need memory for all parameters
2. **Chinese company** - Some enterprise concerns about origin
3. **Censorship** - Some Chinese political topics may be filtered
4. **Complexity** - MoE architecture can be harder to deploy

## CC Forge Recommendations

| Use Case | Model | Tier | Notes |
|----------|-------|------|-------|
| Reasoning (local) | DeepSeek-R1-Distill-7B | 1 (GPU) | Best reasoning at 7B |
| Reasoning (quality) | DeepSeek-R1-Distill-32B | 2 (CPU) | When 7B insufficient |
| Complex coding | DeepSeek-Coder-V2-Lite | 2 (CPU) | If Qwen-Coder insufficient |
| Math problems | DeepSeek-R1-Distill-14B+ | 2 (CPU) | Math-heavy tasks |

**Note:** For coding, Qwen2.5-Coder may be more practical for CC Forge due to simpler deployment. Use DeepSeek when reasoning is the primary requirement.

## Further Reading

- [DeepSeek Official Site](https://www.deepseek.com/)
- [DeepSeek GitHub](https://github.com/deepseek-ai)
- [DeepSeek-R1 Paper (arXiv)](https://arxiv.org/abs/2501.12948)
- [DeepSeek-R1 on Hugging Face](https://huggingface.co/deepseek-ai/DeepSeek-R1)
- [Ollama DeepSeek Models](https://ollama.com/library/deepseek-r1)
