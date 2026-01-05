---
id: kb-2025-001
title: "C2PA: Coalition for Content Provenance and Authenticity"
created: 2025-01-02
updated: 2025-01-02

author: human
curation_type: ai_assisted

sources:
  - id: src-001
    type: primary
    title: "C2PA Technical Specification v2.2"
    url: "https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html"
    accessed: 2025-01-02
    quotes:
      - text: "A C2PA Manifest comprises one or more assertions, a claim, and a claim signature"
        location: "Section 5 - Data Model"

  - id: src-002
    type: secondary
    title: "C2PA Overview"
    url: "https://c2pa.org/"
    accessed: 2025-01-02
    quotes:
      - text: "Content Credentials function like a nutrition label for digital content"
        location: "Homepage"

  - id: src-003
    type: secondary
    title: "NSA/CISA Guidance on Content Credentials"
    url: "https://media.defense.gov/2025/Jan/29/2003634788/-1/-1/0/CSI-CONTENT-CREDENTIALS.PDF"
    accessed: 2025-01-02

topics:
  - provenance
  - content-authenticity
  - ai-disclosure
  - standards

confidence: high
verified: true
verified_by: human
verification_date: 2025-01-02
verification_notes: "Reviewed C2PA spec directly; quotes verified against source documents"

ai_metadata:
  model: claude-opus-4-5-20251101
  generation_date: 2025-01-02
  reviewed_by: human
  review_date: 2025-01-02
---

# C2PA: Coalition for Content Provenance and Authenticity

## Overview

C2PA is an open technical standard for tracking the origin and edit history of digital content. It provides a way to attach verifiable provenance information to media files, functioning as "a nutrition label for digital content" [src-002].

## Key Concepts

### Manifests, Claims, and Assertions

The C2PA data model is hierarchical [src-001]:

- **Manifest**: A container comprising assertions, a claim, and a claim signature
- **Claim**: A digitally signed statement bundling multiple assertions
- **Assertions**: Individual statements about the content (metadata, actions, ingredients)

### Trust Model

Trust is established through:
1. **X.509 certificates** for cryptographic signing
2. **Trust lists** maintained by validators
3. **Validation states**: well-formed → valid → trusted

### AI Content Disclosure

C2PA explicitly addresses AI-generated content:
- Uses IPTC Digital Source Type vocabulary
- `trainedAlgorithmicMedia` indicates AI-generated content
- Ingredients can reference models and prompts used

## Relevance to CC Forge

We adapt C2PA concepts for our knowledge base:

| C2PA Concept | Our Adaptation |
|--------------|----------------|
| Manifest | YAML frontmatter |
| Claim | Knowledge entry |
| Assertions | Source citations |
| Hard binding | Git commit hash |
| AI disclosure | `curation_type` field |

## Current Status

- Version 2.2 is current (as of 2025)
- Expected ISO standardization in 2025
- Adopted by major platforms (Adobe, Microsoft, OpenAI, BBC, Getty) [src-002]
- NSA/CISA have published guidance on implementation [src-003]

## Further Reading

- [C2PA Specification](https://spec.c2pa.org/)
- [Content Authenticity Initiative](https://contentauthenticity.org/)
- [IPTC Digital Source Types](http://cv.iptc.org/newscodes/digitalsourcetype/)
