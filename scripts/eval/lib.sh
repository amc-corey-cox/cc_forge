#!/bin/bash
# Shared harness helpers for run-task.sh and run-matrix.sh.
#
# Both the warmup and the task runs must configure the agent identically --
# keeping these in one place stops the two from drifting apart.

# Emit the shell that prepares an agent inside the container, before it runs.
# Empty for harnesses that take their config from env vars.
agent_bootstrap() {
    local agent="$1" ollama_url="$2" model="$3"
    [ "$agent" = "opencode" ] || return 0
    # OpenCode reads provider config from a file rather than env vars.
    cat <<EOF
mkdir -p \$HOME/.config/opencode
cat > \$HOME/.config/opencode/opencode.json <<'OCJSON'
{
  "permission": { "bash": "allow", "edit": "allow", "webfetch": "allow" },
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama",
      "options": { "baseURL": "$ollama_url/v1" },
      "models": { "$model": { "name": "$model" } }
    }
  }
}
OCJSON
EOF
}

# Emit the in-container command that runs one prompt, with shell-safe quoting.
agent_cmd() {
    local agent="$1" prompt="$2" model="$3"
    case "$agent" in
        claude)
            printf 'claude -p %q --no-session-persistence --output-format json --model %q --dangerously-skip-permissions' \
                "$prompt" "$model"
            ;;
        opencode)
            # Model is addressed as provider/model; the provider is named in the
            # config written by agent_bootstrap.
            printf 'opencode run -m ollama/%q --print-logs %q' "$model" "$prompt"
            ;;
        *)
            echo "Unknown AGENT: $agent (expected 'claude' or 'opencode')" >&2
            return 1
            ;;
    esac
}
