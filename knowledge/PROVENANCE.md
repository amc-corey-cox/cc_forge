# Knowledge Base Provenance Design

This document defines how we ensure attribution, authenticity, and trust in our knowledge base. The goal is to prevent "garbage in, garbage out" by making every claim traceable and verifiable.

## Inspiration

Two key influences:

1. **[monarch-initiative/dismech](https://github.com/monarch-initiative/dismech)**: Medical knowledge base requiring PubMed citations with exact quotes. Validates that quoted text actually appears in source abstracts.

2. **[C2PA Specification](https://spec.c2pa.org/)**: Coalition for Content Provenance and Authenticity. Provides manifests, claims, and assertions for media provenance, with explicit AI content labeling.

## Core Principles

### 1. Every Claim Needs a Source

No unsourced assertions. Every piece of knowledge must trace back to:
- A primary source (paper, documentation, official announcement)
- A secondary source (reputable article, explainer)
- An explicit "unverified" or "AI-generated" marker

### 2. Sources Must Be Verifiable

- URLs must be live and accessible (or archived)
- Quotes must be exact and findable in the source
- Access dates must be recorded (web content changes)

### 3. Provenance Chain is Preserved

- Who added this knowledge? (human or agent)
- When was it added?
- What was the source of the source? (e.g., found via arXiv, recommended by X)
- Has it been updated since?

### 4. AI Content is Explicitly Labeled

Following C2PA's approach:
- `human_curated`: Human found, read, and summarized
- `ai_assisted`: Human directed AI to summarize, human verified
- `ai_generated`: AI found and summarized, human approved
- `ai_unverified`: AI generated, not yet human verified

### 5. Trust Tiers

Not all sources are equal:

| Tier | Source Type | Examples | Trust Level |
|------|-------------|----------|-------------|
| 1 | Primary | Peer-reviewed papers, official docs, original announcements | Highest |
| 2 | Secondary | Reputable journalism, expert blogs, curated databases | High |
| 3 | Tertiary | Wikipedia, Stack Overflow, community posts | Medium |
| 4 | AI Summary | LLM-generated summaries, even if verified | Lower |
| 5 | Unverified | Claims without sources, AI hallucination risk | Treat as suspect |

---

## Knowledge Entry Schema

Each knowledge entry follows this structure (YAML frontmatter + Markdown body):

```yaml
---
# Identity
id: kb-2025-001
title: "Transformer Architecture Fundamentals"
created: 2025-01-02
updated: 2025-01-02

# Provenance
author: human  # or agent:<agent-id>
curation_type: human_curated  # human_curated | ai_assisted | ai_generated | ai_unverified

# Source Attribution
sources:
  - id: src-001
    type: primary  # primary | secondary | tertiary
    title: "Attention Is All You Need"
    authors: ["Vaswani et al."]
    url: "https://arxiv.org/abs/1706.03762"
    accessed: 2025-01-02
    quotes:
      - text: "The Transformer follows this overall architecture using stacked self-attention..."
        location: "Section 3.1"

# Classification
topics: ["transformers", "attention", "architecture"]
confidence: high  # high | medium | low | uncertain

# Verification
verified: true
verified_by: human  # human | automated | unverified
verification_date: 2025-01-02
verification_notes: "Checked quote against arXiv PDF"
---

# Transformer Architecture Fundamentals

[Content here with inline citations like [src-001]]
```

---

## Verification Pipeline

Inspired by dismech's validation approach:

### Level 1: Schema Validation
- Required fields present
- Dates in correct format
- Source URLs well-formed
- Topics from controlled vocabulary (when established)

### Level 2: Source Accessibility
- URLs return 200 OK (or have archive.org fallback)
- PDFs downloadable
- API endpoints responsive

### Level 3: Quote Verification (Stretch Goal)
- Fetch source content
- Search for quoted text
- Flag if quote not found verbatim
- (This is what dismech does with PubMed abstracts)

### Level 4: Staleness Detection
- Flag entries older than threshold without update
- Check if source URLs have changed
- Detect if topic has significant new developments

---

## AI Content Handling

When agents add to the knowledge base:

### Required Metadata
```yaml
author: agent:dev-assistant-v1
curation_type: ai_generated
ai_metadata:
  model: llama-70b
  prompt_hash: sha256:abc123...  # For reproducibility
  generation_date: 2025-01-02
  confidence_score: 0.85  # If model provides
```

### Verification Requirement
AI-generated content MUST be marked `ai_unverified` until:
- Human reviews and approves, OR
- Automated verification passes (quote check, source check)

### Quarantine Zone
Unverified AI content lives in `knowledge/pending/` until verified, then moves to main knowledge base.

---

## Directory Structure

```
knowledge/
├── PROVENANCE.md           # This document
├── schema/
│   └── entry.yaml          # LinkML or JSON Schema definition
├── topics/                 # Verified knowledge by topic
│   ├── ai-fundamentals/
│   ├── transformers/
│   ├── agents/
│   └── ...
├── project/                # CC Forge-specific knowledge
│   ├── architecture.md
│   ├── conventions.md
│   └── decisions/
├── pending/                # Unverified AI-generated content
│   └── ...
├── sources/                # Cached/archived source material
│   └── ...
└── curriculum/             # Learning paths
    └── ...
```

---

## Implementation Phases

### Phase 1: Manual + Conventions
- YAML frontmatter schema (documented, not enforced)
- Human authors follow conventions
- Git history provides basic provenance

### Phase 2: Schema Validation
- JSON Schema or LinkML for entry validation
- Pre-commit hook to validate new entries
- CI check for schema compliance

### Phase 3: Automated Verification
- URL checking (accessibility)
- Quote verification (where possible)
- Staleness alerts

### Phase 4: Agent Integration
- Agents can add to `pending/`
- Verification pipeline for promotion
- RAG retrieval respects trust tiers

---

## Anti-Patterns to Avoid

1. **Citation Laundering**: Citing a summary that cites a source (lose the chain)
2. **Quote Drift**: Paraphrasing and calling it a quote
3. **Zombie Links**: Sources that 404 with no archive
4. **Trust Inflation**: Treating AI summaries as primary sources
5. **Date Blindness**: Not recording when knowledge was captured

---

## Relation to C2PA

While C2PA is designed for media files with embedded manifests, we adapt its concepts:

| C2PA Concept | Our Adaptation |
|--------------|----------------|
| Manifest | YAML frontmatter |
| Claim | The knowledge entry itself |
| Assertions | Source citations, verification status |
| Hard binding | Git commit hash + file path |
| Claim signature | Git commit signature (GPG) |
| Trust list | Source tier classification |
| AI disclosure | `curation_type` + `ai_metadata` |

The key insight: **Git provides an immutable history**, and **YAML frontmatter provides structured claims**. Together they give us provenance without complex cryptographic infrastructure.

---

## Open Questions

1. **Controlled vocabularies**: Should topics be free-form or from a defined list?
2. **Archive strategy**: Cache sources locally, use archive.org, or trust URLs?
3. **Quote verification**: How aggressive? PubMed-style exact match or fuzzy?
4. **Trust decay**: Should old unverified content be auto-demoted?

---

## References

- [C2PA Specification v2.2](https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html)
- [monarch-initiative/dismech](https://github.com/monarch-initiative/dismech)
- [LinkML](https://linkml.io/) - Schema language used by dismech
- [IPTC Digital Source Type](http://cv.iptc.org/newscodes/digitalsourcetype/) - C2PA's AI content vocabulary
