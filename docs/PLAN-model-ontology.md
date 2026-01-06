# Plan: Knowledge Base Model Ontology

**Branch:** `claude/kb-model-ontology-<session-suffix>`
**Goal:** Build a comprehensive model ontology in the knowledge base that enables informed model selection for CC Forge agents.

---

## Overview

This plan takes us from the current state (basic KB structure, one AI ontology reference doc) to having a working model ontology that:
1. Maps the landscape of available models
2. Captures lineage/relationships between models
3. Categorizes by capability (coding, reasoning, prose, etc.)
4. Maps to local hardware constraints (Intel Arc GPU, CPU tiers)
5. Provides actionable guidance for model selection

---

## Phase 1: Foundation Setup

### 1.1 Create Directory Structure
```
knowledge/
├── topics/
│   └── models/                    # NEW - Model ontology lives here
│       ├── _ontology.md           # The ontology structure itself
│       ├── _selection-guide.md    # How to use the ontology for decisions
│       ├── families/              # Model lineage documentation
│       │   ├── llama.md
│       │   ├── mistral.md
│       │   ├── qwen.md
│       │   └── ...
│       ├── capabilities/          # Capability-focused views
│       │   ├── coding.md
│       │   ├── reasoning.md
│       │   ├── embedding.md
│       │   └── ...
│       └── local/                 # Local deployment considerations
│           ├── intel-arc.md       # What runs on our GPU
│           ├── cpu-tier.md        # What runs on CPU (70B quantized)
│           └── quantization.md    # Quantization tradeoffs
```

### 1.2 Define Model Entry Schema
Extend the KB schema template for model-specific entries:
- Base model / parent relationship
- Parameter count and variants
- Quantization options available
- Context length
- Capability tags (from controlled vocabulary)
- Hardware requirements (VRAM, RAM)
- Ollama availability
- Benchmark references (if available)

**Deliverable:** `knowledge/schema/model-entry.md` - Template for model documentation

---

## Phase 2: Ontology Design

### 2.1 Define the Ontology Structure
Create `knowledge/topics/models/_ontology.md` with:

**Capability Hierarchy:**
```
Capabilities
├── Text Generation
│   ├── Code Generation
│   │   ├── General Purpose
│   │   ├── Infill/Completion
│   │   └── Language-Specific (considerations, not separate models)
│   ├── Reasoning
│   │   ├── Chain-of-Thought
│   │   ├── Mathematical
│   │   └── Logical
│   ├── Prose/Creative
│   │   ├── Long-form
│   │   └── Conversational
│   └── Instruction Following
│       ├── Chat/Assistant
│       └── Task Completion
├── Embedding/Retrieval
│   ├── Text Embedding
│   └── Code Embedding
└── Multimodal (future)
    ├── Vision-Language
    └── Audio (out of scope for now)
```

**Lineage Structure:**
```
Model Families
├── Meta/Llama Family
│   ├── Llama 2 → Llama 3 → Llama 3.1 → Llama 3.2 → Llama 3.3
│   └── Code Llama (branched from Llama 2)
├── Mistral Family
│   ├── Mistral 7B → Mistral Nemo → Mistral Small/Large
│   └── Codestral (code-focused branch)
├── Qwen Family
│   ├── Qwen → Qwen 1.5 → Qwen 2 → Qwen 2.5
│   ├── CodeQwen
│   └── QwQ (reasoning-focused)
├── DeepSeek Family
│   ├── DeepSeek → DeepSeek V2 → DeepSeek V3
│   ├── DeepSeek-Coder
│   └── DeepSeek-R1 (reasoning)
└── ... (other families as relevant)
```

**Hardware Tier Mapping:**
```
CC Forge Hardware Tiers (from DESIGN.md)
├── Tier 1: Intel Arc GPU (limited VRAM)
│   └── Models that fit: 7B-14B at Q4-Q8
├── Tier 2: System CPU/RAM
│   └── Models: Up to 70B at Q4 (slow but capable)
└── Tier 3: External API
    └── When local insufficient
```

### 2.2 Define Controlled Vocabularies
Create `knowledge/schema/model-vocabularies.md`:
- Capability tags (coding, reasoning, chat, embedding, etc.)
- Size categories (small: <10B, medium: 10-30B, large: 30-70B, xl: >70B)
- Quantization levels (Q4_K_M, Q5_K_M, Q8_0, FP16, etc.)
- License types (open, restricted, commercial)

**Deliverable:** Ontology structure document + controlled vocabularies

---

## Phase 3: Research & Survey

### 3.1 Survey Ollama Library
Research what's actually available in Ollama:
- List all models relevant to our use cases
- Note parameter sizes and quantization options
- Check which are actively maintained

