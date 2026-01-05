---
id: kb-2025-003
title: "AI Model Ontologies and Metadata Standards"
created: 2025-01-02
updated: 2025-01-02

author: human
curation_type: ai_assisted

sources:
  - id: src-001
    type: primary
    title: "Artificial Intelligence Ontology (AIO) GitHub Repository"
    authors: ["Berkeley BOP"]
    url: "https://github.com/berkeleybop/artificial-intelligence-ontology"
    accessed: 2025-01-02
    quotes:
      - text: "An ontology modeling classes and relationships describing deep learning networks, their component layers and activation functions, machine learning methods, as well as AI/ML potential biases."
        location: "Repository description"

  - id: src-002
    type: primary
    title: "The Artificial Intelligence Ontology: LLM-assisted construction of AI concept hierarchies"
    authors: ["Joachimiak et al."]
    url: "https://arxiv.org/abs/2404.03044"
    arxiv: "2404.03044"
    accessed: 2025-01-02
    published: 2024-04-03

  - id: src-003
    type: primary
    title: "Hugging Face Model Cards Documentation"
    url: "https://huggingface.co/docs/hub/en/model-cards"
    accessed: 2025-01-02
    quotes:
      - text: "Model cards are files that accompany the models and provide handy information... essential for discoverability, reproducibility, and sharing"
        location: "Introduction"

  - id: src-004
    type: primary
    title: "MLCommons Croissant Metadata Format Announcement"
    url: "https://mlcommons.org/2024/03/croissant_metadata_announce/"
    accessed: 2025-01-02
    published: 2024-03-06

topics:
  - ontology
  - model-metadata
  - standards
  - ai-fundamentals

confidence: high
verified: true
verified_by: human
verification_date: 2025-01-02
verification_notes: "Sources directly reviewed; quotes verified"

ai_metadata:
  model: claude-opus-4-5-20251101
  generation_date: 2025-01-02
  reviewed_by: human
  review_date: 2025-01-02
---

# AI Model Ontologies and Metadata Standards

## Overview

Several standards exist for describing AI/ML models. Rather than creating our own ontology, CC Forge adopts and references these established standards.

## Standards Landscape

### Artificial Intelligence Ontology (AIO)

**What**: A formal OWL ontology for AI concepts, developed by Berkeley BOP with LLM assistance [src-001, src-002].

**Structure**: Eight main branches:
- Bias (ethical considerations)
- Layer (neural network components)
- Machine Learning Task
- Mathematical Function
- Model
- Network
- Preprocessing
- Training Strategy

**Use in CC Forge**: Reference for formal AI concept definitions in knowledge base entries.

**Links**:
- [GitHub Repository](https://github.com/berkeleybop/artificial-intelligence-ontology)
- [arXiv Paper](https://arxiv.org/abs/2404.03044)
- Available in OBO, OWL, and JSON formats

### Hugging Face Model Cards

**What**: A practical YAML metadata schema for model documentation [src-003]. Industry standard, widely adopted.

**Key Fields**:
```yaml
language: [list of ISO 639-1 codes]
license: "license identifier"
library_name: "transformers, etc."
pipeline_tag: "text-generation, etc."
tags: [custom tags]
datasets: [training datasets]
base_model: "parent model identifier"
model-index: [evaluation results]
```

**Use in CC Forge**: Basis for our model registry schema. Compatible with ecosystem tooling.

### MLCommons Croissant

**What**: Metadata format for ML datasets, not models [src-004]. Supported by Kaggle, Hugging Face, OpenML.

**Use in CC Forge**: Reference for dataset documentation if we track training data sources.

### SML (Semantic ML Model Ontology)

**What**: Academic ontology for ML model characteristics and specifications.

**Use in CC Forge**: Additional reference for formal model descriptions.

## CC Forge Approach

We do NOT create a new ontology. Instead:

1. **Reference AIO** for formal concept definitions
2. **Adopt HF Model Card conventions** for practical metadata
3. **Extend with local-specific fields** for our hardware/use case

See `knowledge/schema/model-registry.schema.json` for our local model tracking schema.

## Relevance to CC Forge

Understanding these standards is essential because:
- Agents need consistent vocabulary for discussing models
- Model selection logic requires structured capability descriptions
- Knowledge base entries about models should use standard terminology
- Interoperability with broader ecosystem (Ollama, HF, etc.)

## Further Reading

- [AIO on BioPortal](https://bioportal.bioontology.org/ontologies/AIO)
- [Hugging Face Model Card Guidebook](https://huggingface.co/docs/hub/en/model-card-guidebook)
- [Papers with Code Model Index Spec](https://github.com/paperswithcode/model-index)
