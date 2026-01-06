---
id: kb-2026-011
title: "CPU Tier Model Deployment"
created: 2026-01-06
updated: 2026-01-06

author: human
curation_type: ai_assisted

sources:
  - id: src-001
    type: secondary
    title: "Llama 3.3 70B Local Performance"
    url: "https://simonwillison.net/2024/Dec/9/llama-33-70b/"
    accessed: 2026-01-06
  - id: src-002
    type: secondary
    title: "Local LLM Benchmarks 2025"
    url: "https://www.practicalwebtools.com/blog/local-llm-benchmarks-consumer-hardware-guide-2025"
    accessed: 2026-01-06

topics:
  - models
  - models/local
  - cpu-inference

confidence: medium
verified: true
verified_by: human
verification_date: 2026-01-06
verification_notes: "Based on community benchmarks and reports"

ai_metadata:
  model: claude-opus-4-5-20251101
  generation_date: 2026-01-06
  reviewed_by: human
  review_date: 2026-01-06
---

# CPU Tier Model Deployment

## Overview

When models don't fit on GPU (Tier 1), CPU inference is the fallback. It's slow but capable—you can run 70B+ parameter models on sufficient RAM.

**Key constraint:** Speed. Expect 1-5 tokens/second depending on model size and hardware.

**When to use:** Complex tasks where quality matters more than speed.

## Hardware Requirements

### Minimum for Large Models

| Model Size | RAM Needed (Q4_K_M) | RAM Needed (Q8_0) |
|------------|---------------------|-------------------|
| 32B | ~20GB | ~35GB |
| 70B | ~42GB | ~75GB |
| 72B (Qwen) | ~44GB | ~78GB |

**Rule of thumb:** Need 1.5x the model file size in available RAM.

### Recommended System

For running 70B models comfortably:
- **RAM:** 64GB minimum, 128GB preferred
- **Storage:** SSD for model loading
- **CPU:** Modern multi-core (more cores = faster prompt processing)

## Performance Expectations

### Token Generation Speed

Based on community benchmarks [src-002]:

| Model | Quantization | ~Speed | Notes |
|-------|--------------|--------|-------|
| 32B Q4_K_M | Q4_K_M | 3-5 tok/s | Usable |
| 70B Q4_K_M | Q4_K_M | 1-3 tok/s | Slow but works |
| 70B Q8_0 | Q8_0 | 0.5-1 tok/s | Very slow |

### Real-World Reports

**Llama 3.3 70B on M2 Pro 32GB (Q4):**
- "8.4 tokens/second - the model works" [src-002]
- Prompt processing is faster; generation is the bottleneck

**70B on 64GB RAM:**
- "Requires approximately 64GB of RAM to work well" [src-001]
- First attempt may crash system if other apps open [src-001]
- Close browsers, IDEs before running

## What Runs on CPU Tier

### Good Candidates

Models that benefit from CPU tier (too big for 8GB GPU):

| Model | Size | Use Case | Speed |
|-------|------|----------|-------|
| **Qwen2.5-Coder-32B** | ~18GB | Complex coding | 3-5 tok/s |
| **QwQ-32B** | ~18GB | Reasoning | 2-4 tok/s |
| **DeepSeek-R1-32B** | ~18GB | Reasoning | 2-4 tok/s |
| **Llama-3.3-70B** | ~42GB | General, best quality | 1-3 tok/s |
| **DeepSeek-R1-70B** | ~42GB | Best reasoning | 1-2 tok/s |
| **Qwen2.5-72B** | ~44GB | Best open-source | 1-2 tok/s |

### Pulling Large Models

```bash
# 32B models (~18GB download)
ollama pull qwen2.5-coder:32b-instruct-q4_K_M
ollama pull qwq:32b-q4_K_M
ollama pull deepseek-r1:32b-q4_K_M

# 70B models (~40-45GB download)
ollama pull llama3.3:70b-instruct-q4_K_M
ollama pull deepseek-r1:70b-q4_K_M
ollama pull qwen2.5:72b-instruct-q4_K_M
```

**Note:** Large downloads. Ensure stable connection and disk space.

## Usage Strategies

### When to Use CPU Tier

| Scenario | Use CPU Tier? | Why |
|----------|---------------|-----|
| Quick coding question | No | 7B on GPU faster |
| Complex architecture decision | Yes | 32B quality worth the wait |
| Debugging subtle bug | Maybe | Try 7B first, escalate if needed |
| Step-by-step math proof | Yes | Reasoning models excel |
| Batch processing many items | No | Speed matters |
| Single critical analysis | Yes | Quality matters |

### Practical Workflow

1. **Try Tier 1 (GPU) first** for most tasks
2. **Escalate to Tier 2 (CPU)** when:
   - 7B model produces wrong answers
   - Task requires complex reasoning
   - Quality is critical
3. **Accept the wait** - start the task, do something else

### Batching Strategy

For CPU inference, batch your questions:
- Prepare multiple questions
- Run them sequentially (model stays loaded)
- Loading time amortized across questions

## Memory Management

### Before Running Large Models

```bash
# Check available memory
free -h

# Close memory-hungry apps
# - Browsers (especially Chrome/Firefox with many tabs)
# - IDEs (VS Code, JetBrains)
# - Docker containers if not needed

# Verify model will fit
# Model file size + ~20% overhead < Available RAM
```

### If System Crashes

Large models can consume all RAM and crash the system.

**Prevention:**
- Start with smaller models to test
- Monitor memory: `watch -n 1 free -h`
- Set memory limits if possible

**Recovery:**
- Restart Ollama service after system recovery
- Consider smaller quantization

## Service Configuration

### Using ollama-cpu Service

CC Forge's `ollama-cpu` service is the default for large models:

```bash
# Ensure CPU service is active
sudo systemctl is-active ollama-cpu

# If not, switch to it
sudo systemctl disable --now ollama-ipex
sudo systemctl enable --now ollama-cpu
```

### Why Not GPU + CPU Split?

Intel Arc doesn't reliably support partial offloading. Running the full model on CPU is more stable than attempting a split.

## Optimization Tips

### Quantization Choice

For CPU inference, Q4_K_M is usually best:
- Q8_0: Better quality but uses more RAM and is slower
- Q4_K_M: Good balance of quality, speed, and RAM usage
- Q3_K_M: Only if RAM is extremely tight (quality suffers)

### Context Length

Longer context = more RAM and slower inference.
- Keep context reasonable (4K-8K if possible)
- Use RAG to retrieve relevant context rather than loading everything

### Prompt Efficiency

- Be concise in prompts
- Don't repeat context unnecessarily
- System prompts count toward context

## Expected Wait Times

For a typical response (500 tokens) on 70B Q4_K_M:

| Hardware | Generation Time |
|----------|-----------------|
| 64GB RAM, modern CPU | ~3-5 minutes |
| 128GB RAM, fast CPU | ~2-3 minutes |
| Server-class | ~1-2 minutes |

**Plan accordingly.** Start complex queries, work on something else.

## Related Documents

- GPU tier: `intel-arc.md`
- Quantization guide: `quantization.md`
- Model selection: `../_selection-guide.md`
- Family docs: `../families/`
