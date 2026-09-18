#!/bin/bash
# Shared harness helpers for run-task.sh and run-matrix.sh.
#
# Both the warmup and the task runs must configure the agent identically --
# keeping these in one place stops the two from drifting apart.

# Normalize a model name to OpenCode's provider/model form. Only the ollama
# provider is configured by agent_bootstrap, so anything else is rejected rather
# than launched against a provider the config doesn't define.
opencode_qualify_model() {
    local model="$1"
    case "$model" in
        ollama/*) printf '%s' "$model" ;;
        */*)
            echo "AGENT=opencode supports only the 'ollama' provider, got '$model'" >&2
            return 1
            ;;
        *) printf 'ollama/%s' "$model" ;;
    esac
}

# Emit the shell that prepares an agent inside the container, before it runs.
# Empty for harnesses that take their config from env vars.
agent_bootstrap() {
    local agent="$1" ollama_url="$2" model="$3"
    [ "$agent" = "opencode" ] || return 0
    # OpenCode reads provider config from a file rather than env vars. Built with
    # jq so a model name or URL containing a quote or backslash can't produce
    # invalid JSON -- unlikely with Ollama names, but it would fail obscurely.
    local qualified bare config
    qualified=$(opencode_qualify_model "$model") || return 1
    bare=${qualified#ollama/}
    config=$(jq -n --arg url "$ollama_url/v1" --arg model "$bare" '{
        permission: { bash: "allow", edit: "allow", webfetch: "allow" },
        provider: {
            ollama: {
                npm: "@ai-sdk/openai-compatible",
                name: "Ollama",
                options: { baseURL: $url },
                models: { ($model): { name: $model } }
            }
        }
    }')
    cat <<EOF
mkdir -p \$HOME/.config/opencode
cat > \$HOME/.config/opencode/opencode.json <<'OCJSON'
$config
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
            local qualified
            qualified=$(opencode_qualify_model "$model") || return 1
            printf 'opencode run -m %q --print-logs %q' "$qualified" "$prompt"
            ;;
        *)
            echo "Unknown AGENT: $agent (expected 'claude' or 'opencode')" >&2
            return 1
            ;;
    esac
}
