# Running a Forge Session

This guide walks the Phase-1 loop end to end: hand an agent a task, let it work
in an isolated container, review what it did in Forgejo, and promote the result
to GitHub.

---

## Prerequisites

**On the server (where forge and Docker run):**

- Docker and Docker Compose
- Ollama running locally (see [LOCAL-OLLAMA-SETUP.md](LOCAL-OLLAMA-SETUP.md))
- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- `forge` installed (`uv sync` in the cc_forge checkout)
- A Forgejo admin account and API token (see the README's First-Time Setup)
- `~/.config/forge/config.env` with at least `FORGE_FORGEJO_TOKEN`

**On the workstation (only if you run forge on a separate server):**

- The `forge` wrapper from `scripts/remote-forge/` installed as your `forge`
- SSH access to the server
- The `gh` CLI, authenticated (`gh auth login`)
- A clone of the same repository whose `origin` points at GitHub

If forge and you live on the same machine, ignore the workstation column — the
server prerequisites are all you need.

---

## 1. Start a Session

From any git repository, run:

```bash
forge
```

This launches Claude Code backed by local Ollama models. Behind the scenes forge:

1. Starts the infrastructure (Forgejo + the Ollama proxies) if Forgejo isn't
   already running.
2. Creates the repository on Forgejo if it doesn't exist yet.
3. Pushes your current branch to Forgejo.
4. Launches an agent container that clones from Forgejo — no host mount.
5. Drops you into an interactive Claude Code session inside the container.

### Use the Claude API instead of local models

```bash
forge run --claude
```

Set `FORGE_CLAUDE_API_KEY` in `config.env` (forge also honors `ANTHROPIC_API_KEY`).
The `--claude` flag routes the agent to the Anthropic API instead of the local
Ollama proxy.

### Use Aider

```bash
forge run --agent aider
```

Launches Aider against the same Ollama instance instead of Claude Code.

---

## 2. The Agent Workflow

Inside the session the agent has a clone of your repo and can read, edit, commit,
and push. It also has `gh` — a shim that routes pull-request and repo operations
to Forgejo, and issue reads to GitHub. (GitHub reads need `FORGE_GITHUB_TOKEN`
configured; without it, GitHub-bound commands fail.)

A well-behaved session follows this shape:

1. **Understand the task** — read the relevant code until the goal is clear.
2. **Make the change** — the smallest diff that fully solves it.
3. **`/self-review`** — check the diff for correctness, focus, and clarity.
4. **`/complexity-audit`** — check for abstraction or defensive code that isn't
   earning its keep.
5. **Open a PR** — `gh pr create` on Forgejo.

`/self-review` and `/complexity-audit` are Claude Code slash commands injected
into the container. They're the single-agent seed of forge's planned review teams.

---

## 3. Review the Work

When the session ends you're back in your shell; the agent's commits and PR live
in Forgejo. Open the Forgejo web UI (`http://localhost:3000`, or wherever your
instance runs) to read the PR description, the diff, and the commit history.

To iterate, start another session — but note that `forge` pushes your *current
local branch* to Forgejo at startup. If the agent's branch has moved ahead, pull
it into your local checkout first, or that push will be rejected:

```bash
git fetch forgejo
git merge forgejo/<branch-name>
```

That same fetch-and-merge is also how you take the agent's work locally if you
don't intend to open a GitHub PR at all.

---

## 4. Promote to GitHub

When you're satisfied with the Forgejo PR, promote it:

```bash
forge promote <pr-number>
```

`<pr-number>` is the Forgejo PR number (shown in the Forgejo UI). Promote fetches
the agent's branch, creates a local branch from it, pushes that to your GitHub
remote (`origin` by default), opens a GitHub PR with the same title and body, and
prints the URL.

**Promotion runs where your GitHub credentials are — your machine, never the
container.** The agent container can reach Forgejo but has no GitHub access, so
crossing to GitHub is a deliberate, human-authorized step. How it plays out
depends on your setup:

- **Single machine** — forge, Forgejo, and you on one host. `forge promote` reads
  the local Forgejo directly and pushes to GitHub. It needs `gh` authenticated
  (or `FORGE_GITHUB_TOKEN`), plus the GitHub target set via `FORGE_GITHUB_REPO`
  (`owner/repo`) or `FORGE_GITHUB_OWNER` in `config.env`.

- **Separate workstation + server** — run `forge promote` on your **workstation**
  (the `scripts/remote-forge/` wrapper). It SSHes to the server for the PR's
  metadata, then does the push and GitHub PR locally with your `gh` auth,
  **inferring the repo from your `origin` remote — so no `FORGE_GITHUB_*` config
  is needed on the workstation**. You need the wrapper installed and SSH to the
  server.

### Options

```bash
forge promote 1 --remote upstream    # push to a remote other than origin
forge promote 1 --repo /path/to/repo
```

### Inspect a PR without promoting

```bash
forge pr-show <pr-number>
```

Prints the head branch, base branch, title, and body as JSON. (It's also the call
the workstation wrapper makes under the hood to fetch metadata from the server.)

---

## Configuration Reference

Settings are read from `~/.config/forge/config.env`, a `.env` file in the working
directory, or environment variables (which take precedence). The common ones:

| Variable | Default | Purpose |
|----------|---------|---------|
| `FORGE_FORGEJO_TOKEN` | *(required)* | Forgejo API token |
| `FORGE_FORGEJO_URL` | `http://localhost:3000` | Forgejo instance URL |
| `FORGE_CLAUDE_API_KEY` | *(empty)* | Anthropic API key for `--claude` mode |
| `FORGE_CLAUDE_MODEL` | `qwen3-coder-32k` | Model for Claude Code in Ollama mode |
| `FORGE_GITHUB_TOKEN` | *(empty)* | GitHub token — for the agent's GitHub reads, and for promote when `gh` isn't authed |
| `FORGE_GITHUB_REPO` | *(empty)* | GitHub `owner/repo` for single-machine promote (or set `FORGE_GITHUB_OWNER`) |
| `FORGE_GITHUB_OWNER` | *(empty)* | GitHub owner; repo name derived from the local directory |
| `FORGE_AGENT_IMAGE` | `cc-forge-agent:latest` | Docker image for agent containers |
| `FORGE_AGENT_MEM_LIMIT` | `4g` | Memory limit per agent container |

This is the set you'll usually touch, not every knob — see `config.py` for the
full list.
