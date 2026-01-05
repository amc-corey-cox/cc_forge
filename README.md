# CC Forge

A local-first AI agents development system for autonomous software development.

## What is this?

CC Forge is an experimental project to build a self-improving software development pipeline using AI agents running on local hardware. The system consists of multiple agent teams that work together (and challenge each other) to maintain code quality.

## Teams

- **Dev Team**: Takes issues and creates PRs for bugs and features
- **Test Team**: Creates comprehensive tests and verifies logic
- **Red Team**: Adversarial review to find weaknesses in PRs
- **Blue Team**: Validates test quality through mutation testing

The system also includes a knowledge base component for tracking developments in AI.

## Principles

- **Local-First**: Runs on local hardware with local models
- **Self-Bootstrapping**: The system develops itself
- **Transparent**: All agent actions are logged and auditable
- **Defense in Depth**: Multiple teams ensure quality through redundancy

## Status

This project is in early development (Phase 0: Foundation).

See [ROADMAP.md](ROADMAP.md) for the implementation plan.

## Documentation

- [DESIGN.md](DESIGN.md) - Architectural vision and detailed design
- [AGENTS.md](AGENTS.md) - Instructions for AI agents working in this repo
- [ROADMAP.md](ROADMAP.md) - Phased implementation plan

## Contributing

This is currently a personal project. If you're interested in the concept, feel free to fork and adapt for your own use.

## License

TBD
