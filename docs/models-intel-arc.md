---
id: kb-2026-010
title: "Intel Arc GPU Model Deployment"
created: 2026-01-06
updated: 2026-01-06

author: human
curation_type: ai_assisted

sources:
  - id: src-001
    type: primary
    title: "CC Forge Local Ollama Setup"
    url: "file:///docs/LOCAL-OLLAMA-SETUP.md"
    accessed: 2026-01-06
    notes: "Internal CC Forge documentation"
  - id: src-002
    type: primary
    title: "IPEX-LLM GitHub"
    url: "https://github.com/intel/ipex-llm"
    accessed: 2026-01-06

topics:
  - models
  - models/local
  - intel-arc
  - ipex-llm

confidence: high
verified: true
verified_by: human
verification_date: 2026-01-06
verification_notes: "Based on actual CC Forge hardware testing"

ai_metadata:
  model: claude-opus-4-5-20251101
  generation_date: 2026-01-06
  reviewed_by: human
  review_date: 2026-01-06
---

# Intel Arc GPU Model Deployment

## Overview

This guide covers deploying LLMs on Intel Arc GPUs using IPEX-LLM. Intel Arc is CC Forge's Tier 1 hardware for fast local inference.

**Key constraint:** ~8GB VRAM limits models to approximately 7B-14B parameters depending on quantization.

**Full setup instructions:** See `/docs/LOCAL-OLLAMA-SETUP.md`

## Hardware Tier 1 Capability

| Aspect | Specification |
|--------|---------------|
| GPU | Intel Arc (A-series) |
| VRAM | ~8GB (varies by model) |
| Backend | IPEX-LLM via SYCL/Level Zero |
| Port | 11434 (Ollama default) |

### Performance Benchmarks (from CC Forge testing)

Using `llama3.1:latest` (4.7GB):

| Backend | Prompt Eval | Generation |
|---------|-------------|------------|
| IPEX GPU | 147.6 tok/s | 39.0 tok/s |
| CPU | 47.6 tok/s | 18.1 tok/s |

**IPEX advantage:** ~3x faster prompt processing, ~2x faster generation.

## What Fits on 8GB VRAM

### General Rule

```
VRAM needed ≈ Parameters × Bits / 8

7B × 4-bit / 8 = ~3.5GB
7B × 8-bit / 8 = ~7GB
14B × 4-bit / 8 = ~7GB
14B × 8-bit / 8 = ~14GB (won't fit)
```

### Verified Compatible Models

| Model | Size | Quantization | VRAM | Status |
|-------|------|--------------|------|--------|
| Qwen2.5-Coder-7B | 4.5GB | Q4_K_M | ~4.5GB | ✅ Fast |
| Qwen2.5-7B | 4.7GB | Q4_K_M | ~4.7GB | ✅ Fast |
| Llama-3.1-8B | 4.7GB | Q4_K_M | ~4.7GB | ✅ Fast |
| Llama-3.2-3B | 2GB | Q8_0 | ~2GB | ✅ Very fast |
| DeepSeek-R1-Distill-7B | 4.7GB | Q4_K_M | ~4.7GB | ✅ Fast |
| Mistral-7B | 4.1GB | Q4_K_M | ~4.1GB | ✅ Fast |
| nomic-embed-text | 0.5GB | Default | ~1GB | ✅ Very fast |

### Borderline (May Fit)

| Model | Size | Quantization | VRAM | Notes |
|-------|------|--------------|------|-------|
| Qwen2.5-Coder-7B | 7.6GB | Q8_0 | ~7.6GB | Tight fit |
| Llama-3.1-8B | 8.5GB | Q8_0 | ~8.5GB | May swap |
| DeepSeek-Coder-V2-Lite | ~8GB | Q4_K_M | ~8GB | MoE, test first |

### Won't Fit (Use CPU)

| Model | Size | Why |
|-------|------|-----|
| Qwen2.5-Coder-32B | 18GB+ | Too large |
| QwQ-32B | 18GB+ | Too large |
| Llama-3.3-70B | 42GB+ | Way too large |
| DeepSeek-R1-32B | 18GB+ | Too large |

