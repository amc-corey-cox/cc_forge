# Model Registry

This directory contains our local model registry — tracking which AI models we've tested, their capabilities, and when to use them.

## Purpose

The model registry serves multiple purposes:
1. **Documentation**: What models work on our hardware
2. **Selection**: Help agents choose the right model for a task
3. **Benchmarking**: Track performance over time
4. **Decisions**: Record why we use certain models for certain tasks

## File Format

Each model has a YAML file following a common structure. See `llama-70b.yaml` for the expected fields.

See `llama-70b.yaml` for an example entry.

## Tier System

Models are assigned to tiers based on where they run:

| Tier | Hardware | Speed | Quality | Use When |
|------|----------|-------|---------|----------|
| `gpu` | Intel ARC | Fast | Good | Quick tasks, classification |
| `cpu` | System RAM | Slow | Better | Complex generation, quality matters |
| `api` | External | Fast | Best | Local isn't good enough |

## Status Values

- `untested`: Model identified but not yet tested locally
- `testing`: Currently being evaluated
- `validated`: Confirmed working, benchmarked
- `retired`: No longer in use (superseded or problematic)
- `failed`: Doesn't work on our hardware

## Adding a New Model

1. Copy `llama-70b.yaml` as a template
2. Update all fields with actual data
3. Run benchmarks and fill in performance section
4. Document quality observations
5. Add to git

## Quality Ratings

Subjective ratings for our use cases:

- `excellent`: Performs as well as or better than API models
- `good`: Suitable for production use
- `adequate`: Works but with notable limitations
- `poor`: Not recommended for this task
- `untested`: Haven't evaluated yet

## TODO

Models to evaluate during Phase 1 (Infrastructure Setup):
- [ ] Llama 3.2 7B (GPU candidate)
- [ ] Llama 3.2 13B (GPU/CPU candidate)
- [ ] CodeLlama 7B (code-specific, GPU candidate)
- [ ] Mistral 7B (alternative small model)
- [ ] Phi-3 (very small, classification candidate)
