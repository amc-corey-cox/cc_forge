#!/bin/bash
# Workspace setup for 02-fix-typo. Runs inside the agent container with cwd=/workspace.
set -e

git init -q
git config user.email "eval@forge.local"
git config user.name "Eval Setup"
echo "# Hello Wrold" > README.md
git add .
git commit -qm "init"
