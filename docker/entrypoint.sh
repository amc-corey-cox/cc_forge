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

echo "Repository cloned. Starting agent..."
echo ""

case "${FORGE_AGENT:-claude}" in
    claude)
        echo "Starting Claude Code..."
        exec claude
        ;;
    aider)
        echo "Starting Aider..."
        exec aider --model "ollama/${AIDER_MODEL:-llama3.1}"
        ;;
    *)
        echo "Unknown agent: $FORGE_AGENT. Dropping to shell."
        exec /bin/bash
        ;;
esac
