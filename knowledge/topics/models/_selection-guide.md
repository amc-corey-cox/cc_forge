---
id: kb-2026-002
title: "CC Forge Model Selection Guide"
created: 2026-01-06
updated: 2026-01-06

author: human
curation_type: ai_assisted

sources:
  - id: src-001
    type: tertiary
    title: "LocalLLaMA Reddit Community"
    url: "https://reddit.com/r/LocalLLaMA"
    accessed: 2026-01-06
    notes: "Community experience reports"
  - id: src-002
    type: secondary
    title: "Ollama Model Library"
    url: "https://ollama.com/library"
    accessed: 2026-01-06

topics:
  - models
  - model-selection
  - local-deployment

confidence: medium
verified: false
verified_by: unverified
verification_date: 2026-01-06
verification_notes: "Based on community consensus; needs local validation"

ai_metadata:
  model: claude-opus-4-5-20251101
  generation_date: 2026-01-06
  reviewed_by: human
  review_date: 2026-01-06
---

# Model Selection Guide

A practical decision framework for choosing models in CC Forge.

---

## Quick Decision Matrix

| I need to... | Tier 1 (GPU) | Tier 2 (CPU) | Notes |
|--------------|--------------|--------------|-------|
| Write code | Qwen2.5-Coder-7B | DeepSeek-Coder-33B | Qwen strong at 7B |
| Reason step-by-step | QwQ-7B* | QwQ-32B | *Check availability |
| General assistant | Llama-3.3-8B | Llama-3.3-70B | Solid all-rounder |
| Process long docs | Qwen2.5-7B (128K) | Qwen2.5-72B | Context length key |
| Generate embeddings | nomic-embed-text | - | Runs fast on CPU too |
| Generate images | SDXL | - | Via Automatic1111 |

---

## Decision Flowchart

### Step 1: What's the primary task?

```
┌─────────────────────────────────────────────────────┐
│                What do you need?                     │
└─────────────────────────┬───────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
   ┌─────────┐      ┌──────────┐      ┌──────────┐
   │  CODE   │      │ REASONING│      │  GENERAL │
   └────┬────┘      └────┬─────┘      └────┬─────┘
        │                │                 │
        ▼                ▼                 ▼
   Go to §2A        Go to §2B         Go to §2C
```

### Step 2A: Code Generation

```
What kind of coding task?
│
├── Quick generation / completion
│   └── Tier 1: Qwen2.5-Coder-7B-Instruct
│       └── Ollama: qwen2.5-coder:7b-instruct
│
├── Complex / architectural decisions
│   └── Tier 2: DeepSeek-Coder-V2-Instruct (16B/33B)
│       └── Slower but handles complexity better
│
├── Fill-in-middle / autocomplete
│   └── Check if model supports FIM format
│       └── Qwen2.5-Coder and Codestral do
│
└── Code review / explanation
    └── Any capable instruct model
        └── Coding-specialized not required
```

### Step 2B: Reasoning Tasks

```
What kind of reasoning?
│
├── Math / logical puzzles
│   └── Reasoning-specialized models excel
│       ├── QwQ (Qwen reasoning)
│       └── DeepSeek-R1 (when available)
│
├── Step-by-step analysis
│   └── Models with chain-of-thought training
│       └── QwQ, or prompt general models with "think step by step"
│
└── General analytical
    └── Strong instruct models work fine
        └── Qwen2.5-Instruct, Llama-3.3
```

### Step 2C: General Assistant

```
What's the context?
│
├── Short conversations / tasks
│   └── Tier 1: Llama-3.3-8B or Qwen2.5-7B
│
├── Long document processing (>32K tokens)
│   └── Need 128K context model
│       └── Qwen2.5 or Llama-3.1+ with long context
│
└── Creative writing / prose
    └── Llama models often preferred for natural text
        └── Community preference, verify locally
```

### Step 3: Check Hardware Fit

```
Does your model fit Tier 1 (Intel Arc ~8GB)?
│
├── 7B model → Yes at Q8_0 or Q4_K_M
│
├── 14B model → Maybe at Q4_K_M (tight fit)
│
├── 32B+ model → No, use Tier 2 (CPU)
│
└── Unsure → Check model card for VRAM requirements
    └── Rule of thumb: Q4 needs ~0.5GB per billion params
```

---

## Model Recommendations by Role

### For CC Forge Agents

| Agent Role | Primary Model | Fallback | Why |
|------------|---------------|----------|-----|
| Dev Agent | Qwen2.5-Coder-7B | DeepSeek-Coder-33B | Code generation primary task |
| Test Agent | Qwen2.5-7B-Instruct | - | Understanding + generation |
| Red Team | Strong reasoning model | - | Analytical thinking needed |
| Blue Team | Similar to Test | - | Test analysis |

### For Knowledge Base RAG

| Component | Model | Notes |
|-----------|-------|-------|
| Embedding | nomic-embed-text | Good balance, Ollama native |
| Retrieval ranking | (future) | May add reranker |
| Generation | Task-appropriate | Use task model |

---

## Quantization Selection

### When to use which quantization?

| Scenario | Quantization | Reasoning |
|----------|--------------|-----------|
| Fits comfortably in VRAM | Q8_0 | Best quality |
| Tight VRAM fit | Q4_K_M | Good quality, 50% size |
| CPU inference | Q4_K_M | Speed matters more |
| Quality critical | Q6_K or Q8_0 | Noticeable difference |
| Just experimenting | Q4_K_M | Fast iteration |

### Quality Impact (General Guidelines)

```
Q8_0  ████████████████████ ~98% of FP16 quality
Q6_K  █████████████████░░░ ~95% of FP16 quality
Q5_K_M████████████████░░░░ ~93% of FP16 quality
Q4_K_M██████████████░░░░░░ ~90% of FP16 quality
Q3_K_M████████████░░░░░░░░ ~85% of FP16 quality (degradation visible)
```

*These are rough estimates; actual impact varies by model and task.*

---

## Common Pitfalls

### 1. Bigger Isn't Always Better (Locally)
A 7B model at Q8_0 may outperform a 70B at Q2_K due to quantization degradation.

### 2. Wrong Model for Task
Using a general model for code when Qwen2.5-Coder exists at the same size.

### 3. Ignoring Context Length
Loading a 4K context model for a task needing 32K tokens.

### 4. Forgetting Prompt Format
Each model family has preferred prompt formats. Wrong format = worse results.
- Llama 3: Uses special tokens `<|begin_of_text|>`, etc.
- Qwen: ChatML format preferred
- Mistral: `[INST]...[/INST]` format
- Ollama handles this automatically for chat

### 5. Not Testing Locally
Community benchmarks don't reflect your hardware. Always verify.

---

## Validation Checklist

Before committing to a model for production use:

- [ ] Does it fit in target hardware tier?
- [ ] Have you tested it on representative tasks?
- [ ] Is the prompt format correct?
- [ ] Is inference speed acceptable?
- [ ] Is the license compatible with your use?
- [ ] Is there a clear upgrade path if it's insufficient?

---

## Quick Reference: Ollama Commands

```bash
# List available models
ollama list

# Pull a model
ollama pull qwen2.5-coder:7b-instruct

# Pull specific quantization
ollama pull llama3.3:70b-q4_K_M

# Run interactive
ollama run qwen2.5-coder:7b-instruct

# Check model info
ollama show qwen2.5-coder:7b-instruct
```

---

## Cross-References

- **Ontology overview:** `_ontology.md`
- **Family details:** `families/*.md`
- **Capability deep-dives:** `capabilities/*.md`
- **Local deployment:** `local/*.md`
