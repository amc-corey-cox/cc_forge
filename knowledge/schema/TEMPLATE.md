---
# Copy this template for new knowledge base entries
# Delete these comment lines in your actual entry

id: kb-YYYY-NNN  # Year and sequential number
title: "Your Title Here"
created: YYYY-MM-DD
updated: YYYY-MM-DD

# Provenance - WHO created this
author: human  # or agent:<agent-id>
curation_type: human_curated  # human_curated | ai_assisted | ai_generated | ai_unverified

# Sources - MUST have at least one
sources:
  - id: src-001
    type: primary  # primary | secondary | tertiary
    title: "Source Title"
    authors: ["Author Name"]  # optional
    url: "https://example.com/source"
    accessed: YYYY-MM-DD
    published: YYYY-MM-DD  # optional
    doi: "10.1234/example"  # optional
    arxiv: "1234.56789"  # optional
    quotes:  # optional but encouraged
      - text: "Exact quote from the source"
        location: "Section/page reference"

# Classification
topics:
  - topic-one
  - topic-two

confidence: high  # high | medium | low | uncertain

# Verification
verified: false  # true when sources checked
verified_by: unverified  # human | automated | unverified
verification_date: YYYY-MM-DD  # when verified
verification_notes: ""  # how verification was done

# AI Metadata - REQUIRED if curation_type is ai_*
# ai_metadata:
#   model: model-name
#   model_version: v1.0  # optional
#   prompt_hash: sha256:...  # optional, for reproducibility
#   generation_date: YYYY-MM-DD
#   confidence_score: 0.85  # optional, 0-1
#   reviewed_by: human  # if ai_assisted
#   review_date: YYYY-MM-DD  # if ai_assisted

# Optional
# supersedes: kb-YYYY-NNN  # if replacing another entry
# related:
#   - kb-YYYY-NNN
#   - kb-YYYY-NNN
---

# Title

## Overview

Brief introduction to the topic.

## Key Concepts

### Concept One

Explanation with inline citations like [src-001].

### Concept Two

More content.

## Relevance to CC Forge

Why this matters for our project.

## Further Reading

- [Link text](url)
