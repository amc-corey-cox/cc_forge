---
id: kb-2026-012
title: "Quantization Guide for Local LLMs"
created: 2026-01-06
updated: 2026-01-06

author: human
curation_type: ai_assisted

sources:
  - id: src-001
    type: secondary
    title: "Local LLM Benchmarks 2025"
    url: "https://www.practicalwebtools.com/blog/local-llm-benchmarks-consumer-hardware-guide-2025"
    accessed: 2026-01-06
  - id: src-002
    type: tertiary
    title: "GGUF Quantization Types - llama.cpp"
    url: "https://github.com/ggerganov/llama.cpp/discussions/2948"
    accessed: 2026-01-06

topics:
  - models
  - models/local
  - quantization

confidence: medium
verified: true
verified_by: human
verification_date: 2026-01-06
verification_notes: "Based on llama.cpp documentation and community testing"

ai_metadata:
  model: claude-opus-4-5-20251101
  generation_date: 2026-01-06
  reviewed_by: human
  review_date: 2026-01-06
---

# Quantization Guide for Local LLMs

## Overview

Quantization reduces model precision to shrink file size and memory usage. A 7B model at FP16 (~14GB) becomes ~4GB at Q4_K_M—enabling it to run on consumer hardware.

**Tradeoff:** Smaller size = some quality loss. The key is finding the right balance.

## Understanding Quantization

### What It Does

Neural network weights are originally stored as 16-bit or 32-bit floating point numbers. Quantization converts these to lower precision:

| Precision | Bits per Weight | Relative Size |
|-----------|-----------------|---------------|
| FP16 | 16 | 100% (baseline) |
| Q8_0 | 8 | ~50% |
| Q6_K | 6 | ~38% |
| Q5_K_M | 5 | ~31% |
| Q4_K_M | 4 | ~25% |
| Q3_K_M | 3 | ~19% |
| Q2_K | 2 | ~13% |

### GGUF Format

Most local LLM tools use GGUF (GPT-Generated Unified Format), developed by llama.cpp. Quantization types follow this naming:

```
Q[bits]_[method]_[variant]

Q4_K_M = 4-bit, K-quant method, Medium variant
Q5_K_S = 5-bit, K-quant method, Small variant
Q8_0   = 8-bit, basic method
```

**K-quants** (Q4_K_M, Q5_K_M, etc.) are newer and generally better than basic quants (Q4_0, Q5_0).

## Quantization Levels Explained

### Q8_0 (8-bit)

- **Size:** ~50% of FP16
- **Quality:** ~98% of original
- **Use when:** Quality is critical, VRAM available

```
7B model: ~7GB
14B model: ~14GB
70B model: ~70GB
```

### Q6_K (6-bit)

- **Size:** ~38% of FP16
- **Quality:** ~95% of original
- **Use when:** Want high quality, slight space savings

### Q5_K_M (5-bit Medium)

- **Size:** ~31% of FP16
- **Quality:** ~93% of original
- **Use when:** Good balance for capable hardware

```
7B model: ~5GB
14B model: ~10GB
```

### Q4_K_M (4-bit Medium) ⭐ RECOMMENDED

- **Size:** ~25% of FP16
- **Quality:** ~90% of original
- **Use when:** Default choice for local deployment

```
7B model: ~4GB
14B model: ~7GB
32B model: ~18GB
70B model: ~40GB
```

**This is the sweet spot for most users.**

### Q3_K_M (3-bit Medium)

- **Size:** ~19% of FP16
- **Quality:** ~85% of original (noticeable degradation)
- **Use when:** Desperate for space, accept quality loss

### Q2_K (2-bit)

- **Size:** ~13% of FP16
- **Quality:** Poor (significant degradation)
- **Use when:** Experimental only, not recommended

## Quality Impact by Task

Quantization affects different tasks differently:

| Task | Q8_0 | Q4_K_M | Q3_K_M |
|------|------|--------|--------|
| General chat | Excellent | Good | Acceptable |
| Code generation | Excellent | Good | Noticeable errors |
| Math/reasoning | Excellent | Good | Degraded |
| Creative writing | Excellent | Good | Acceptable |
| Factual recall | Excellent | Slightly worse | Degraded |

