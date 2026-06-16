#!/bin/bash
# Run the full eval matrix: each model in $MODELS is pre-warmed once, then all
# tasks in $TASKS_DIR are run against it serially while the model is hot.
#
# Usage:
#   MODELS="qwen3-coder-32k gpt-oss:20b" \
#   OLLAMA_URL=http://forge-ollama-proxy:11434 \
#   run-matrix.sh
#
# Output: eval-results/$RUN_ID/<model>/<task>/{prompt.txt,output.json,stderr.log,meta.json}
#         plus eval-results/$RUN_ID/_warmup/<model>/* for the warmup probe.
#
# Performance characteristics (see README.md for the full cost model):
# - First call to a model: ~25-30 min on CPU (model load + Claude Code system
#   prompt prefill). This is the warmup.
# - Subsequent calls: dominated by output generation rate (~0.5 tok/s on CPU).

set -euo pipefail

MODELS="${MODELS:?MODELS env required, space-separated list of Ollama model names}"
TASKS_DIR="${TASKS_DIR:-$(dirname "$0")/tasks}"
OLLAMA_URL="${OLLAMA_URL:-http://forge-ollama-proxy:11434}"
RUN_ID="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
OUTPUT_BASE="eval-results/$RUN_ID"
AGENT_IMAGE="${AGENT_IMAGE:-cc-forge-agent:latest}"

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

[ -d "$TASKS_DIR" ] || { echo "TASKS_DIR not found: $TASKS_DIR" >&2; exit 1; }

mkdir -p "$OUTPUT_BASE"
echo "Eval run: $RUN_ID"
echo "  models: $MODELS"
echo "  tasks_dir: $TASKS_DIR"
echo "  ollama_url: $OLLAMA_URL"
echo "  output: $OUTPUT_BASE"

# Build a small "task" with a trivial prompt purely to populate the model's
# KV cache for Claude Code's system prompt. Reuses the same docker run path so
# whatever Claude Code prefix gets cached is the same prefix the real tasks
# will benefit from.
warmup() {
    local model="$1"
    local warmup_out="$OUTPUT_BASE/_warmup/$model"
    mkdir -p "$warmup_out"
    echo "  warming $model (first call to a model is ~25-30 min on CPU)..."
    local start end
    start=$(date +%s)
    local cmd
    cmd=$(printf 'claude -p %q --no-session-persistence --output-format json --model %q --dangerously-skip-permissions' \
        "OK" "$model")
    docker run --rm \
        --network forge-network \
        -e ANTHROPIC_BASE_URL="$OLLAMA_URL" \
        -e ANTHROPIC_AUTH_TOKEN=ollama \
        --entrypoint /bin/bash \
        "$AGENT_IMAGE" \
        -c "$cmd" \
        > "$warmup_out/output.json" 2> "$warmup_out/stderr.log" || true
    end=$(date +%s)
    echo "  warmup duration: $((end - start))s"
}

export OUTPUT_BASE OLLAMA_URL AGENT_IMAGE

for model in $MODELS; do
    echo
    echo "=== Model: $model ==="
    warmup "$model"

    for task_dir in "$TASKS_DIR"/*/; do
        [ -d "$task_dir" ] || continue
        "$SCRIPT_DIR/run-task.sh" "$model" "$task_dir"
    done
done

echo
echo "Done. Results: $OUTPUT_BASE/"
