# CC Forge Model Ontology Schema

This document defines the structure for our model ontology, following OBO Foundry principles adapted for practical use.

## Design Principles

Based on [OBO Foundry Principles](http://obofoundry.org/principles/fp-000-summary.html):

1. **Unique Identifiers** - Every term has a CCF ID
2. **Hierarchical Structure** - Explicit is_a relationships
3. **Formal Relations** - Defined predicates (has_capability, fits_tier, etc.)
4. **Cross-References** - Links to external sources (Ollama, HuggingFace)
5. **Versioning** - Ontology has explicit version

## Identifier Format

```
ccf:<namespace>:<local_id>

Examples:
  ccf:model:qwen2.5-coder-7b
  ccf:family:qwen
  ccf:capability:code-generation
  ccf:tier:gpu-8gb
```

Namespaces:
- `model` - Specific model variants
- `family` - Model families/lineages
- `capability` - What models can do
- `tier` - Hardware deployment tiers
- `quant` - Quantization levels

## Term Schema

Each term is defined in YAML:

```yaml
# Term Definition
id: ccf:model:qwen2.5-coder-7b
label: "Qwen2.5-Coder-7B-Instruct"
definition: "7 billion parameter code-specialized model from Qwen 2.5 series"

# Hierarchy
is_a: ccf:family:qwen           # Parent in hierarchy

# Relations
relations:
  has_capability:
    - ccf:capability:code-generation
    - ccf:capability:code-completion
    - ccf:capability:instruction-following
  has_parameter_count: 7B
  fits_tier:
    - ccf:tier:gpu-8gb          # At Q4_K_M
  developed_by: "Alibaba Cloud"
  license: "Apache-2.0"

# Cross-references
xrefs:
  ollama: "qwen2.5-coder:7b-instruct"
  huggingface: "Qwen/Qwen2.5-Coder-7B-Instruct"

# Metadata
created: 2026-01-06
updated: 2026-01-06
status: active
```

## Hierarchy Structure

```
ccf:root
├── ccf:family:*                    # Model families
│   ├── ccf:family:qwen
│   ├── ccf:family:llama
│   ├── ccf:family:deepseek
│   ├── ccf:family:mistral
│   └── ccf:family:stable-diffusion
│
├── ccf:capability:*                # Capabilities
│   ├── ccf:capability:text-generation
│   │   ├── ccf:capability:code-generation
│   │   ├── ccf:capability:reasoning
│   │   └── ccf:capability:chat
│   ├── ccf:capability:embedding
│   └── ccf:capability:image-generation
│
├── ccf:tier:*                      # Hardware tiers
│   ├── ccf:tier:gpu-8gb           # Intel Arc
│   ├── ccf:tier:cpu-64gb          # CPU inference
│   └── ccf:tier:api               # External API
│
└── ccf:quant:*                     # Quantization
    ├── ccf:quant:q8_0
    ├── ccf:quant:q4_k_m
    └── ccf:quant:q3_k_m
```

## Relation Definitions

| Relation | Domain | Range | Description |
|----------|--------|-------|-------------|
| `is_a` | any | any | Hierarchical parent |
| `has_capability` | model | capability | What model can do |
| `fits_tier` | model | tier | Where model runs |
| `has_parameter_count` | model | string | Size (e.g., "7B") |
| `developed_by` | model/family | string | Creator organization |
| `derived_from` | model | model | Base model (for finetunes) |
| `supersedes` | model | model | Replaces older model |

## File Organization

```
knowledge/topics/models/
├── ontology/
│   ├── _schema.md              # This document
│   ├── _terms.yaml             # All term definitions
│   ├── families.yaml           # Family hierarchy
│   ├── capabilities.yaml       # Capability hierarchy
│   └── tiers.yaml              # Hardware tier definitions
├── families/                   # Human-readable docs (reference _terms.yaml)
├── capabilities/
└── ...
```

## Validation

Terms should be validated for:
1. Unique IDs (no duplicates)
2. Valid is_a references (parent exists)
3. Valid relation targets (referenced terms exist)
4. Required fields present (id, label, definition)

## Versioning

Ontology version follows semantic versioning:
- **Major**: Breaking changes to structure
- **Minor**: New terms or relations
- **Patch**: Definition/metadata updates

Current version: `0.1.0` (initial structure)

## Migration from Current State

The existing markdown documents remain as human documentation. The YAML ontology adds:
1. Machine-parseable term definitions
2. Explicit relationships
3. Validation capability
4. Future RAG integration

Markdown docs reference ontology terms by ID for consistency.

---

## References

- [OBO Foundry Principles](http://obofoundry.org/principles/fp-000-summary.html)
- [MONDO Disease Ontology](https://mondo.monarchinitiative.org/)
- [OBO Academy](https://oboacademy.github.io/obook/)
