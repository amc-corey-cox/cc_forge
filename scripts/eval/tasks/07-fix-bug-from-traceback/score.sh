#!/bin/bash
# Pass if check.py runs cleanly. Don't allow the model to "fix" by editing
# the test file — score also checks that check.py is unchanged from setup.
set -e

[ -f check.py ] || { echo "check.py missing"; exit 2; }

# Confirm the model didn't sidestep by editing check.py — compare against the
# root (initial setup) commit so a later commit by the agent can't hide the edit.
ROOT=$(git rev-list --max-parents=0 HEAD | head -1)
if ! git diff --exit-code "$ROOT" -- check.py > /dev/null 2>&1; then
    echo "check.py was modified — the fix should not touch the test file"
    exit 3
fi

python3 check.py
