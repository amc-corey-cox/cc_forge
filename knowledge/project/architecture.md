---
id: kb-2025-002
title: "CC Forge Architecture Overview"
created: 2025-01-02
updated: 2025-01-02

author: human
curation_type: human_curated

sources:
  - id: src-001
    type: primary
    title: "CC Forge DESIGN.md"
    url: "file://DESIGN.md"
    accessed: 2025-01-02

  - id: src-002
    type: primary
    title: "CC Forge ROADMAP.md"
    url: "file://ROADMAP.md"
    accessed: 2025-01-02

topics:
  - cc-forge
  - architecture
  - project-docs

confidence: high
verified: true
verified_by: human
verification_date: 2025-01-02
verification_notes: "This IS the project documentation"
---

# CC Forge Architecture Overview

This entry provides a quick reference for agents and humans working in the CC Forge codebase.

## What is CC Forge?

CC Forge is a local-first AI agents development system for autonomous software development. It runs on local hardware using local LLMs, with a team-based architecture for quality assurance.

## Core Principles

1. **Local-First**: Core operations run on local hardware
2. **Self-Bootstrapping**: The system develops itself
3. **Transparency**: All agent actions are logged
4. **Defense in Depth**: Multiple teams ensure quality

## Model Strategy

We use a tiered hybrid approach:

| Tier | Hardware | Speed | Use Case |
|------|----------|-------|----------|
| 1 | GPU (Intel ARC) | Fast | Classification, simple tasks |
| 2 | CPU (System RAM) | Slow | Complex code generation |
| 3 | External API | Fast | When local isn't enough |

## Team Architecture (Aspirational)

Five teams are planned:

1. **Triage Team**: Converts roadmap to issues, prioritizes backlog
2. **Dev Team**: Takes issues, creates PRs
3. **Test Team**: Generates tests, ensures coverage
4. **Red Team**: Adversarial review, finds weaknesses
5. **Blue Team**: Validates test quality via mutation testing

Currently in MVP phase with a single "Dev Assistant" agent.

## Current Phase

**Phase 0-3 (MVP)** - Focus on:
- Hardware validation (Intel ARC + Ollama)
- Knowledge base foundation
- Single agent MVP

See [ROADMAP.md](file://ROADMAP.md) for full phasing.

## Key Files

| File | Purpose |
|------|---------|
| `DESIGN.md` | Full architectural vision |
| `ROADMAP.md` | Implementation phases |
| `AGENTS.md` | Instructions for AI agents |
| `knowledge/PROVENANCE.md` | Knowledge base attribution rules |

## Directory Structure

```
cc_forge/
├── src/
│   ├── agents/      # Agent implementations
│   ├── teams/       # Team-specific logic
│   ├── knowledge/   # Knowledge base code
│   └── common/      # Shared utilities
├── knowledge/       # Knowledge base content
├── tests/
├── docker/
└── docs/
```
