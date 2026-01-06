---
id: kb-2026-009
title: "Embedding Models for RAG"
created: 2026-01-06
updated: 2026-01-06

author: human
curation_type: ai_assisted

sources:
  - id: src-001
    type: secondary
    title: "Finding the Best Open-Source Embedding Model for RAG"
    url: "https://www.tigerdata.com/blog/finding-the-best-open-source-embedding-model-for-rag"
    accessed: 2026-01-06
  - id: src-002
    type: secondary
    title: "Best Ollama Embedding Models Guide"
    url: "https://www.arsturn.com/blog/picking-the-perfect-partner-a-guide-to-choosing-the-best-embedding-models-in-ollama"
    accessed: 2026-01-06
  - id: src-003
    type: secondary
    title: "Comparing AI Embedding Models"
    url: "https://geirfreysson.com/posts/2025-01-25-comparing-embedding-models/"
    accessed: 2026-01-06

topics:
  - models
  - models/capability/embedding
  - embedding-text
  - rag

confidence: medium
verified: true
verified_by: human
verification_date: 2026-01-06
verification_notes: "Based on benchmarks and community comparisons"

ai_metadata:
  model: claude-opus-4-5-20251101
  generation_date: 2026-01-06
  reviewed_by: human
  review_date: 2026-01-06
---

# Embedding Models for RAG

## Overview

Embedding models convert text into numerical vectors that capture semantic meaning. These vectors enable:
- **Semantic search** - Find relevant documents by meaning, not just keywords
- **RAG (Retrieval-Augmented Generation)** - Feed relevant context to LLMs
- **Clustering** - Group similar documents
- **Similarity comparison** - Measure how alike texts are

**Why it matters for CC Forge:** The knowledge base will need retrieval. Good embeddings mean better context for agents.

## Key Concepts

### What Makes a Good Embedding Model?

| Factor | Description |
|--------|-------------|
| **Retrieval accuracy** | Does it find the right documents? |
| **Speed** | How fast can it embed text? |
| **Dimensions** | Vector size (affects storage/search speed) |
| **Context length** | Max input tokens |
| **Domain fit** | General vs. code vs. specialized |

### MTEB Benchmark

The Massive Text Embedding Benchmark (MTEB) is the standard for comparing embedding models across multiple tasks.

Key MTEB scores:
- **Overall** - Average across all tasks
- **Retrieval** - Finding relevant documents (most important for RAG)
- **Clustering** - Grouping similar items
- **Classification** - Categorizing text

## Model Comparison

### Models Available in Ollama

| Model | Dimensions | Context | Size | MTEB Overall | MTEB Retrieval |
|-------|------------|---------|------|--------------|----------------|
| nomic-embed-text | 768 | 8192 | 548MB | 62.39 | 49.01 |
| mxbai-embed-large | 1024 | 512 | 1.34GB | 64.68 | 54.39 |
| all-minilm | 384 | 256 | 46MB | ~56 | ~45 |
| snowflake-arctic-embed | 1024 | 512 | 1.1GB | 67+ | 55+ |

### Direct Comparison: nomic vs mxbai

From benchmark testing [src-001]:

| Aspect | nomic-embed-text | mxbai-embed-large |
|--------|------------------|-------------------|
| Overall retrieval | 57.25% | 59.25% |
| Short queries | 63.75% | 57.5% |
| Long documents | Better | Worse |
| Context length | 8192 | 512 |
| Size | 548MB | 1.34GB |
| Speed | Very fast | Fast |

**Key insight:** nomic-embed-text performs better on short, direct queries despite lower overall scores [src-001].

### Best Overall: bge-m3

"bge-m3 achieved the highest overall retrieval accuracy at 72%, significantly outperforming other models" [src-001]

However, bge-m3 is larger and may not be in Ollama by default.

## Recommendations by Use Case

### General RAG (Knowledge Base)

**Recommended:** nomic-embed-text

