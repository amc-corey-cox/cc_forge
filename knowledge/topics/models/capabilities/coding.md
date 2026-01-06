---
id: kb-2026-007
title: "Coding Models Comparison"
created: 2026-01-06
updated: 2026-01-06

author: human
curation_type: ai_assisted

sources:
  - id: src-001
    type: secondary
    title: "5 Open-Source Coding LLMs You Can Run Locally in 2025"
    url: "https://www.labellerr.com/blog/best-coding-llms/"
    accessed: 2026-01-06
  - id: src-002
    type: secondary
    title: "Aider LLM Leaderboard"
    url: "https://aider.chat/docs/leaderboards/"
    accessed: 2026-01-06
  - id: src-003
    type: secondary
    title: "Qwen2.5-Coder-32B Review - Simon Willison"
    url: "https://simonw.substack.com/p/qwen25-coder-32b-is-an-llm-that-can"
    accessed: 2026-01-06

topics:
  - models
  - models/capability/coding
  - code-generation

confidence: high
verified: true
verified_by: human
verification_date: 2026-01-06
verification_notes: "Synthesized from multiple sources and benchmarks"

ai_metadata:
  model: claude-opus-4-5-20251101
  generation_date: 2026-01-06
  reviewed_by: human
  review_date: 2026-01-06
---

# Coding Models Comparison

## Overview

Code generation is one of the most practical applications of local LLMs. This document compares models specifically optimized for coding tasks, focusing on what's viable for local deployment.

## Task Breakdown

"Coding" includes several distinct tasks:

| Task | Description | Best Approach |
|------|-------------|---------------|
| Code Generation | Writing new code from description | Instruct models |
| Code Completion | FIM (Fill-in-Middle) autocomplete | FIM-capable models |
| Code Review | Analyzing existing code | Any capable model |
| Debugging | Finding and fixing bugs | Strong reasoning + coding |
| Refactoring | Restructuring code | Strong instruct models |
| Documentation | Writing docs/comments | General models work |

## Model Comparison

### By Benchmark Performance

| Model | HumanEval | MBPP | Aider Score | Notes |
|-------|-----------|------|-------------|-------|
| Qwen2.5-Coder-32B | 92.7% | - | 74% | Best open-source |
| Qwen2.5-Coder-14B | - | - | 69% | Good mid-size |
| Qwen2.5-Coder-7B | - | - | 58% | Best at 7B tier |
| DeepSeek-Coder-V2-16B | 90.2% | 76.2% | 73.7% | MoE architecture |
| Codestral 22B | 86.6% | - | - | 256K context |
| Llama 3.3 70B | - | - | ~60% | General, not specialized |

### By Size Tier

**Tier 1: Small (≤8B) - Fits on 8GB VRAM**

| Model | Params | Aider | Best For |
|-------|--------|-------|----------|
| **Qwen2.5-Coder-7B** | 7B | 58% | Best overall at this tier |
| DeepSeek-Coder-V2-Lite | 16B (2.4B active) | - | If MoE fits |
| Code Llama 7B | 7B | <50% | Legacy, use Qwen instead |

**Recommendation:** Qwen2.5-Coder-7B-Instruct is the clear winner at this tier.

**Tier 2: Medium (10-35B) - GPU or CPU**

| Model | Params | Aider | Best For |
|-------|--------|-------|----------|
| **Qwen2.5-Coder-32B** | 32B | 74% | Best open-source coding |
| Codestral 22B | 22B | - | FIM, large context |
| DeepSeek-Coder-33B | 33B | - | Alternative to Qwen |

**Recommendation:** Qwen2.5-Coder-32B if you can run it; Codestral if you need FIM or 256K context.

**Tier 3: Large (70B+) - CPU only for most**

| Model | Params | Notes |
|-------|--------|-------|
| DeepSeek-Coder-V2 236B | 236B (21B active) | Needs serious hardware |
| Llama 3.3 70B | 70B | General, decent at code |

## Feature Comparison

