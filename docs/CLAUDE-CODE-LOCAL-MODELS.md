# Claude Code with Local Ollama Models

How Claude Code performs against local Ollama models, and which ones we recommend. Part of the [Track 1 evaluation](https://github.com/amc-corey-cox/cc_forge/issues) of the agent-architecture exploration.

> **Status:** Initial cost-model captured (see below). Matrix results pending the first evaluation pass.

## Headline cost model

Performance has a sharp two-mode profile:

- **First call to a model:** ~25-30 minutes wall-clock on CPU, regardless of how short the prompt is. ~95% of that is Claude Code's large invariant system prompt being prefilled through the model.
- **Subsequent calls to the same model:** seconds for short responses, dominated by output generation rate (~0.5 tok/sec on CPU). Ollama's KV cache reuses the system-prompt prefix.

Practical implication: a forge session against a fresh local model will appear hung for ~25 minutes on the first prompt. After that, it behaves like a normal CPU-inference session.

Full mechanism, decomposition, empirical measurements, and operational consequences are documented in [`scripts/eval/README.md`](../scripts/eval/README.md) — that's where the eval harness lives and where this understanding is canonically maintained.

## Running an eval matrix

See `scripts/eval/README.md` for the harness invocation. Output lands in `eval-results/<run-id>/`.

## Results

_Will be populated after the first matrix pass. Until then, no recommendation — use `qwen3-coder-32k` as the dogfood default (current `FORGE_CLAUDE_MODEL` default in `config.py`)._

## Pre-flight requirements (run on the forge host)

Before running an eval pass:

- Ollama is reachable on a docker-bridge-accessible interface (not localhost-only). See the [Ollama systemd notes](LOCAL-OLLAMA-SETUP.md#stock-ollamaservice-reactivation-after-upgrades) — a stock `ollama.service` taking over port 11434 silently breaks this.
- The agent image is built (`docker images cc-forge-agent:latest`).
- The `forge-network` exists and `forge-ollama-proxy` is running.
- The candidate models are pulled (`ollama list` should include each).

Eventually [`forge doctor`](https://github.com/amc-corey-cox/cc_forge/issues/57) will check these automatically.
