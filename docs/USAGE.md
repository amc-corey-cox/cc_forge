# Using the Local Coding Assistant

This guide covers daily use of Aider with local Ollama models.

---

## Prerequisites

- Ollama running (check with `ollama list`)
- Aider installed (`which aider` should return `/usr/local/bin/aider`)
- A coding model pulled (e.g., `qwen2.5-coder:7b-instruct-q4_K_M`)

---

## Quick Start

```bash
# Navigate to your project
cd /path/to/your/project

# Start Aider with local Ollama model
aider --model ollama/qwen2.5-coder:7b-instruct-q4_K_M
```

Aider will start an interactive session. Type your request and press Enter.

---

## Common Workflows

### Generate New Code

```
> Create a function that validates email addresses using regex
```

Aider will generate the code and show you a diff. Type `y` to apply.

### Edit Existing Code

First, add files to the chat context:

```
> /add src/utils.py
```

Then request changes:

```
> Add error handling to the parse_config function
```

### Explain Code

```
> /add src/complex_module.py
> Explain what the process_data function does
```

### Fix Bugs

```
> /add src/buggy.py
> Fix the off-by-one error in the loop on line 42
```

---

## Git Integration

Aider auto-commits changes with descriptive messages by default.

### Useful Git Options

```bash
# Disable auto-commit (manual control)
aider --no-auto-commits --model ollama/qwen2.5-coder:7b-instruct-q4_K_M

# Work without git entirely
aider --no-git --model ollama/qwen2.5-coder:7b-instruct-q4_K_M
```

### Undo Changes

Aider commits each change separately, so you can undo with:

```bash
git reset --hard HEAD~1
```

---

## Model Selection

### GPU Tier (Fast, 7B models)

For quick tasks — use models that fit on GPU:

```bash
aider --model ollama/qwen2.5-coder:7b-instruct-q4_K_M
```

Best for: Simple edits, explanations, small functions.

### CPU Tier (Slow, 32B-70B models)

For complex tasks — larger models on CPU:

```bash
aider --model ollama/qwen2.5-coder:32b-instruct-q4_K_M
```

Best for: Architecture decisions, complex refactoring, multi-file changes.

Expect slower responses (1-5 tokens/sec). Start the task and do something else.

---

## In-Chat Commands

| Command | Description |
|---------|-------------|
| `/add <file>` | Add file to chat context |
| `/drop <file>` | Remove file from context |
| `/ls` | List files in context |
| `/diff` | Show pending changes |
| `/undo` | Undo last change |
| `/clear` | Clear chat history |
| `/help` | Show all commands |
| `/quit` | Exit Aider |

---

## Configuration

Create `.aider.conf.yml` in your project or home directory:

```yaml
# Example configuration
model: ollama/qwen2.5-coder:7b-instruct-q4_K_M
auto-commits: true
```

See `aider --help` for all options.

---

## Tips

### Reduce Token Usage

- Add only the files you need (`/add` specific files, not whole directories)
- Be specific in your requests
- Use `/clear` to reset context when switching tasks

### Better Results

- Provide context: "In this Flask app, add a route that..."
- Reference existing patterns: "Following the style of the other functions in this file..."
- Break large tasks into smaller steps

### When Things Go Wrong

- `/undo` reverts the last change
- `git diff` to see what changed
- `git reset --hard HEAD~1` to undo the last commit
- Try a larger model for complex tasks

---

## Troubleshooting

### "Connection refused" to Ollama

Check Ollama is running:

```bash
systemctl status ollama-ipex  # or ollama-cpu
ollama list
```

### Model not found

Pull the model first:

```bash
ollama pull qwen2.5-coder:7b-instruct-q4_K_M
```

### Slow responses

You're likely using a CPU-tier model. This is expected. For faster responses, use a smaller GPU-tier model.

### Poor quality output

Try a larger model, or be more specific in your prompt. The 7B models work well for simple tasks but struggle with complex reasoning.

---

## Examples

### Example: Add a New Feature

```bash
cd ~/projects/myapp
aider --model ollama/qwen2.5-coder:7b-instruct-q4_K_M

> /add src/api/routes.py src/models/user.py
> Add a new endpoint POST /api/users/deactivate that sets user.active = False
```

### Example: Refactor with Tests

```bash
aider --model ollama/qwen2.5-coder:7b-instruct-q4_K_M

> /add src/utils.py tests/test_utils.py
> Refactor the parse_date function to handle ISO 8601 format, and update the tests
```

### Example: Explain and Document

```bash
aider --model ollama/qwen2.5-coder:7b-instruct-q4_K_M

> /add src/algorithm.py
> Explain how the optimize function works, then add docstrings to all public functions
```

---

## Remote Server Setup (tesseract)

The local AI assistant runs on a dedicated server (tesseract) with GPU/CPU resources for Ollama.

### Architecture

```
Local Workstation                    Tesseract Server
┌─────────────────────┐              ┌─────────────────────┐
│ ~/Code/cc_forge     │◄──── git ───►│ ~/Code/cc_forge     │
│ Claude Code (cloud) │              │ Aider + Ollama      │
└─────────────────────┘              └─────────────────────┘
```

### Connecting

```bash
ssh tesseract
cd ~/Code/cc_forge
aider --model ollama/qwen2.5-coder:7b-instruct-q4_K_M
```

### Workflow

1. **Work locally** with Claude Code (or other tools), push to GitHub
2. **SSH to tesseract**, `git pull`, run Aider for local AI tasks
3. **Push changes** from tesseract, pull locally when needed

### GitHub Authentication

Tesseract uses a fine-grained Personal Access Token (PAT) for GitHub push access:

- **Token scope**: cc_forge and cc_env repos only
- **Permissions**: Contents (read/write), Metadata (read)
- **Storage**: `~/.git-credentials` on tesseract

To update the token (when it expires):

```bash
# On tesseract
# Delete old credential
git credential reject <<EOF
protocol=https
host=github.com
EOF

# Next git push will prompt for new token
```

### Available Models

Check available models on tesseract:

```bash
ssh tesseract "ollama list"
```

Common models:
- `qwen2.5-coder:7b-instruct-q4_K_M` — Fast (GPU), good for simple tasks
- `llama3.3:70b-instruct-q6_K` — Slow (CPU), better for complex tasks

---

## Related Documentation

- Model tiers: `docs/models-intel-arc.md` (GPU), `docs/models-cpu-tier.md` (CPU)
- Framework evaluation: `docs/AGENT-FRAMEWORK-EVALUATION.md`
- Aider docs: https://aider.chat/docs/

---

*Last updated: 2026-01-30*