## Recommended Models for Intel Arc

### Coding: Qwen2.5-Coder-7B

```bash
ollama pull qwen2.5-coder:7b-instruct-q4_K_M
```

Best coding model that fits. Use Q4_K_M for headroom or Q8_0 for max quality (tight fit).

### Reasoning: DeepSeek-R1-Distill-7B

```bash
ollama pull deepseek-r1:7b
```

Chain-of-thought reasoning in a 7B package.

### General: Llama-3.1-8B or Qwen2.5-7B

```bash
ollama pull llama3.1:8b-instruct-q4_K_M
ollama pull qwen2.5:7b-instruct-q4_K_M
```

Solid general-purpose options.

### Embedding: nomic-embed-text

```bash
ollama pull nomic-embed-text
```

Fast even on CPU, trivial on GPU.

## Service Configuration

CC Forge uses multiple Ollama services for different scenarios:

| Service | Use When |
|---------|----------|
| `ollama-ipex` | Models ≤8GB, want speed |
| `ollama-cpu` | Models >8GB, fallback |
| `ollama-vulkan` | IPEX issues, need GPU |

### Switching Services

```bash
# Switch to IPEX (GPU acceleration)
sudo systemctl disable --now ollama-cpu ollama-vulkan
sudo systemctl enable --now ollama-ipex

# Switch to CPU (for large models)
sudo systemctl disable --now ollama-ipex ollama-vulkan
sudo systemctl enable --now ollama-cpu

# Check active service
systemctl is-active ollama-cpu ollama-ipex ollama-vulkan
```

## Usage Patterns

### Workflow for Mixed Model Sizes

1. **Default:** Keep `ollama-cpu` enabled (works with everything)
2. **Performance session:** Switch to `ollama-ipex` when using 7B models
3. **Complex task:** Switch to `ollama-cpu` when you need 32B/70B

### Practical Example

```bash
# Morning: General coding with GPU acceleration
sudo systemctl enable --now ollama-ipex
ollama run qwen2.5-coder:7b-instruct

# Afternoon: Need complex reasoning
sudo systemctl enable --now ollama-cpu
ollama run qwq:32b-q4_K_M  # Runs on CPU, slow but works

# Evening: Back to fast coding
sudo systemctl enable --now ollama-ipex
```

## Limitations

### No CPU+GPU Split

Intel Arc + IPEX-LLM doesn't reliably support partial offloading (running part of model on GPU, part on CPU). Models either fit entirely on GPU or should run entirely on CPU.

### Manual Service Switching

Currently requires manual switching between services. See CC Forge Issue #1 for future proxy solution.

### Memory Pressure

When VRAM is full:
- Performance degrades significantly
- May cause crashes or garbled output
- Solution: Use smaller quantization or switch to CPU

## Troubleshooting

### Model loads but runs slowly

Check which service is active:
```bash
systemctl is-active ollama-ipex ollama-cpu
```

If `ollama-cpu` is active, switch to `ollama-ipex` for GPU.

### Out of memory errors

Model too large for VRAM. Options:
1. Use smaller quantization (Q4_K_M instead of Q8_0)
2. Switch to smaller model
3. Use CPU service for this model

### Garbled output

Sometimes indicates memory issues. Try:
1. Restart the Ollama service
2. Use smaller quantization
3. Switch to CPU service

### IPEX service won't start

Check logs:
```bash
journalctl -u ollama-ipex -f
```

Common issues:
- Level Zero not installed (see `/docs/LOCAL-OLLAMA-SETUP.md`)
- Permission errors (check `/opt/ipex-llm` ownership)

## Related Documents

- Full setup guide: `LOCAL-OLLAMA-SETUP.md`
- CPU tier guide: `models-cpu-tier.md`
- Quantization guide: `models-quantization.md`
- Model selection: `/knowledge/topics/models/_selection-guide.md`
