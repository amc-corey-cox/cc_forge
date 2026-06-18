# Claude Code with Local Ollama Models

How Claude Code performs against local Ollama models, and which ones we recommend. Part of the [Track 1 evaluation](https://github.com/amc-corey-cox/cc_forge/issues) of the agent-architecture exploration.

> **Status:** Screening matrices 1 (2026-06-17) and 2 (2026-06-18) complete. Headline result: `qwen3-coder-32k` is still the only model in either shortlist that meaningfully drives Claude Code in this harness. Matrix 2 added five more candidates (Devstral, OLMo, Granite, Gemma 3, Phi-4) — three were filtered by the tool-support pre-flight, the other two ran but failed every capability task. Recommendation stands as the dogfood default.

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

## Results — screening matrix 2 (2026-06-18)

Following on the community research in #53, the second screening run broadens beyond the initial Qwen/GPT-OSS family to test whether other open-weight families produce different capability profiles in our harness. The shortlist deliberately spans:

- **An agentic-coding-specialized model** (Devstral Small 2)
- **A fully-open research-style model** (OLMo 3.1 — releases weights + data + training code in the AI2 mold)
- **An enterprise-open Apache-2.0 model** (IBM Granite 4.1)
- **A recent Google release** (Gemma 3 — captures the "what's hot from a major lab this month" angle; Gemma 4's 12B variant needs a newer Ollama than the host runs)
- **A small-but-strong reasoning model** (Phi-4)
- **`qwen3-coder-32k` retained as the carryover baseline** — matrix 1's only 5/5 capability pass

### Shortlist

| Model | Ollama name | Approx size | Why | Origin |
|-------|-------------|-------------|-----|--------|
| `qwen3-coder-32k` | `qwen3-coder-32k` | 17 GB | Carry-over baseline; 5/5 in matrix 1 | Alibaba / Qwen |
| Devstral Small 2 | `devstral:24b` | 14 GB | Mistral, Dec 2025, explicitly agentic-tuned, 256K context, Apache 2.0 | Mistral AI (France) |
| OLMo 3.1 32B | `olmo-3.1:32b` | 19 GB | Generalist comparison from a fully-open research team | Allen AI / AI2 (US) |
| IBM Granite 4.1-8B | `granite4.1:8b` | 5 GB | Apache 2.0, fast small comparison, IBM Research's open-source release pattern | IBM Research (US) |
| Gemma 3 12B | `gemma3:12b` | 8 GB | Google. Gemma 4's 12B variant needs Ollama newer than 0.15.4 (the version on the forge host); using 3 as the practical near-equivalent. | Google DeepMind (US) |
| Phi-4 | `phi4:14b` | 9 GB | Microsoft, strong reasoning per byte | Microsoft Research (US) |

### Pre-flight result on the forge host (2026-06-17)

Of the six candidates above, **only three declare `tools` capability** in their Ollama manifest as pulled:

- ✅ `qwen3-coder-32k` (carryover)
- ✅ `devstral:24b`
- ✅ `granite4.1:8b`
- ❌ `olmo-3.1:32b` — capabilities: `completion, thinking` (no tools)
- ❌ `gemma3:12b` — capabilities: `completion, vision` (no tools)
- ❌ `phi4:14b` — capabilities: `completion` (no tools)

Web research suggested these models had tool calling, but the variants actually pulled via the standard `ollama pull <name>` don't expose it. Without `tools` in the capabilities list, Ollama returns HTTP 400 immediately on the first Claude Code request — they can't participate in the matrix.

This makes the pre-flight check (`ollama show <model> | grep tools`) genuinely load-bearing: it's not redundant with web/blog research, because the blog research and the model-as-pulled don't always agree. The check is now built into `scripts/eval/screening-matrix-2.sh`.

There may be tool-capable variants of OLMo / Phi-4 we didn't pull (e.g., specialized instruction-tuned releases). Adding them to the matrix is straightforward but requires pulling additional ~10-20GB each and re-running the check — a follow-up if matrix 2's results suggest the gap is worth investigating.

### Matrix as run

Three models × six tasks. Run-runner is `screening-matrix-2.sh`; the script filters to only tools-capable models, so the unviable three above are skipped automatically.

| Task | qwen3-coder-32k | devstral:24b | granite4.1:8b |
|------|-----------------|--------------|---------------|
| 01-sanity-pong | ran (8 min) | ran (5 min) | ran (3 min) |
| 02-fix-typo | **PASS** (28 min) | fail (11 min) | fail (5 min) |
| 03-add-docstring | **PASS** (28 min) | fail (21 min) | fail (4 min) |
| 04-rename-variable | **PASS** (29 min) | fail (10 min) | fail (4 min) |
| 05-fix-failing-test | **PASS** (31 min) | fail (11 min) | fail (4 min) |
| 06-implement-from-stub | **PASS** (36 min) | fail (6 min) | fail (4 min) |
| **Capability pass-rate** | **5/5** | **0/5** | **0/5** |

qwen3-coder-32k's column carries over verbatim from matrix 1 — we did not re-run it for this matrix.

### Interpretation

- **qwen3-coder-32k — recommended (unchanged).** Same 5/5 result as matrix 1. Still the only model on either shortlist that meaningfully drives Claude Code in this harness.
- **devstral:24b — fails despite declared `tools` capability.** Every failed task ended after exactly one model turn with `exit_code 0`. The model acknowledges the request ("I'll help you fix the typo in `README.md`. Let me look at the file."), but then never emits an actual tool call — it just stops, sometimes outputting fake skill tags (`<skill skill="Glob"></skill>`) as text, sometimes admitting "I don't have access to the files or tools." The Ollama manifest says `tools` is supported; Devstral's behavior in this harness says otherwise. Possibly a tokenizer or chat-template mismatch between Devstral's tool-calling format and what Claude Code's harness expects from Ollama — but not something we can fix from the harness side.
- **granite4.1:8b — same shape as devstral, smaller and faster.** 0/5, same single-turn narration pattern. The 8B size means each failed task only burned ~4 min — cheap failure, but a failure all the same. Granite did not crash; Claude Code exited cleanly each time with the model just refusing to act.
- **The pre-flight filter held its weight.** Three of six candidates (OLMo 3.1, Gemma 3, Phi-4) were skipped without burning any runtime — they don't declare `tools` in their Ollama manifests. That saved an estimated 6-12 hours of wall-clock that would have ended in `HTTP 400 does not support tools` from Ollama.

### Caveat: pre-flight bug discovered mid-matrix

The first attempt to run matrix 2 incorrectly skipped `devstral:24b` despite its having `tools` capability. Root cause: `set -o pipefail` + `grep -q` — once grep matched and exited, it SIGPIPE'd the still-writing `ollama show`, and the non-zero pipeline exit propagated as a falsy `if`. Larger Ollama manifests (like Devstral's 21-line output) were just long enough to trip it. Fix in `scripts/eval/screening-matrix-2.sh`: capture `ollama show` output into a variable first, then grep. Worth recording because the same bash gotcha will bite future preflight scripts that combine pipefail with grep -q.

### What this changes about the recommendation

Nothing. `qwen3-coder-32k` remains the default `FORGE_CLAUDE_MODEL`. The candidates that ran in matrix 2 (Devstral, Granite) failed in a way that suggests an Ollama-side or model-side tool-call format mismatch rather than something a different prompt or harness tweak would unlock. The next eval pass (issue #54, cloud Ollama services) is where we'd test whether the same models become viable with a different inference backend that handles tool calls differently.

## Pre-flight requirements (run on the forge host)

Before running an eval pass:

- Ollama is reachable on a docker-bridge-accessible interface (not localhost-only). See [`LOCAL-OLLAMA-SETUP.md`](LOCAL-OLLAMA-SETUP.md) — a stock `ollama.service` taking over port 11434 silently breaks this.
- The agent image is built (`docker images cc-forge-agent:latest`).
- The `forge-network` exists and `forge-ollama-proxy` is running.
- The candidate models are pulled (`ollama list` should include each).
- Each candidate declares `tools` capability: `ollama show <model> | grep -i tools`. Without it, Ollama returns HTTP 400 immediately and the model can't drive Claude Code. `scripts/eval/screening-matrix-2.sh` does this check automatically and refuses to include models that fail it.

Eventually [`forge doctor`](https://github.com/amc-corey-cox/cc_forge/issues/57) will check these automatically.

## Confirmed unusable for this harness

Models we exercised as matrix candidates against Claude Code's harness and shown not to drive it. Useful for not re-pulling them for future forge eval passes. **Note:** scoped to candidates we deliberately tested for this application. Models that happen to be on the host for unrelated purposes — even ones that lack `tools` capability — are out of scope; only remove if you know you don't use them elsewhere.

| Model | Why it fails | Source |
|-------|--------------|--------|
| `gpt-oss:20b` | Runs but fails every capability check (0/5) | Matrix 1 |
| `gpt-oss-64k` | 5/6 hit Claude Code's HTTP timeout with zero output | Matrix 1 |
| `devstral:24b` | `tools` declared but never emits real tool calls (0/5) | Matrix 2 |
| `granite4.1:8b` | Same single-turn narration pattern as Devstral (0/5) | Matrix 2 |
| `olmo-3.1:32b` | No `tools` capability in Ollama manifest | Matrix 2 pre-flight |
| `gemma3:12b` | No `tools` capability in Ollama manifest | Matrix 2 pre-flight |
| `phi4:14b` | No `tools` capability in Ollama manifest | Matrix 2 pre-flight |

The Devstral / Granite failure mode is identical: `exit_code 0`, `num_turns: 1`, model emits a polite acknowledgment ("I'll help you fix that, let me look at the file…") and then never issues a tool call. The Ollama manifest says they support tools; their actual output stream in this harness doesn't. Possibly a tokenizer or chat-template mismatch — not something fixable from our side without a different inference backend.
