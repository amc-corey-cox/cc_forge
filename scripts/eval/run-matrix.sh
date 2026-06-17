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

# Build a small "task" with an explicit terminating prompt purely to populate
# the model's KV cache for Claude Code's system prompt. The prompt has to be
# unambiguous about producing tiny output — vague prompts like just "OK" have
# been observed sending models into multi-turn tool-use loops that don't
# terminate. A 30-minute wall-clock cap (timeout 1800) catches any model that
# still wanders, so a runaway warmup costs ≤30 min instead of hours.
WARMUP_PROMPT="Reply with the single word OK and nothing else."
WARMUP_TIMEOUT_S=1800

warmup() {
    local model="$1"
    local warmup_path
    warmup_path=$(echo "$model" | tr ':/' '__')
    local warmup_out="$OUTPUT_BASE/_warmup/$warmup_path"
    mkdir -p "$warmup_out"
    echo "  warming $model (cap: ${WARMUP_TIMEOUT_S}s)..."
    local start end
    start=$(date +%s)
    local cmd
    cmd=$(printf 'claude -p %q --no-session-persistence --output-format json --model %q --dangerously-skip-permissions' \
        "$WARMUP_PROMPT" "$model")
    timeout "$WARMUP_TIMEOUT_S" docker run --rm \
        --network forge-network \
        -e ANTHROPIC_BASE_URL="$OLLAMA_URL" \
        -e ANTHROPIC_AUTH_TOKEN=ollama \
        --entrypoint /bin/bash \
        "$AGENT_IMAGE" \
        -c "$cmd" \
        > "$warmup_out/output.json" 2> "$warmup_out/stderr.log" \
        && WU_EXIT=0 || WU_EXIT=$?
    end=$(date +%s)
    if [ "$WU_EXIT" -eq 124 ]; then
        echo "  warmup TIMEOUT after $((end - start))s — proceeding to tasks anyway"
    else
        echo "  warmup duration: $((end - start))s (exit $WU_EXIT)"
    fi
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
