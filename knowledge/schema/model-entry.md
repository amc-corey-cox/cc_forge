---
# Model Entry Schema - Extended from TEMPLATE.md
# Use this template for individual model or model family documentation

id: kb-YYYY-NNN
title: "Model/Family Name"
created: YYYY-MM-DD
updated: YYYY-MM-DD

author: human
curation_type: ai_assisted  # human_curated | ai_assisted | ai_generated | ai_unverified

# Model-Specific Metadata
model_info:
  type: family  # family | model | variant
  family: ""  # Parent family (e.g., "llama", "qwen", "mistral")
  base_model: ""  # For variants/finetunes, the parent model
  developer: ""  # Organization (Meta, Alibaba, Mistral AI, DeepSeek, etc.)
  license: ""  # apache-2.0, llama3, mit, proprietary, etc.
  release_date: YYYY-MM-DD

  # Size and Variants (for families, list available; for models, specify)
  parameter_sizes: []  # e.g., [7B, 13B, 70B]
  context_lengths: []  # e.g., [4096, 8192, 32768, 128000]

  # Capabilities (from controlled vocabulary)
  primary_capabilities: []  # Primary strengths
  secondary_capabilities: []  # Additional capabilities

  # Local Deployment
  ollama_available: false  # Is it in Ollama library?
  ollama_tags: []  # Available Ollama tags (e.g., ["7b", "7b-q4_K_M", "70b"])
  recommended_quantization: ""  # For local use

  # Hardware Requirements (estimates)
  hardware:
    min_vram_gb: null  # Minimum VRAM for smallest quantized variant
    recommended_vram_gb: null  # For good performance
    cpu_viable: false  # Can run reasonably on CPU?
    cpu_ram_gb: null  # RAM needed for CPU inference

sources:
  - id: src-001
    type: primary
    title: "Official Documentation/Paper"
    url: ""
    accessed: YYYY-MM-DD

topics:
  - models
  # Add capability topics: coding, reasoning, chat, embedding, etc.

confidence: medium
verified: false
verified_by: unverified
verification_date: YYYY-MM-DD
verification_notes: ""

# For AI-assisted entries
ai_metadata:
  model: ""
  generation_date: YYYY-MM-DD
  reviewed_by: human
  review_date: YYYY-MM-DD
---

# Model/Family Name

## Overview

Brief description of the model/family, its origins, and significance.

## Lineage

```
Parent Model
└── This Model
    ├── Variant A
    └── Variant B
```

(Or for families, show the evolution timeline)

## Key Characteristics

### Strengths
- Strength 1 [src-001]
- Strength 2

### Limitations
- Limitation 1
- Limitation 2

### Notable Features
- Feature 1
- Feature 2

## Available Variants

| Variant | Parameters | Context | Best For |
|---------|------------|---------|----------|
| variant-7b | 7B | 8K | General use |
| variant-7b-instruct | 7B | 8K | Chat/instruction |

## Local Deployment

### Ollama
```bash
ollama pull model-name:tag
```

### Hardware Considerations
- **Intel Arc (8GB VRAM):** [Can/Cannot run, which variants]
- **CPU Tier:** [Viable? Which quantization?]

### Quantization Notes
- Q4_K_M: [Quality/speed tradeoff notes]
- Q8_0: [Quality/speed tradeoff notes]

## Real-World Performance

### Community Reports
- Report 1: [Summary of real-world usage experience]
- Report 2: [Another data point]

### Local Testing Notes
(To be filled in after local testing)

## Relevance to CC Forge

Why this model matters for our use cases:
- Use case 1
- Use case 2

## Further Reading

- [Link 1](url)
- [Link 2](url)
