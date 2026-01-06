# Model Ontology Controlled Vocabularies

This document defines the controlled vocabularies used in model documentation.
Use these exact terms for consistency and queryability.

---

## Capability Tags

### Primary Capabilities
Use these for `primary_capabilities` field:

| Tag | Description |
|-----|-------------|
| `code-generation` | Writing code from prompts/instructions |
| `code-completion` | Infill, autocomplete, FIM (fill-in-middle) |
| `code-reasoning` | Understanding and explaining code |
| `reasoning` | General logical/analytical reasoning |
| `reasoning-cot` | Chain-of-thought / step-by-step reasoning |
| `reasoning-math` | Mathematical problem solving |
| `chat` | Conversational assistant |
| `instruction-following` | Following complex multi-step instructions |
| `long-context` | Optimized for long document processing |
| `embedding-text` | Text embedding generation |
| `embedding-code` | Code embedding generation |
| `creative-writing` | Prose, stories, creative content |
| `summarization` | Document/text summarization |
| `translation` | Language translation |
| `image-generation` | Text-to-image generation |
| `image-understanding` | Vision/image analysis |

### Secondary Capabilities
Same tags, but indicates "can do" vs "optimized for"

---

## Model Types

| Type | Description |
|------|-------------|
| `family` | A lineage of related models (e.g., "Llama") |
| `base` | Pre-trained model, not instruction-tuned |
| `instruct` | Instruction-tuned variant |
| `chat` | Chat/conversation optimized |
| `code` | Code-specialized variant |
| `reasoning` | Reasoning-optimized (e.g., QwQ, R1) |
| `embedding` | Embedding model |
| `finetune` | Community/third-party finetune |

---

## Size Categories

| Category | Parameter Range | Typical Use |
|----------|-----------------|-------------|
| `tiny` | < 3B | Edge devices, fast inference |
| `small` | 3B - 9B | Local GPU, good balance |
| `medium` | 10B - 30B | High-end local GPU |
| `large` | 30B - 70B | Multi-GPU or CPU offload |
| `xl` | > 70B | Server-class or API |

---

## Quantization Levels

Common quantization formats (GGUF/llama.cpp convention):

| Format | Bits | Quality | Size Reduction | Notes |
|--------|------|---------|----------------|-------|
| `FP16` | 16 | Highest | None | Full precision |
| `Q8_0` | 8 | Very High | ~50% | Minimal quality loss |
| `Q6_K` | 6 | High | ~60% | Good quality/size balance |
| `Q5_K_M` | 5 | Good | ~65% | Popular choice |
| `Q4_K_M` | 4 | Acceptable | ~75% | Best for VRAM-limited |
| `Q4_0` | 4 | Lower | ~75% | Older format |
| `Q3_K_M` | 3 | Degraded | ~80% | Last resort |
| `Q2_K` | 2 | Poor | ~85% | Experimental only |

### Quantization Selection Guide
- **Quality critical:** Q8_0 or Q6_K
- **Balanced (recommended):** Q5_K_M or Q4_K_M
- **VRAM constrained:** Q4_K_M
- **CPU inference:** Q4_K_M (speed) or Q5_K_M (quality)

---

## License Types

| License | Commercial Use | Modification | Notes |
|---------|---------------|--------------|-------|
| `apache-2.0` | Yes | Yes | Permissive |
| `mit` | Yes | Yes | Permissive |
| `llama3` | Yes* | Yes | Meta's license, some restrictions |
| `llama3.1` | Yes* | Yes | Updated Meta license |
| `qwen` | Yes | Yes | Alibaba's license |
| `gemma` | Yes* | Yes | Google's license |
| `deepseek` | Yes | Yes | DeepSeek license |
| `cc-by-nc-4.0` | No | Yes | Non-commercial only |
| `proprietary` | Varies | No | Check specific terms |

*Check specific license for usage restrictions (e.g., user count limits)

---

## Hardware Tiers (CC Forge Specific)

From DESIGN.md, our hardware strategy:

| Tier | Hardware | Capacity | Speed | Use For |
|------|----------|----------|-------|---------|
| `tier-1-gpu` | Intel Arc (8GB VRAM) | 7B-14B Q4-Q8 | Fast | Primary inference |
| `tier-2-cpu` | System RAM (64GB+) | Up to 70B Q4 | Slow | Complex tasks |
| `tier-3-api` | External API | Unlimited | Variable | When local insufficient |

---

## Model Families (Top-Level)

Current families tracked in ontology:

| Family | Developer | Primary Focus |
|--------|-----------|---------------|
| `llama` | Meta | General purpose |
| `qwen` | Alibaba | General + coding |
| `mistral` | Mistral AI | Efficiency |
| `deepseek` | DeepSeek | Coding + reasoning |
| `phi` | Microsoft | Small + efficient |
| `gemma` | Google | Open research |
| `stable-diffusion` | Stability AI | Image generation |

---

## Topic Tags

Standard topics for model entries:

- `models` (always include)
- `models/family/{family-name}` (e.g., `models/family/llama`)
- `models/capability/{capability}` (e.g., `models/capability/coding`)
- `models/local` (for local deployment focused)
- `models/image-generation` (for image models)

---

*Last updated: 2026-01-06*
