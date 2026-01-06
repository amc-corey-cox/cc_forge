---
id: kb-2026-005
title: "Meta Llama Model Family"
created: 2026-01-06
updated: 2026-01-06

author: human
curation_type: ai_assisted

model_info:
  type: family
  family: llama
  developer: "Meta AI"
  license: "Llama 3.3 Community License"
  release_date: 2023-02-24

  parameter_sizes: [1B, 3B, 8B, 11B, 70B, 90B, 405B]
  context_lengths: [8192, 32768, 131072]

  primary_capabilities:
    - chat
    - instruction-following
    - code-generation
    - creative-writing
    - long-context

  ollama_available: true
  ollama_tags:
    - "llama3.2:1b"
    - "llama3.2:3b"
    - "llama3.3:70b"
    - "llama3.1:8b"
    - "llama3.1:70b"
    - "llama3.1:405b"

sources:
  - id: src-001
    type: primary
    title: "Llama 3.3 Announcement - Meta AI"
    url: "https://ai.meta.com/blog/llama-3-3-70b/"
    accessed: 2026-01-06
  - id: src-002
    type: secondary
    title: "I can now run a GPT-4 class model on my laptop"
    authors: ["Simon Willison"]
    url: "https://simonwillison.net/2024/Dec/9/llama-33-70b/"
    accessed: 2026-01-06
  - id: src-003
    type: secondary
    title: "Llama 3.3 70B and Ollama - Collabnix"
    url: "https://collabnix.com/what-is-metas-llama-3-3-70b/"
    accessed: 2026-01-06
  - id: src-004
    type: secondary
    title: "Local LLM Benchmarks 2025"
    url: "https://www.practicalwebtools.com/blog/local-llm-benchmarks-consumer-hardware-guide-2025"
    accessed: 2026-01-06

topics:
  - models
  - models/family/llama
  - general-purpose
  - chat

confidence: high
verified: true
verified_by: human
verification_date: 2026-01-06
verification_notes: "Verified against Meta announcements and community reports"

ai_metadata:
  model: claude-opus-4-5-20251101
  generation_date: 2026-01-06
  reviewed_by: human
  review_date: 2026-01-06
---

# Meta Llama Model Family

## Overview

Llama (Large Language Model Meta AI) is Meta's open-weights model family and arguably the most influential open-source LLM series. The Llama architecture has become a de facto standard, with many other models (Qwen, Mistral, etc.) using compatible architectures. Llama 3.3 70B represents a landmark: GPT-4 class performance running on consumer hardware.

**Why it matters for CC Forge:** Llama models are the baseline. They're well-supported everywhere (Ollama, vLLM, llama.cpp), have extensive community knowledge, and provide solid all-around performance. When in doubt, Llama is a safe choice.

## Lineage

```
Llama 1 (February 2023) ─ Research release
└── Llama 2 (July 2023) ─ First commercial license
    ├── Code Llama (August 2023) ─ Code specialized
    │   └── (Largely superseded by Llama 3.x)
    │
    └── Llama 3 (April 2024) ─ Major architecture update
        ├── Llama 3.1 (July 2024) ─ Extended context (128K)
        │   ├── 8B, 70B, 405B variants
        │   │
        │   └── Llama 3.2 (September 2024) ─ Multimodal + small
        │       ├── 1B, 3B (text-only, edge)
        │       ├── 11B, 90B (vision)
        │       │
        │       └── Llama 3.3 (December 2024) ─ Optimized 70B
        │           └── 70B (text-only, high quality)
```

## Key Models

### Llama 3.3 70B

The current flagship, released December 2024. Delivers Llama 3.1 405B-level quality in a 70B model.

| Aspect | Specification |
|--------|---------------|
| Parameters | 70B |
| Context | 128K tokens |
| Languages | 8 (EN, DE, FR, IT, PT, HI, ES, TH) |
| Architecture | Grouped-Query Attention (GQA) |

**Key Claims:**
- "Performance comparable to the much larger Llama 3.1 405B model" [src-001]
- "A genuinely GPT-4 class Large Language Model that runs on a laptop" [src-002]

**Benchmarks:**
- Competitive with GPT-4o on many tasks
- Strong instruction following
- Good at creative writing and natural prose

### Llama 3.2 (Small & Vision)

Smaller models for edge deployment and multimodal variants.

| Model | Parameters | Context | Features |
|-------|------------|---------|----------|
| Llama-3.2-1B | 1B | 128K | Edge deployment |
| Llama-3.2-3B | 3B | 128K | Edge deployment |
| Llama-3.2-11B-Vision | 11B | 128K | Image understanding |
| Llama-3.2-90B-Vision | 90B | 128K | Image understanding |

