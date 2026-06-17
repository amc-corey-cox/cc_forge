# Running a Forge Session

This guide walks through the Phase-1 loop: give an agent a task, let it work in
isolation, review what it did, and promote the result to GitHub.

---

## Prerequisites

**On the server (where forge and Docker run):**

- Docker and Docker Compose
- Ollama running locally (see [LOCAL-OLLAMA-SETUP.md](LOCAL-OLLAMA-SETUP.md))
- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- `forge` installed (`uv sync` in the cc_forge checkout)
- A Forgejo admin account and API token (see the README's First-Time Setup)
- `~/.config/forge/config.env` with at least `FORGE_FORGEJO_TOKEN`

**On the workstation (where you promote to GitHub):**

- The `gh` CLI, authenticated (`gh auth login`)
- A clone of the same repository with an `origin` remote pointing at GitHub

If the server and workstation are the same machine, both sets of prerequisites
apply there.

---

## 1. Start a Session

Navigate to any git repository and run:

```bash
forge
```

This starts Claude Code backed by local Ollama models. Behind the scenes forge:

1. Starts Forgejo and the Ollama proxy containers if they aren't already running.
2. Creates the repository on Forgejo if it doesn't exist yet.
3. Pushes your current branch to Forgejo.
4. Launches an agent container that clones from Forgejo (no host mount).
5. Drops you into an interactive Claude Code session inside the container.

### Using the Claude API instead of local models

If you have an Anthropic API key and want to use it instead of Ollama:

```bash
forge run --claude
```

Set `FORGE_CLAUDE_API_KEY` in your `config.env` (or export `ANTHROPIC_API_KEY`
— forge checks both). The `--claude` flag tells forge to route requests to the
Anthropic API rather than the local Ollama proxy.

### Using Aider

```bash
forge run --agent aider
```

This launches Aider instead of Claude Code. Aider connects to the same Ollama
instance.

---

## 2. The Agent Workflow

Once inside the session the agent has a clone of your repo and can read, edit,
commit, and push. It also has access to `gh` (a shim that routes to Forgejo for
writes and to GitHub for reads).

A well-behaved session follows this sequence:

1. **Understand the task.** Read the relevant code and the issue until the goal
   is clear.
2. **Make the change.** Write the smallest diff that fully solves the task.
3. **Self-review.** Run `/self-review` — this checks the change against the
   task goals for correctness, focus, and clarity.
4. **Complexity audit.** Run `/complexity-audit` — this checks for unnecessary
   abstraction, over-engineering, or defensive code that doesn't earn its keep.
5. **Open a PR.** The agent opens a pull request on Forgejo via `gh pr create`.

The `/self-review` and `/complexity-audit` commands are Claude Code slash
commands injected into the container. They're the single-agent seed of forge's
planned multi-agent review teams.

---

## 3. Review the Work

When the session ends you're back in your shell. The agent's commits and PR live
in Forgejo.

Open the Forgejo web UI at `http://localhost:3000` (or wherever your Forgejo
instance is running) to:

- Read the PR description and diff.
- Check the commit history.
- Leave comments if you plan to iterate.

If the work isn't right, start another session — the agent will pick up from the
current state of the Forgejo branch.

If you just want the changes locally without opening a GitHub PR, you can pull
the agent's branch directly:

```bash
git fetch forgejo
git merge forgejo/<branch-name>
```

---

## 4. Promote to GitHub

Once you're satisfied with the PR, promote it:

```bash
forge promote <pr-number>
```

Where `<pr-number>` is the Forgejo PR number (visible in the Forgejo UI).

This command:

1. Fetches the agent's branch from the `forgejo` remote.
2. Creates a local branch tracking it.
3. Pushes the branch to your GitHub remote (`origin` by default).
4. Opens a GitHub PR with the same title and description.
5. Prints the GitHub PR URL.

### Why promote exists

The agent container can talk to Forgejo but has no GitHub credentials. Promotion
is the deliberate boundary crossing: reviewed work moves from the local safety
zone to the public repository, using your credentials, on your machine.

### Options

```bash
# Push to a different remote:
forge promote 1 --remote upstream

# Run from a different directory:
forge promote 1 --repo /path/to/repo
```

### Configuration for promote

`forge promote` needs to know where to push on GitHub. Set one of these in
`~/.config/forge/config.env`:

- `FORGE_GITHUB_REPO` — explicit `owner/repo` (e.g. `amc-corey-cox/cc_forge`).
- `FORGE_GITHUB_OWNER` — just the owner; the repo name is derived from the
  local directory.

One of these is required. Promote will warn if the resolved repo doesn't match
your `origin` remote URL, but it doesn't fall back to parsing the remote.

For authentication, promote uses ambient `gh auth` by default. If you prefer
token-based auth, set `FORGE_GITHUB_TOKEN` in `~/.config/forge/config.env`.

You can also inspect a Forgejo PR's metadata without promoting it:

```bash
forge pr-show <pr-number>
```

This prints the head branch, base branch, title, and body as JSON.

---

## Configuration Reference

All settings live in `~/.config/forge/config.env` (or a `.env` file in the
working directory, or environment variables). Environment variables take
precedence.

| Variable | Default | Purpose |
|----------|---------|---------|
| `FORGE_FORGEJO_TOKEN` | *(required)* | Forgejo API token |
| `FORGE_FORGEJO_URL` | `http://localhost:3000` | Forgejo instance URL |
| `FORGE_CLAUDE_API_KEY` | *(empty)* | Anthropic API key for `--claude` mode |
| `FORGE_CLAUDE_MODEL` | `qwen3-coder-32k` | Model name for Claude Code (Ollama mode) |
| `FORGE_GITHUB_TOKEN` | *(empty)* | GitHub token for promote (optional if `gh` is authed) |
| `FORGE_GITHUB_REPO` | *(empty)* | GitHub `owner/repo` for promote (required unless `FORGE_GITHUB_OWNER` is set) |
| `FORGE_GITHUB_OWNER` | *(empty)* | GitHub owner for promote (repo name derived from local directory) |
| `FORGE_AGENT_IMAGE` | `cc-forge-agent:latest` | Docker image for agent containers |
| `FORGE_AGENT_MEM_LIMIT` | `4g` | Memory limit per agent container |

---

*Last updated: 2026-06-17*
