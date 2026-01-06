---
id: kb-2026-001
title: "CC Forge Model Ontology"
created: 2026-01-06
updated: 2026-01-06

author: human
curation_type: ai_assisted

sources:
  - id: src-001
    type: secondary
    title: "Hugging Face Model Hub"
    url: "https://huggingface.co/models"
    accessed: 2026-01-06
  - id: src-002
    type: secondary
    title: "Ollama Model Library"
    url: "https://ollama.com/library"
    accessed: 2026-01-06

topics:
  - models
  - ontology
  - model-selection

confidence: medium
verified: false
verified_by: unverified
verification_date: 2026-01-06
verification_notes: "Structure based on current model landscape; needs ongoing updates"

ai_metadata:
  model: claude-opus-4-5-20251101
  generation_date: 2026-01-06
  reviewed_by: human
  review_date: 2026-01-06
---

# CC Forge Model Ontology

## Purpose

This ontology provides a structured way to understand, categorize, and select AI models for CC Forge. It serves two purposes:

1. **Human reference:** Navigate the model landscape, understand relationships
2. **Agent guidance:** Structured data for model selection decisions

## Ontology Structure

The ontology has three primary axes:

```
                    ┌─────────────────┐
                    │     MODELS      │
                    └────────┬────────┘
           ┌─────────────────┼─────────────────┐
           │                 │                 │
    ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
    │   LINEAGE   │   │ CAPABILITY  │   │ CONSTRAINTS │
    │  (Families) │   │  (Use Case) │   │ (Hardware)  │
    └─────────────┘   └─────────────┘   └─────────────┘
```

---

## Axis 1: Lineage (Model Families)

Models evolve through versions and branch into specialized variants. Understanding lineage helps predict behavior and compatibility.

### Text Generation Families

```
Meta / Llama Family
├── Llama 1 (2023-02) ─ Foundation
│   └── Llama 2 (2023-07) ─ Commercial release
│       ├── Llama 3 (2024-04) ─ Major architecture update
│       │   ├── Llama 3.1 (2024-07) ─ Extended context (128K)
│       │   │   └── Llama 3.2 (2024-09) ─ Multimodal, smaller variants
│       │   │       └── Llama 3.3 (2024-12) ─ 70B quality in smaller
│       └── Code Llama (2023-08) ─ Code-specialized branch
│           └── (Largely superseded by Llama 3.x for coding)

Alibaba / Qwen Family
├── Qwen (2023-08) ─ Initial release
│   └── Qwen 1.5 (2024-02) ─ Improved
│       └── Qwen 2 (2024-06) ─ Major update
│           └── Qwen 2.5 (2024-09) ─ Current generation
│               ├── Qwen 2.5-Coder ─ Code-specialized
│               └── QwQ (2024-11) ─ Reasoning-specialized

Mistral AI / Mistral Family
├── Mistral 7B (2023-09) ─ Foundation, efficient
│   ├── Mistral Nemo (2024-07) ─ 12B, Nvidia collab
│   ├── Mistral Small (2024) ─ Balanced
│   └── Mistral Large (2024) ─ Flagship
├── Mixtral 8x7B (2023-12) ─ Mixture of Experts
│   └── Mixtral 8x22B (2024-04) ─ Larger MoE
└── Codestral (2024-05) ─ Code-specialized

DeepSeek
├── DeepSeek (2024) ─ Foundation
│   ├── DeepSeek V2 (2024-05) ─ MoE architecture
│   │   └── DeepSeek V3 (2024-12) ─ Current flagship
│   └── DeepSeek-Coder (2023-11) ─ Code-specialized
│       └── DeepSeek-Coder-V2 (2024-06) ─ Updated coder
└── DeepSeek-R1 (2025-01) ─ Reasoning-specialized

Microsoft / Phi Family
├── Phi-1 (2023-06) ─ Tiny efficient
│   └── Phi-2 (2023-12) ─ 2.7B
│       └── Phi-3 (2024-04) ─ Current generation
│           ├── Phi-3-mini (3.8B)
│           ├── Phi-3-small (7B)
│           └── Phi-3-medium (14B)

Google / Gemma Family
├── Gemma (2024-02) ─ Open weights from Google
│   └── Gemma 2 (2024-06) ─ Updated
│       ├── 2B, 9B, 27B variants
│       └── CodeGemma ─ Code-specialized
```

### Image Generation Families

```
Stability AI / Stable Diffusion Family
├── SD 1.x (2022) ─ Original release
│   ├── SD 1.4
│   └── SD 1.5 ─ Most finetuned base
├── SD 2.x (2022-11) ─ New architecture
│   ├── SD 2.0
│   └── SD 2.1
├── SDXL (2023-07) ─ 1024px native
│   └── SDXL Turbo (2023-11) ─ Few-step
└── SD 3 (2024) ─ Latest architecture
    └── SD 3.5 (2024)

(Note: Flux, Midjourney, DALL-E are alternatives but less local-friendly)
```

### Embedding Models

```
Sentence Transformers Ecosystem
├── all-MiniLM-L6-v2 ─ Fast, decent quality
├── all-mpnet-base-v2 ─ Better quality
└── Instructor models ─ Task-specific

Nomic
└── nomic-embed-text ─ Good local option

Alibaba
└── gte-* models ─ Strong performance
```