### Llama 3.1 (Still Relevant)

| Model | Parameters | Context | Notes |
|-------|------------|---------|-------|
| Llama-3.1-8B | 8B | 128K | Good local option |
| Llama-3.1-70B | 70B | 128K | Superseded by 3.3 |
| Llama-3.1-405B | 405B | 128K | Largest, needs cloud |

## Local Deployment

### Tier 1: Intel Arc (~8GB VRAM)

**Recommended:** Llama-3.2-3B or Llama-3.1-8B

```bash
# Smaller, faster
ollama pull llama3.2:3b

# More capable
ollama pull llama3.1:8b-instruct-q4_K_M
```

**Notes:**
- 3B: Fits easily, fast inference, limited capability
- 8B at Q4_K_M: ~4.5GB, good balance
- 8B at Q8_0: ~8GB, tight fit on 8GB VRAM

### Tier 2: CPU (64GB+ RAM)

**Recommended:** Llama-3.3-70B

```bash
ollama pull llama3.3:70b-instruct-q4_K_M
```

**Real-World Performance:**
- "The Ollama download fetched 42GB of data" [src-002]
- "Requires approximately 64GB of RAM to work well" [src-002]
- "The first time I tried it, it consumed every remaining bit of available memory and hard-crashed my Mac" [src-002]
- On M2 Pro 32GB at Q4: "8.4 tokens/second - the model works" [src-004]
- On RTX 4090: Runs with Q4_K_M if context kept ≤16K [src-003]

**Tip:** Close other applications before running 70B locally. It's memory hungry.

### Hardware Requirements Summary

| Model | Quantization | VRAM/RAM Needed | Speed |
|-------|--------------|-----------------|-------|
| 3.2-1B | Q8_0 | ~1GB | Very fast |
| 3.2-3B | Q8_0 | ~3GB | Fast |
| 3.1-8B | Q4_K_M | ~4.5GB | Fast |
| 3.1-8B | Q8_0 | ~8GB | Good |
| 3.3-70B | Q4_K_M | ~42GB | Slow (CPU) |
| 3.3-70B | Q8_0 | ~70GB | Very slow (CPU) |

### Prompt Format

Llama 3 uses special tokens:

```
<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a helpful assistant<|eot_id|><|start_header_id|>user<|end_header_id|>

Hello<|eot_id|><|start_header_id|>assistant<|end_header_id|>
```

Ollama handles this automatically.

## Strengths

1. **Universal support** - Works everywhere (Ollama, vLLM, llama.cpp, etc.)
2. **Excellent ecosystem** - Most community tools support Llama first
3. **Natural prose** - Often preferred for creative writing
4. **Strong baseline** - Solid all-around performance
5. **Commercial license** - Permissive for most uses
6. **GPT-4 class at 70B** - Genuinely capable locally

## Limitations

1. **Not the best at coding** - Qwen-Coder and DeepSeek-Coder beat it
2. **No reasoning variant** - Unlike Qwen (QwQ) or DeepSeek (R1)
3. **70B is large** - Needs serious hardware for good speed
4. **8B is mediocre** - Other 7-8B models (Qwen, Mistral) often outperform
5. **License restrictions** - Some limits for very large deployments

## Community Reception

"Just 20 months ago, running something GPT-3 class on the same machine was amazing. The quality of models that are accessible on consumer hardware has improved dramatically in the past two years." [src-002]

"Llama 3.3 70B marries impressive benchmark clout with realistic hardware demands, earning its place as the workhorse of the open-source LLM world." [src-003]

## CC Forge Recommendations

| Use Case | Model | Tier | Notes |
|----------|-------|------|-------|
| Quick tasks | Llama-3.2-3B | 1 (GPU) | Fast, limited |
| General assistant | Llama-3.1-8B | 1 (GPU) | Good balance |
| Creative writing | Llama-3.3-70B | 2 (CPU) | Best prose |
| Coding | *Use Qwen-Coder instead* | - | Llama not optimal |
| Reasoning | *Use QwQ or R1 instead* | - | Llama lacks CoT |

**Primary Role in CC Forge:** Backup/baseline model. Use specialized models (Qwen-Coder, QwQ) for specific tasks, Llama when you need a reliable general-purpose option.

## Further Reading

- [Meta AI Blog](https://ai.meta.com/blog/)
- [Llama on Hugging Face](https://huggingface.co/meta-llama)
- [Ollama Llama Models](https://ollama.com/library/llama3.3)
- [llama.cpp GitHub](https://github.com/ggerganov/llama.cpp)