**General pattern:** Precision-sensitive tasks (math, code) degrade more than creative tasks.

## Choosing the Right Quantization

### Decision Flowchart

```
Does Q4_K_M fit in your VRAM/RAM?
├── Yes → Use Q4_K_M (best balance)
│   └── Want better quality? → Try Q5_K_M or Q6_K
└── No →
    ├── Does Q3_K_M fit?
    │   ├── Yes → Accept quality loss or...
    │   └── Consider smaller model at Q4_K_M
    └── No → Model too large for your hardware
```

### CC Forge Hardware Recommendations

**Tier 1: Intel Arc (~8GB VRAM)**

| Model Size | Recommended Quant | Size |
|------------|-------------------|------|
| 7B | Q4_K_M or Q8_0 | 4-7GB |
| 8B | Q4_K_M | ~5GB |
| 14B | Q4_K_M only | ~7GB |

**Tier 2: CPU (64GB RAM)**

| Model Size | Recommended Quant | Size |
|------------|-------------------|------|
| 32B | Q4_K_M | ~18GB |
| 70B | Q4_K_M | ~40GB |
| 72B | Q4_K_M | ~42GB |

### Rule: Bigger Model at Q4 > Smaller Model at Q8

A key insight: **a larger model at lower quantization often outperforms a smaller model at higher quantization**.

Example:
- 7B at Q8_0 (~7GB) vs 14B at Q4_K_M (~7GB)
- The 14B Q4_K_M usually wins

**If you have the RAM, prefer larger models at Q4_K_M.**

## Ollama Quantization Tags

Ollama models include quantization in tags:

```bash
# Default (usually Q4_K_M)
ollama pull qwen2.5-coder:7b-instruct

# Specific quantization
ollama pull qwen2.5-coder:7b-instruct-q4_K_M
ollama pull qwen2.5-coder:7b-instruct-q8_0
ollama pull llama3.3:70b-instruct-q4_K_M
```

### Finding Available Quantizations

Check Ollama library page or:

```bash
# List available tags
ollama show qwen2.5-coder:7b-instruct --modelfile
```

## Comparing Quality

### Quick Test

Run the same prompts at different quantizations:

```bash
# Test at Q4_K_M
ollama run model:7b-q4_K_M "Explain quicksort in Python"

# Test at Q8_0
ollama run model:7b-q8_0 "Explain quicksort in Python"
```

Compare the outputs. For many tasks, you won't notice a difference.

### When to Upgrade Quantization

Consider higher quantization if:
- Getting wrong answers to factual questions
- Code has subtle bugs
- Math calculations are off
- And you have the VRAM/RAM headroom

## Size Estimation Formula

```
Approximate size = Parameters × Bits / 8

7B at 4-bit:  7 × 4 / 8 = 3.5GB
7B at 8-bit:  7 × 8 / 8 = 7GB
70B at 4-bit: 70 × 4 / 8 = 35GB
```

Actual sizes are slightly larger due to overhead, but this gives a good estimate.

## Common Pitfalls

### 1. Assuming Higher Bits Always Better

Q8_0 of a 7B model won't match Q4_K_M of a 70B model. Model size matters more than quantization within reasonable ranges.

### 2. Ignoring K-Quants

Q4_K_M is better than Q4_0. Always prefer K-quant variants when available.

### 3. Going Too Low

Q2_K and Q3_K produce noticeably worse results. Only use Q4_K_M or higher for production.

### 4. Not Testing

Quantization impact varies by model and task. Test on your actual use cases.

## Summary Table

| Quantization | Quality | Size Ratio | Recommendation |
|--------------|---------|------------|----------------|
| Q8_0 | Excellent | 50% | When quality critical |
| Q6_K | Very Good | 38% | High quality with savings |
| Q5_K_M | Good | 31% | Good balance |
| **Q4_K_M** | Good | 25% | **Default choice** |
| Q3_K_M | Acceptable | 19% | Only if necessary |
| Q2_K | Poor | 13% | Avoid |

## Related Documents

- Intel Arc guide: `intel-arc.md`
- CPU tier guide: `cpu-tier.md`
- Model selection: `../_selection-guide.md`