---

## Axis 2: Capability (Use Case)

What do you need the model to do? This hierarchy helps navigate to relevant models.

```
Capabilities
│
├── Text Generation
│   │
│   ├── Code
│   │   ├── General Code Generation
│   │   │   → Qwen2.5-Coder, DeepSeek-Coder-V2, Codestral
│   │   ├── Code Completion / Infill (FIM)
│   │   │   → Qwen2.5-Coder, Codestral (supports FIM)
│   │   ├── Code Review / Explanation
│   │   │   → Any strong coder or general model
│   │   └── Specialized (by language)
│   │       → Generally not needed; modern coders handle all
│   │
│   ├── Reasoning
│   │   ├── Chain-of-Thought / Step-by-Step
│   │   │   → QwQ, DeepSeek-R1
│   │   ├── Mathematical
│   │   │   → QwQ, DeepSeek-R1, Qwen2.5-Math
│   │   └── Logical / Analytical
│   │       → QwQ, DeepSeek-R1, strong general models
│   │
│   ├── General Assistant / Chat
│   │   ├── Instruction Following
│   │   │   → Llama 3.3, Qwen2.5-Instruct, Mistral
│   │   ├── Long Context Processing
│   │   │   → Llama 3.1+ (128K), Qwen2.5 (128K)
│   │   └── Creative Writing
│   │       → General models, some prefer Llama for prose
│   │
│   └── Specialized Tasks
│       ├── Summarization → General models
│       ├── Translation → General models, some specialized
│       └── Extraction → General instruction models
│
├── Embedding / Retrieval
│   ├── Text Embedding
│   │   → nomic-embed-text, gte-*, all-MiniLM
│   └── Code Embedding
│   │   → Specialized or general embedding models
│
└── Image Generation
    ├── Text-to-Image
    │   → Stable Diffusion (1.5, SDXL, SD3)
    ├── Image-to-Image
    │   → SD with img2img
    └── Inpainting
        → SD with inpainting models
```

---

## Axis 3: Constraints (Hardware Tiers)

What can actually run on CC Forge hardware?

### Tier 1: Intel Arc GPU (~8GB VRAM)

**What fits:**
- 7B models at Q4_K_M to Q8_0
- Some 14B models at Q4_K_M
- SDXL (with optimizations)

**Recommended models:**
| Use Case | Model | Quantization |
|----------|-------|--------------|
| Coding | Qwen2.5-Coder-7B | Q8_0 or Q4_K_M |
| General | Llama-3.3-7B | Q8_0 or Q4_K_M |
| Reasoning | QwQ-7B (if available) | Q4_K_M |
| Embedding | nomic-embed-text | Default |

### Tier 2: CPU + System RAM (64GB+)

**What fits:**
- Up to 70B models at Q4_K_M
- Slower but more capable

**Recommended models:**
| Use Case | Model | Quantization | Notes |
|----------|-------|--------------|-------|
| Complex coding | DeepSeek-Coder-33B | Q4_K_M | Slow but capable |
| Complex reasoning | Qwen2.5-72B | Q4_K_M | Very slow |
| When 7B insufficient | Llama-3.3-70B | Q4_K_M | Quality jump |

### Tier 3: External API

**When to use:**
- Tasks requiring frontier model capabilities
- Time-critical with quality requirements
- Multimodal beyond local capability

---

## Navigation Guide

### "I need to generate code"

```
Code Generation
├── Quick/frequent tasks → Tier 1
│   └── Qwen2.5-Coder-7B-Instruct (Q8_0)
├── Complex/architectural → Tier 2
│   └── DeepSeek-Coder-V2 or Qwen2.5-Coder-32B (Q4_K_M)
└── FIM/Completion →
    └── Codestral or Qwen2.5-Coder with FIM
```

### "I need to reason through a problem"

```
Reasoning
├── Step-by-step analysis →
│   └── QwQ or DeepSeek-R1 (when available locally)
├── Mathematical →
│   └── QwQ, Qwen2.5-Math, DeepSeek-R1
└── General logic →
    └── Strong instruct model (Qwen2.5, Llama 3.3)
```

### "I need embeddings for RAG"

```
Embedding
├── General text →
│   └── nomic-embed-text (Ollama: nomic-embed-text)
├── High quality →
│   └── gte-large or similar
└── Code-specific →
    └── Evaluate based on retrieval quality
```

### "I need to generate images"

```
Image Generation
├── General purpose →
│   └── SDXL via Automatic1111
├── Fast iteration →
│   └── SD 1.5 (faster, more LoRAs available)
└── Highest quality →
    └── SDXL or SD 3.x
```

---

## Cross-References

- **Detailed family docs:** `families/*.md`
- **Capability deep-dives:** `capabilities/*.md`
- **Local deployment:** `local/*.md`
- **Selection guide:** `_selection-guide.md`
- **Controlled vocabularies:** `/knowledge/schema/model-vocabularies.md`

---

## Maintenance Notes

This ontology requires updates when:
- New major model releases occur
- Model capabilities significantly change
- Local testing reveals new information
- Hardware constraints change

**Last landscape review:** 2026-01-06
