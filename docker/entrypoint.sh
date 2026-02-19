#!/bin/bash
set -e

# CC Forge Agent Entrypoint
# Clones the repo from Forgejo, checks out the branch, and starts the agent.

if [ -z "$REPO_URL" ]; then
    echo "ERROR: REPO_URL not set"
    exit 1
fi

# Configure git credential helper for token-based Forgejo auth
if [ -n "$FORGEJO_TOKEN" ] && [ -n "$FORGEJO_URL" ]; then
    # Extract protocol and host from FORGEJO_URL
    FORGEJO_PROTO=$(echo "$FORGEJO_URL" | sed 's|://.*||')
    FORGEJO_HOST=$(echo "$FORGEJO_URL" | sed 's|https\?://||' | sed 's|/.*||')
    # Write credentials file with restrictive permissions
    CRED_FILE="$HOME/.git-credentials"
    echo "${FORGEJO_PROTO}://forge-agent:${FORGEJO_TOKEN}@${FORGEJO_HOST}" > "$CRED_FILE"
    chmod 600 "$CRED_FILE"
    git config --global credential.helper "store --file=$CRED_FILE"
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