### 3.2 Research Model Lineages
For each major family:
- Document the lineage/evolution
- Note key differences between versions
- Identify which variants are best for what

### 3.3 Gather Capability Data
For coding, reasoning, and general assistant use:
- Find benchmark comparisons (HumanEval, MBPP, GSM8K, etc.)
- Note real-world observations from community
- Document known strengths/weaknesses

### 3.4 Local Hardware Testing (References)
- Document Intel Arc specific considerations (IPEX-LLM quirks)
- Note what's been tested in our setup (reference existing docs/LOCAL-OLLAMA-SETUP.md)
- Identify gaps to test

**Deliverable:** Research notes (can go in `knowledge/pending/` initially)

---

## Phase 4: Content Creation

### 4.1 Write Model Family Documents
For each major family (prioritized):
1. **Qwen Family** - Strong coding, reasoning, active development
2. **DeepSeek Family** - Excellent coding, reasoning models
3. **Llama Family** - Ubiquitous, good baseline
4. **Mistral Family** - Codestral for coding
5. **Others as relevant**

Each document includes:
- History and lineage
- Key models and their focus
- Recommended variants for different uses
- Local deployment notes

### 4.2 Write Capability Documents
For each major capability:
1. **Coding Models** - Comparison of options, recommendations by use case
2. **Reasoning Models** - Chain-of-thought, mathematical reasoning
3. **Embedding Models** - For RAG/retrieval (important for KB itself)

### 4.3 Write Local Deployment Guides
1. **Intel Arc Guide** - What works, what doesn't, performance expectations
2. **CPU Tier Guide** - Running large models on CPU, tradeoffs
3. **Quantization Guide** - When to use Q4 vs Q8, quality impact

### 4.4 Write Selection Guide
`_selection-guide.md` - Decision framework:
- "I need a coding model" → here are your options by tier
- "I need reasoning" → here are your options
- "I need to run locally on Arc" → here's what fits

**Deliverable:** Complete model knowledge base section

---

## Phase 5: Integration & Validation

### 5.1 Cross-Reference with Agent Frameworks
- How does model selection affect framework choice?
- Document which frameworks work well with which models
- Note any framework-specific model requirements

### 5.2 Create Model Selection Checklist
Practical checklist for choosing a model:
- [ ] What's the primary task? (coding/reasoning/chat)
- [ ] What tier can we use? (GPU/CPU/API)
- [ ] What context length needed?
- [ ] Speed vs quality tradeoff?
- [ ] License restrictions?

### 5.3 Validate with Test Runs
- Pick a few candidate models
- Run through IPEX-LLM on Intel Arc
- Document actual performance

**Deliverable:** Validated, actionable model selection framework

---

## Completion Criteria

The work is complete when:

1. **Structure exists:** `knowledge/topics/models/` directory with ontology
2. **Ontology documented:** `_ontology.md` with capability hierarchy and lineage structure
3. **Major families covered:** At least 4 model families documented (Qwen, DeepSeek, Llama, Mistral)
4. **Capabilities documented:** Coding, reasoning, and embedding capability docs
5. **Local guides exist:** Intel Arc, CPU tier, and quantization guides
6. **Selection guide works:** Can answer "what model for X on Y hardware?"
7. **Provenance maintained:** All entries follow KB schema with proper sources
8. **Ready for evaluation:** Have enough info to start actual model testing/selection

---

## Estimated Effort

| Phase | Scope |
|-------|-------|
| Phase 1 | Directory setup, schema extension |
| Phase 2 | Ontology design, vocabularies |
| Phase 3 | Research (web searches, doc reading) |
| Phase 4 | Content writing (bulk of work) |
| Phase 5 | Integration, validation |

---

## Dependencies & Risks

**Dependencies:**
- Access to model documentation (Hugging Face, Ollama, official repos)
- Existing LOCAL-OLLAMA-SETUP.md for hardware baseline

**Risks:**
- Model landscape changes fast - entries may need updates
- Some performance claims hard to verify without testing
- Quantization quality varies by model - may need empirical testing

**Mitigations:**
- Use `updated` field in schema to track freshness
- Mark uncertain claims with `confidence: medium/low`
- Link to `knowledge/pending/` for claims needing verification

---

## Open Questions for User

1. **Scope of families:** Focus on the 4-5 most relevant, or comprehensive coverage?
2. **Depth vs breadth:** Deep dives on few models, or lighter coverage of many?
3. **Testing priority:** Should we include actual benchmark runs in this phase, or defer?
4. **Multimodal:** Include vision models now, or defer to later?

---

*Plan created: 2026-01-06*
*Status: Awaiting approval*
