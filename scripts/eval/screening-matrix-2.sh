#!/bin/bash
# Screening matrix 2: candidates beyond the initial Qwen/GPT-OSS family.
# Documented in docs/CLAUDE-CODE-LOCAL-MODELS.md ("Screening matrix 2 — candidates").
#
# Usage (on the forge host, after `ollama pull` for each model below):
#   ./scripts/eval/screening-matrix-2.sh
#
# Or to do a tool-support dry-run without launching the matrix:
#   ./scripts/eval/screening-matrix-2.sh --check
#
# This script captures the standard invocation (run-matrix.sh + the agreed
# model list) so we don't reconstruct it by hand every time. The full matrix
# is the same shape as matrix 1: 6 tasks per model, run-matrix.sh pre-warms
# each model once before running tasks serially.

set -euo pipefail

# Candidates for screening matrix 2. Ollama names; ! prefix marks the
# carry-over baseline from matrix 1 (we already trust it works in this harness).
MODELS=(
    "qwen3-coder-32k"   # carry-over baseline
    "devstral:24b"      # Mistral, agentic-coding-specialized
    "olmo-3.1:32b"      # Allen AI, generalist + fully open, declared tools support
    "granite4.1:8b"     # IBM Research, Apache 2.0
    "gemma3:12b"        # Google. Gemma 4 (12b) requires newer Ollama than 0.15.4; fell back to 3.
    "phi4:14b"          # Microsoft, strong-per-byte
)

# Tool-support pre-flight. Claude Code's harness requires tool calling — a
# model that lacks it (e.g. qwen:72b in matrix 1) will fail every task with
# Ollama returning HTTP 400 immediately. Catch this before sinking hours of
# wall-clock by checking `ollama show <model>` for the `tools` capability.
preflight_models() {
    local kept=()
    local rejected=()
    for m in "${MODELS[@]}"; do
        if ollama show "$m" 2>/dev/null | grep -qi "^\s*tools\s*$"; then
            kept+=("$m")
        else
            rejected+=("$m")
        fi
    done

    if [ ${#rejected[@]} -gt 0 ]; then
        echo "These models will be SKIPPED (no 'tools' capability per ollama show):"
        for m in "${rejected[@]}"; do
            echo "  - $m"
        done
        echo
    fi

    echo "These models will be included in the matrix:"
    for m in "${kept[@]}"; do
        echo "  - $m"
    done
    echo

    # Set the env var for run-matrix.sh
    SELECTED_MODELS="${kept[*]}"
    export SELECTED_MODELS
}

# Verify everything is pulled before starting — fail fast if not.
verify_pulled() {
    local missing=()
    for m in "${MODELS[@]}"; do
        if ! ollama list 2>/dev/null | awk '{print $1}' | grep -qFx "$m"; then
            missing+=("$m")
        fi
    done
    if [ ${#missing[@]} -gt 0 ]; then
        echo "These models are not yet pulled on this host:" >&2
        for m in "${missing[@]}"; do
            echo "  - $m" >&2
        done
        echo >&2
        echo "Run \`ollama pull <model>\` for each, then re-run this script." >&2
        exit 1
    fi
}

main() {
    local check_only=0
    if [ "${1:-}" = "--check" ]; then
        check_only=1
    fi

    echo "=== Pre-flight: pulled models ==="
    verify_pulled
    echo "All ${#MODELS[@]} models present in ollama list."
    echo

    echo "=== Pre-flight: tool calling support ==="
    preflight_models

    if [ "$check_only" -eq 1 ]; then
        echo "Check-only mode — not launching matrix."
        exit 0
    fi

    SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
    RUN_ID="${RUN_ID:-screening-matrix-2-$(date -u +%Y%m%dT%H%M%SZ)}"
    OUTPUT_BASE="eval-results/$RUN_ID"
    OLLAMA_URL="${OLLAMA_URL:-http://forge-ollama-proxy:11434}"

    echo "=== Launching matrix ==="
    echo "  run_id: $RUN_ID"
    echo "  output: $OUTPUT_BASE"
    echo "  ollama: $OLLAMA_URL"
    echo "  models: $SELECTED_MODELS"
    echo

    RUN_ID="$RUN_ID" OUTPUT_BASE="$OUTPUT_BASE" MODELS="$SELECTED_MODELS" \
        OLLAMA_URL="$OLLAMA_URL" \
        "$SCRIPT_DIR/run-matrix.sh"
}

main "$@"
