#!/bin/bash
# Run a single (model, task) through the Claude Code harness.
#
# Usage:
#   OLLAMA_URL=http://forge-ollama-proxy:11434 \
#   OUTPUT_BASE=eval-results/<run-id> \
#   run-task.sh <model> <task-dir>
#
# Captures the agent's structured JSON output, stderr, and wall-clock duration
# into $OUTPUT_BASE/<model>/<task>/. Does NOT pre-warm the model; orchestrate
# pre-warming + iteration via run-matrix.sh.

set -euo pipefail

MODEL="${1:?model name required}"
TASK_DIR="${2:?task dir required}"
OLLAMA_URL="${OLLAMA_URL:-http://forge-ollama-proxy:11434}"
OUTPUT_BASE="${OUTPUT_BASE:-eval-results/$(date -u +%Y%m%dT%H%M%SZ)}"
AGENT_IMAGE="${AGENT_IMAGE:-cc-forge-agent:latest}"

PROMPT_FILE="$TASK_DIR/prompt.txt"
[ -f "$PROMPT_FILE" ] || { echo "no prompt.txt in $TASK_DIR" >&2; exit 1; }

TASK_NAME=$(basename "$TASK_DIR")
OUT="$OUTPUT_BASE/$MODEL/$TASK_NAME"
mkdir -p "$OUT"
cp "$PROMPT_FILE" "$OUT/prompt.txt"

PROMPT=$(cat "$PROMPT_FILE")

# Build the in-container claude command with shell-safe quoting.
CLAUDE_CMD=$(printf 'claude -p %q --no-session-persistence --output-format json --model %q --dangerously-skip-permissions' \
    "$PROMPT" "$MODEL")

echo "[$(date +%H:%M:%S)] model=$MODEL task=$TASK_NAME"
START=$(date +%s)

# Capture exit code so meta.json reflects actual success/failure — failed runs
# should not look like valid task outputs to downstream analysis.
docker run --rm \
    --network forge-network \
    -e ANTHROPIC_BASE_URL="$OLLAMA_URL" \
    -e ANTHROPIC_AUTH_TOKEN=ollama \
    --entrypoint /bin/bash \
    "$AGENT_IMAGE" \
    -c "$CLAUDE_CMD" \
    > "$OUT/output.json" 2> "$OUT/stderr.log" && EXIT_CODE=0 || EXIT_CODE=$?

END=$(date +%s)
DURATION=$((END - START))

# Capture a small meta file alongside the raw output.
printf '{"model":%s,"task":%s,"duration_s":%d,"exit_code":%d,"ollama_url":%s,"timestamp":%s}\n' \
    "$(printf '%s' "$MODEL" | jq -R .)" \
    "$(printf '%s' "$TASK_NAME" | jq -R .)" \
    "$DURATION" \
    "$EXIT_CODE" \
    "$(printf '%s' "$OLLAMA_URL" | jq -R .)" \
    "$(date -u +'%Y-%m-%dT%H:%M:%SZ' | jq -R .)" \
    > "$OUT/meta.json"

if [ "$EXIT_CODE" -eq 0 ]; then
    echo "[$(date +%H:%M:%S)]   ${DURATION}s → $OUT/"
else
    echo "[$(date +%H:%M:%S)]   FAILED exit=$EXIT_CODE after ${DURATION}s → $OUT/" >&2
fi
