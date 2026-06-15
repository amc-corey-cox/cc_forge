#!/bin/bash
set -e

# CC Forge Agent Entrypoint
# Clones the repo from Forgejo, checks out the branch, and starts the agent.

if [ -z "$REPO_URL" ]; then
    echo "ERROR: REPO_URL not set"
    exit 1
fi

# Forge injects .git-credentials before start; fall back to env vars for manual runs.
if [ ! -f "$HOME/.git-credentials" ] && [ -n "$FORGEJO_TOKEN" ] && [ -n "$FORGEJO_URL" ]; then
    FORGEJO_PROTO=$(echo "$FORGEJO_URL" | sed 's|://.*||')
    FORGEJO_HOST=$(echo "$FORGEJO_URL" | sed 's|https\?://||' | sed 's|/.*||')
    # Percent-encode the token so reserved chars (@ : /) don't corrupt the URL.
    ENC_TOKEN=$(python3 -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$FORGEJO_TOKEN")
    echo "${FORGEJO_PROTO}://forge-agent:${ENC_TOKEN}@${FORGEJO_HOST}" > "$HOME/.git-credentials"
    chmod 600 "$HOME/.git-credentials"
fi

echo "Cloning $REPO_URL (branch: ${REPO_BRANCH:-main})..."
git clone --branch "${REPO_BRANCH:-main}" "$REPO_URL" /workspace/repo 2>&1 || {
    echo "Clone failed. Trying without --branch (repo may be empty)..."
    git clone "$REPO_URL" /workspace/repo 2>&1 || {
        echo "ERROR: Could not clone $REPO_URL"
        exit 1
    }
}

cd /workspace/repo

echo "Repository cloned. Ready for agent."
echo ""

# Keep container alive — the forge CLI will exec the agent interactively.
# TTL prevents orphaned containers if the CLI dies without cleanup.
FORGE_AGENT_TTL_SECONDS="${FORGE_AGENT_TTL_SECONDS:-86400}"
exec sleep "$FORGE_AGENT_TTL_SECONDS"