| Model | FIM | Context | Languages | License |
|-------|-----|---------|-----------|---------|
| Qwen2.5-Coder-7B | Yes | 128K | 80+ | Apache 2.0 |
| Qwen2.5-Coder-32B | Yes | 128K | 80+ | Apache 2.0 |
| Codestral 22B | Yes | 256K | 80+ | Restricted |
| DeepSeek-Coder-V2 | Yes | 128K | 338 | DeepSeek License |
| Llama 3.3 70B | No | 128K | General | Llama License |

### Fill-in-Middle (FIM) Support

FIM is crucial for IDE-style code completion. Models with native FIM:

- **Qwen2.5-Coder** - Full FIM support
- **Codestral** - Excellent FIM
- **DeepSeek-Coder** - FIM support
- **Mistral 7B** - Basic FIM

## Real-World Performance

### Qwen2.5-Coder-32B

"Answered real coding questions as effectively as Perplexity" [src-003]

"On M2 Mac 64GB: 95 tokens/sec prompt processing, 10 tokens/sec generation" [src-003]

Community consensus: Currently the best open-source coding model.

### Qwen2.5-Coder-7B

Best-in-class at the 7B tier. Outperforms models 2-3x its size on coding tasks.

### DeepSeek-Coder-V2

"Coding performance improved by roughly 20% and cut documentation searches by 40%" in production use.

MoE architecture means faster inference than parameter count suggests.

### Codestral

Excels at: Scaffolding, test generation, refactoring

Struggles with: Multi-file coordination [src-001]

The 256K context is genuinely useful for large codebases.

## CC Forge Recommendations

### Primary Coding Model: Qwen2.5-Coder-7B

```bash
ollama pull qwen2.5-coder:7b-instruct
```

**Why:**
- Fits on Intel Arc 8GB at Q8_0
- Best performance at this size
- Good FIM support
- Apache 2.0 license
- Active development

### Fallback for Complex Tasks: Qwen2.5-Coder-32B

```bash
ollama pull qwen2.5-coder:32b-instruct-q4_K_M
```

**Use when:**
- 7B model produces incorrect code
- Task requires architectural decisions
- Complex refactoring needed

### IDE Completion: Qwen2.5-Coder-7B or Codestral

Both support FIM. Qwen is more accessible; Codestral has larger context.

## Prompt Engineering for Code

### Generation Prompt

```
You are an expert programmer. Write clean, well-documented code.

Task: [description]

Requirements:
- Use [language]
- Follow [style guide]
- Include error handling

Respond with only the code, no explanations.
```

### Review Prompt

```
Review this code for:
1. Bugs and potential issues
2. Performance problems
3. Security vulnerabilities
4. Style improvements

Code:
```[code]```

Provide specific, actionable feedback.
```

### Refactoring Prompt

```
Refactor this code to:
- [specific goal]
- Maintain the same functionality
- Add tests if appropriate

Current code:
```[code]```
```

## When to Use Which

| Scenario | Model | Why |
|----------|-------|-----|
| Day-to-day coding | Qwen2.5-Coder-7B | Fast, capable |
| Complex architecture | Qwen2.5-Coder-32B | Better reasoning |
| Large codebase | Codestral | 256K context |
| IDE autocomplete | Qwen2.5-Coder-7B | FIM, speed |
| Code review | Any strong model | Understanding > generation |

## Benchmark Caveats

Benchmarks (HumanEval, MBPP, Aider) measure specific skills:
- HumanEval: Algorithmic problem-solving
- MBPP: Python basics
- Aider: Real-world editing tasks

Real coding involves more:
- Understanding existing code
- Working with frameworks
- Debugging production issues
- Writing maintainable code

Benchmark winners don't always win at real tasks. **Local testing matters.**

## Related Documents

- Family details: `../families/qwen.md`, `../families/deepseek.md`, `../families/mistral.md`
- Local deployment: `../local/intel-arc.md`
- Selection guide: `../_selection-guide.md`