```bash
ollama pull nomic-embed-text
```

**Why:**
- 8192 token context - handles longer documents
- Good balance of speed and quality
- Small footprint (548MB)
- Native Ollama support

### Maximum Quality

**Recommended:** snowflake-arctic-embed or bge-m3

Higher scores but larger models. Use if retrieval quality is critical.

### Edge/Constrained

**Recommended:** all-minilm

```bash
ollama pull all-minilm
```

- Only 46MB
- Fast inference
- Lower quality but adequate for simple use

### Code Embedding

For embedding code specifically, options include:
- **nomic-embed-text** - Works reasonably for code
- **CodeBERT derivatives** - Specialized but less Ollama support
- **OpenAI text-embedding-3** - API option if local insufficient

Most general embedding models handle code adequately for retrieval purposes.

## Local Deployment

### Using with Ollama

```bash
# Pull the model
ollama pull nomic-embed-text

# Generate embeddings
curl http://localhost:11434/api/embeddings \
  -d '{"model": "nomic-embed-text", "prompt": "Your text here"}'
```

### Performance Expectations

On typical hardware:
- **nomic-embed-text:** ~100+ documents/sec
- **mxbai-embed-large:** ~50+ documents/sec

Embedding is much faster than LLM generation - even CPU is fine.

### Memory Requirements

Embedding models are small:
- nomic-embed-text: ~1GB RAM during inference
- mxbai-embed-large: ~2GB RAM during inference

No GPU required for reasonable performance.

## RAG Architecture Considerations

### Chunking Strategy

How you split documents matters more than embedding model choice:

| Chunk Size | Pros | Cons |
|------------|------|------|
| Small (256 tokens) | Precise retrieval | Loses context |
| Medium (512-1024) | Good balance | Standard choice |
| Large (2048+) | More context | May miss specific info |

**Recommendation:** Start with 512-token chunks with 50-100 token overlap.

### Hybrid Search

Combining embedding search with keyword search often beats either alone:
- Embeddings catch: Semantic similarity, paraphrases
- Keywords catch: Exact terms, names, technical terms

### Reranking

For critical applications, add a reranker:
1. Retrieve top 20-50 with embeddings
2. Rerank with a cross-encoder
3. Return top 5-10

Reranking improves quality but adds latency.

## CC Forge Recommendations

### Primary Embedding Model

**nomic-embed-text**

```bash
ollama pull nomic-embed-text
```

**Rationale:**
- 8K context handles most knowledge base entries
- Good speed for bulk embedding
- Adequate quality for our use case
- Simple Ollama integration

### For the Knowledge Base

The CC Forge knowledge base (`knowledge/`) will need:
1. **Document embedding** - Embed all KB entries
2. **Query embedding** - Embed user/agent queries
3. **Retrieval** - Find relevant entries

nomic-embed-text is sufficient for this scale.

### Future Considerations

If retrieval quality becomes a bottleneck:
1. Try larger models (bge-m3, arctic)
2. Add reranking step
3. Tune chunking strategy
4. Consider domain-specific fine-tuning

## Practical Example

### Embedding Knowledge Base Entries

```python
import ollama

def embed_document(text: str) -> list[float]:
    response = ollama.embeddings(
        model='nomic-embed-text',
        prompt=text
    )
    return response['embedding']

# Embed a KB entry
doc_text = "Qwen2.5-Coder is a code-specialized model..."
vector = embed_document(doc_text)
# vector is a 768-dimensional list of floats
```

### Similarity Search

```python
import numpy as np

def cosine_similarity(a: list, b: list) -> float:
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# Compare query to documents
query_vec = embed_document("best coding model for local use")
similarities = [
    cosine_similarity(query_vec, doc_vec)
    for doc_vec in document_vectors
]
```

## Related Documents

- Selection guide: `../_selection-guide.md`
- Knowledge base design: `/knowledge/PROVENANCE.md`
