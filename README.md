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

This project is in active development (Phase 3: MVP Integration). Local AI coding assistant is functional.

See [ROADMAP.md](ROADMAP.md) for the implementation plan.

## Quick Start: Claude Code with Local Models

Run Claude Code using local Ollama models instead of cloud APIs.

### Prerequisites

- Ollama 0.15+ running on your server (see [LOCAL-OLLAMA-SETUP.md](docs/LOCAL-OLLAMA-SETUP.md))
- Claude Code CLI installed (see [Anthropic's documentation](https://docs.anthropic.com/en/docs/claude-code))
- A model pulled: `ollama pull llama3.1`

### Running on the Server

Run Claude Code directly on your Ollama server (via SSH or local terminal - no difference):

```bash
# If remote, SSH to your server first
ssh myserver

# Set environment and run
export ANTHROPIC_AUTH_TOKEN=ollama
export ANTHROPIC_BASE_URL=http://localhost:11434
claude --model llama3.1
```

For GPU acceleration (requires [shim setup](docs/LOCAL-OLLAMA-SETUP.md#option-2-use-shim-for-gpu-advanced)):
```bash
export ANTHROPIC_BASE_URL=http://localhost:4001
claude --model llama3.1
```

**Note:** Whether you SSH in or use a local terminal, the commands are identical - Claude Code connects to Ollama on localhost either way.

### Remote Access (Coming Soon)

Secure remote access via Tailscale is planned for Phase 7. This will allow running Claude Code from any device without exposing ports to your network.

See [ROADMAP.md](ROADMAP.md#phase-7-remote-and-mobile-access) for details.

### What to Expect

- **First request**: 60-90 seconds (Claude Code sends a large ~18KB system prompt)
- **Subsequent requests**: Faster while model stays loaded
- **Quality**: Local 7B models are much weaker than cloud Claude - best for simple tasks

For complex coding work, consider [Aider](https://aider.chat) (optimized for local models) or cloud Claude.

### Troubleshooting

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Check available models
ollama list

# Test basic inference
ollama run llama3.1 "Hello"
```

See [docs/LOCAL-OLLAMA-SETUP.md](docs/LOCAL-OLLAMA-SETUP.md) for detailed configuration.

## Documentation

- [DESIGN.md](DESIGN.md) - Architectural vision and detailed design
- [AGENTS.md](AGENTS.md) - Instructions for AI agents working in this repo
- [ROADMAP.md](ROADMAP.md) - Phased implementation plan

## Contributing

This is currently a personal project. If you're interested in the concept, feel free to fork and adapt for your own use.

## License

TBD
