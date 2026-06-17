# Claude Code with Local Ollama Models

How Claude Code performs against local Ollama models, and which ones we recommend. Part of the [Track 1 evaluation](https://github.com/amc-corey-cox/cc_forge/issues) of the agent-architecture exploration.

> **Status:** First screening matrix run complete (2026-06-17). Headline result: `qwen3-coder-32k` is the only model in our initial shortlist that meaningfully drives Claude Code in this harness. Recommendation stands as the dogfood default.

## Headline cost model

Performance has a sharp two-mode profile:

- **First call to a model:** ~25-30 minutes wall-clock on CPU, regardless of how short the prompt is. ~95% of that is Claude Code's large invariant system prompt being prefilled through the model.
- **Subsequent calls to the same model:** seconds for short responses, dominated by output generation rate (~0.5 tok/sec on CPU). Ollama's KV cache reuses the system-prompt prefix.

Practical implication: a forge session against a fresh local model will appear hung for ~25 minutes on the first prompt. After that, it behaves like a normal CPU-inference session.

Full mechanism, decomposition, empirical measurements, and operational consequences are documented in [`scripts/eval/README.md`](../scripts/eval/README.md) — that's where the eval harness lives and where this understanding is canonically maintained.

## Running an eval matrix

See `scripts/eval/README.md` for the harness invocation. Output lands in `eval-results/<run-id>/`.

## Results — screening matrix 1 (2026-06-17)

Eval harness invocation: `MODELS="qwen3-coder-32k gpt-oss:20b gpt-oss-64k" ./scripts/eval/run-matrix.sh`. All 6 tasks (`01-sanity-pong` plus `02` through `06` as defined in `scripts/eval/tasks/`). Hardware: server CPU only, Ollama via the `forge-ollama-proxy` bridge.

| Task | qwen3-coder-32k | gpt-oss:20b | gpt-oss-64k |
|------|-----------------|-------------|-------------|
| 01-sanity-pong | ran (8 min) | ran (2 min) | timed out (58 min) |
| 02-fix-typo | **PASS** (28 min) | fail (7 min) | timed out (58 min) |
| 03-add-docstring | **PASS** (28 min) | fail (96 min) | timed out (58 min) |
| 04-rename-variable | **PASS** (29 min) | fail (73 min) | timed out (58 min) |
| 05-fix-failing-test | **PASS** (31 min) | fail (96 min) | timed out (58 min) |
| 06-implement-from-stub | **PASS** (36 min) | fail (63 min) | **PASS** (16 min) |
| **Capability pass-rate** | **5/5** | **0/5** | **1/5** |

### Interpretation

- **qwen3-coder-32k (17 GB) — recommended.** Passed every capability task cleanly. ~28-36 min per task, ~3 hours for the full task suite once warm. Multi-turn agent loops worked end-to-end. Implementations were correct, not pattern-matched (e.g., `06` produced canonical `return s == s[::-1]` and explained why).
- **gpt-oss:20b (12 GB) — not suitable.** Fast (2-7 min per task) but failed every capability check. The agent does engage and produce output, but the changes it makes don't satisfy the task's structural requirements. Not a slowness problem; a capability problem.
- **gpt-oss-64k (12 GB) — too slow.** Five of six tasks hit Claude Code's HTTP request timeout at ~58 minutes with zero tokens generated — the model is just slow enough that Claude Code's client gives up before it produces useful output. The single pass (`06`) is real (the workspace was correctly modified) but the model also emitted weird narration about being unable to help; the win may not be reproducible. Not the right model for this harness on this hardware.

### Caveats worth knowing

- **All numbers are wall-clock on a CPU-only host.** A faster CPU shifts every number proportionally, but the pattern (pass/fail per task) reflects model capability, which is hardware-independent.
- **The HTTP timeout that gpt-oss-64k hit is Claude Code's, not Ollama's.** Ollama would happily wait longer. A patched Claude Code with a higher timeout might let gpt-oss-64k complete tasks; we haven't tested that.
- **`gpt-oss:20b`'s failures had two flavors:** `exit_code 0` (clean run but score check failed — model did *something* that didn't satisfy the task) and `exit_code 1` (claude itself crashed). Both count as failures here.
- **Cost model held up.** First-call latency for each model was ~25-60 min depending on size; subsequent calls were faster but dominated by output-generation rate. The story in `scripts/eval/README.md` is unchanged.

### What this changes about the recommendation

`qwen3-coder-32k` stays as the default `FORGE_CLAUDE_MODEL` in `src/cc_forge/config.py`. The other two are not viable replacements for this combination of (Claude Code harness, CPU-only host, our task set). The next eval pass (probably issue #54, cloud Ollama services) is where we'd test whether the same models become viable with more compute behind them, or whether something like `qwen3-coder-32k` running on a faster backend gives a meaningful speed-up.

## Pre-flight requirements (run on the forge host)

Before running an eval pass:

- Ollama is reachable on a docker-bridge-accessible interface (not localhost-only). See [`LOCAL-OLLAMA-SETUP.md`](LOCAL-OLLAMA-SETUP.md) — a stock `ollama.service` taking over port 11434 silently breaks this.
- The agent image is built (`docker images cc-forge-agent:latest`).
- The `forge-network` exists and `forge-ollama-proxy` is running.
- The candidate models are pulled (`ollama list` should include each).

Eventually [`forge doctor`](https://github.com/amc-corey-cox/cc_forge/issues/57) will check these automatically.
