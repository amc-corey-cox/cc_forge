#!/bin/bash
# Run a single (model, task) through the Claude Code harness.
#
# Usage:
#   OLLAMA_URL=http://forge-ollama-proxy:11434 \
#   OUTPUT_BASE=eval-results/<run-id> \
#   run-task.sh <model> <task-dir>
#
# Per-task layout (each file optional except prompt.txt):
#   <task-dir>/prompt.txt   - required: user prompt sent to claude -p
#   <task-dir>/setup.sh     - optional: runs in container before claude (cwd=/workspace)
#   <task-dir>/score.sh     - optional: runs in container after claude (cwd=/workspace)
#                              exit 0 = pass, non-zero = fail (recorded in meta.json)
#   <task-dir>/expect.md    - optional: human-readable success criteria
#
# Inside the container:
#   /workspace  - fresh per run; setup.sh populates, claude modifies, score.sh checks
#   /task       - read-only mount of the task source dir
#   /meta       - read-write mount of $OUT (where output.json, meta.json land)
#
# Outputs in $OUT = $OUTPUT_BASE/<model>/<task>/:
#   prompt.txt          copy of the task's prompt
#   output.json         claude -p's full structured response
#   stderr.log          anything claude wrote to stderr
#   setup.log           setup.sh output (only if setup.sh ran)
#   score.log           score.sh output (only if score.sh ran)
#   score-exit          score.sh exit code (only if score.sh ran)
#   meta.json           {model, task, duration_s, exit_code, score?, ollama_url, timestamp}
#   workspace/          final state of /workspace after claude exited

set -euo pipefail

MODEL="${1:?model name required}"
TASK_DIR="${2:?task dir required}"
OLLAMA_URL="${OLLAMA_URL:-http://forge-ollama-proxy:11434}"
OUTPUT_BASE="${OUTPUT_BASE:-eval-results/$(date -u +%Y%m%dT%H%M%SZ)}"
AGENT_IMAGE="${AGENT_IMAGE:-cc-forge-agent:latest}"

PROMPT_FILE="$TASK_DIR/prompt.txt"
[ -f "$PROMPT_FILE" ] || { echo "no prompt.txt in $TASK_DIR" >&2; exit 1; }

TASK_NAME=$(basename "$TASK_DIR")
TASK_DIR_ABS=$(cd "$TASK_DIR" && pwd)

# Sanitize model name for filesystem use. Ollama names like "qwen:72b" contain
# colons that break docker bind-mount path parsing if used directly. The original
# name still gets passed to `claude -p --model` and recorded in meta.json.
MODEL_PATH=$(echo "$MODEL" | tr ':/' '__')

OUT="$OUTPUT_BASE/$MODEL_PATH/$TASK_NAME"
# Clear any stale artifacts from a previous run into the same OUTPUT_BASE so
# /workspace is genuinely fresh and conditional outputs (setup.log, score.log,
# score-exit) from a prior run don't leak into this run's meta.json.
rm -rf "$OUT"
mkdir -p "$OUT/workspace"
cp "$PROMPT_FILE" "$OUT/prompt.txt"
OUT_ABS=$(cd "$OUT" && pwd)
WS_ABS=$(cd "$OUT/workspace" && pwd)

PROMPT=$(cat "$PROMPT_FILE")

# Build the in-container claude command with shell-safe quoting.
CLAUDE_CMD=$(printf 'claude -p %q --no-session-persistence --output-format json --model %q --dangerously-skip-permissions' \
    "$PROMPT" "$MODEL")

# Inline script run inside the container. $CLAUDE_CMD is expanded by the outer
# shell; \$ sequences are escaped so they resolve inside the container.
# `set -u` (no `-e`) lets us continue past a failed claude so score.sh still runs.
INNER=$(cat <<EOF
set -uo pipefail
cd /workspace
if [ -f /task/setup.sh ]; then
    bash /task/setup.sh > /meta/setup.log 2>&1
    SETUP_EXIT=\$?
    if [ "\$SETUP_EXIT" -ne 0 ]; then
        echo "setup.sh failed (exit \$SETUP_EXIT)" >> /meta/setup.log
        exit 90
    fi
fi
$CLAUDE_CMD > /meta/output.json 2> /meta/stderr.log
CLAUDE_EXIT=\$?
if [ -f /task/score.sh ]; then
    (cd /workspace && bash /task/score.sh) > /meta/score.log 2>&1
    echo \$? > /meta/score-exit
fi
exit \$CLAUDE_EXIT
EOF
)

echo "[$(date +%H:%M:%S)] model=$MODEL task=$TASK_NAME"
START=$(date +%s)

docker run --rm \
    --network forge-network \
    -v "$TASK_DIR_ABS:/task:ro" \
    -v "$WS_ABS:/workspace" \
    -v "$OUT_ABS:/meta" \
    -e ANTHROPIC_BASE_URL="$OLLAMA_URL" \
    -e ANTHROPIC_AUTH_TOKEN=ollama \
    --entrypoint /bin/bash \
    "$AGENT_IMAGE" \
    -c "$INNER" \
    && EXIT_CODE=0 || EXIT_CODE=$?

END=$(date +%s)
DURATION=$((END - START))

# Score result (if score.sh ran)
SCORE_FIELD=""
SCORE_DISPLAY=""
if [ -f "$OUT/score-exit" ]; then
    SCORE_EXIT=$(cat "$OUT/score-exit")
    if [ "$SCORE_EXIT" -eq 0 ]; then
        SCORE_FIELD=',"score":"pass","score_exit":0'
        SCORE_DISPLAY=" [score: pass]"
    else
        SCORE_FIELD=",\"score\":\"fail\",\"score_exit\":$SCORE_EXIT"
        SCORE_DISPLAY=" [score: fail($SCORE_EXIT)]"
    fi
fi

printf '{"model":%s,"task":%s,"duration_s":%d,"exit_code":%d%s,"ollama_url":%s,"timestamp":%s}\n' \
    "$(printf '%s' "$MODEL" | jq -R .)" \
    "$(printf '%s' "$TASK_NAME" | jq -R .)" \
    "$DURATION" \
    "$EXIT_CODE" \
    "$SCORE_FIELD" \
    "$(printf '%s' "$OLLAMA_URL" | jq -R .)" \
    "$(date -u +'%Y-%m-%dT%H:%M:%SZ' | jq -R .)" \
    > "$OUT/meta.json"

if [ "$EXIT_CODE" -eq 0 ]; then
    echo "[$(date +%H:%M:%S)]   ${DURATION}s${SCORE_DISPLAY} → $OUT/"
else
    echo "[$(date +%H:%M:%S)]   FAILED exit=$EXIT_CODE after ${DURATION}s${SCORE_DISPLAY} → $OUT/" >&2
fi
