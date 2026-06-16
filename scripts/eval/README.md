# Eval Harness

Scripts for running the Track 1 evaluation matrix (Claude Code harness with local Ollama models). Output goes to `eval-results/<run-id>/` for later analysis.

## Running

```bash
# From a forge host (tesseract):
MODELS="qwen3-coder-32k gpt-oss:20b" \
OLLAMA_URL="http://forge-ollama-proxy:11434" \
./scripts/eval/run-matrix.sh
```

Required: agent image present (`cc-forge-agent:latest`), `forge-network` exists, Ollama reachable at the URL, all the named models pulled.

To run a single task without the warmup orchestration (useful for debugging):

```bash
OUTPUT_BASE="eval-results/debug" \
./scripts/eval/run-task.sh qwen3-coder-32k scripts/eval/tasks/01-sanity-pong
```

## Output structure

```
eval-results/<run-id>/
├── _warmup/
│   └── <model>/
│       ├── output.json     # The warmup probe's full claude -p response
│       └── stderr.log
└── <model>/
    └── <task>/
        ├── prompt.txt      # Copy of the task's prompt for context
        ├── output.json     # Full claude -p response (parse with jq)
        ├── stderr.log      # Anything claude or docker wrote to stderr
        ├── setup.log       # setup.sh output (only if task has setup.sh)
        ├── score.log       # score.sh output (only if task has score.sh)
        ├── score-exit      # score.sh exit code (only if task has score.sh)
        ├── workspace/      # Final state of /workspace after the run
        └── meta.json       # {model, task, duration_s, exit_code, score?, ollama_url, timestamp}
```

## Tasks

A task is a directory under `scripts/eval/tasks/<NN-name>/`. Files (all optional except `prompt.txt`):

| File | Required | What it does |
|------|----------|--------------|
| `prompt.txt` | yes | The user message sent to `claude -p`. |
| `setup.sh` | no | Runs in the container before `claude -p`, with `cwd=/workspace`. Populates the workspace (write files, `git init`, etc.). Failure aborts the run with exit 90. |
| `score.sh` | no | Runs in the container after `claude -p`, with `cwd=/workspace`. Exit 0 = pass, non-zero = fail. Result is captured in `meta.json` as `"score"`. |
| `expect.md` | no | Human-readable success criteria. For tasks without `score.sh`, this is the grading reference. |

Tasks are run in lexical order. Prefix names with `01-`, `02-`, etc. to control ordering.

### Inside the container, a task sees three mount points

- `/workspace` — fresh per run. Setup writes here, the agent works here, score reads here. Captured at `eval-results/.../<task>/workspace/` after the run.
- `/task` — read-only mount of the task source directory. `setup.sh`, `score.sh`, and any fixtures the task ships with are reachable here.
- `/meta` — read-write mount of the result directory. The harness writes `output.json`, `stderr.log`, `setup.log`, etc. here; you don't normally touch it from inside the container.

### Existing tasks

- `01-sanity-pong/` — minimal smoke. No `setup.sh`, no `score.sh`. Validates the harness end-to-end with a trivial prompt that produces ~3 tokens. Finishes fast even on a fully cold model. Use this when iterating on the harness itself, not when evaluating models.
- `02-fix-typo/` — first real capability task. Workspace contains a `README.md` with a typo; agent must find and fix it; `score.sh` verifies the file now contains `Hello World`. Small enough to keep wall-clock cost bounded.

---

## Cost model — why the harness is shaped the way it is

Running Claude Code (`claude -p ...`) against a local Ollama model on CPU has a sharp two-mode performance profile that drives every design choice in this harness.

### First call to a model: ~25-30 minutes

For any prompt, even a trivial one expecting 3 tokens of output, the first invocation against a fresh Ollama process takes 25-30 minutes on CPU. Decomposition:

| Phase | Approx duration | What's happening |
|------|-----------------|------------------|
| Model load | ~1 min | 17GB model weights read from disk into RAM |
| **Prefill of Claude Code's system prompt** | **~25-27 min** | Claude Code sends a multi-thousand-token system prompt (tool definitions, agent loop machinery) on every call. Processing those tokens through a 17B-class model on CPU at ~5 tok/sec dominates wall-clock time. |
| Generation | ~5-10 sec | Actual response generation (~0.5 tok/sec on CPU) |

This is **not** a hardware diagnosis. The ratio of first-call-cost to warm-call-cost stays huge on any CPU-bound setup. A faster CPU reduces both proportionally.

### Subsequent calls to the same model: 3-7 seconds for short responses

After the first call, Ollama's KV cache holds the model's internal state for Claude Code's invariant system prompt prefix. Subsequent `claude -p` invocations against the same model **skip the prefill** — they just process the small user-message delta and generate the response.

Verified empirically on tesseract 2026-06-16:
- First call: 28m 2s (output: "PONG", 3 tokens)
- Warm call (same prompt): 3.7s (output: "PING", 2 tokens)
- Warm call (**different** prompt — "what is 2+2"): 5.7s (output: "4", 2 tokens)

The third measurement is the critical one: prefix caching works across *independent* `claude -p` invocations as long as the system prompt is unchanged, and survives user-message variation. That's why pre-warming is just a single throwaway call per model.

### Cache persistence

The KV cache persists as long as:
- `OLLAMA_KEEP_ALIVE=-1` is set (see `ollama-cpu.service` in `docs/`), so models don't get auto-evicted on idle
- The Ollama process keeps running (a restart wipes the cache)
- Nothing else evicts the model from memory (concurrent use of a larger model can knock the cached one out)

If you start the matrix and OpenWebUI uses a different big model mid-run, you may pay a fresh warmup the next time the matrix calls into a model. Run the matrix when the box is otherwise quiet for predictable timing.

### Implications for the harness

- **`run-matrix.sh` pre-warms each model exactly once** before timing real tasks. The warmup itself is captured under `_warmup/<model>/` for reference, but its duration is not included in the per-task results.
- **Tasks for a single model run serially** while it's hot. We don't interleave models because every interleave would pay a fresh warmup.
- **No parallelism.** Concurrent runs would compete for the same model in cache and almost guarantee evictions.
- **`run-task.sh` does not warm the model**, by design. It's meant to be orchestrated from `run-matrix.sh` (which warmed it) or called manually when you know the model is already hot.
- **`AGENT_IMAGE` is `cc-forge-agent:latest`** — the same image forge sessions use. The harness exercises the actual production code path, not a stripped-down test harness.

### Implications for the matrix design

- Per-task timing is dominated by **output length**, not input length. Design task prompts that bound expected output to keep matrix runs tractable.
- "Cold call" timing is interesting once, not per task. Capture it from `_warmup/` if you want it as a number.
- The first model in a matrix run pays the full cold cost. Subsequent models pay only their model load (~1 min), not the full ~28 min, because Ollama's KV cache for *Claude Code's system prompt* is keyed per-model — but the same prompt-shape prefix may benefit from CPU-side memory-pressure caching even across models. Don't over-rely on this; assume each new model is ~25 min.

### Implications for Track 3 (cloud Ollama services)

The cache assumptions above are local-Ollama-specific. Cloud services like Together, Fireworks, or OpenRouter may not preserve KV caches across independent requests at all. The harness's pre-warm logic is harmless in that case (the warmup just adds one extra request), but per-task timing won't show the dramatic warm-vs-cold divide. Re-measure Track 1's assumptions when we get to Track 3.
