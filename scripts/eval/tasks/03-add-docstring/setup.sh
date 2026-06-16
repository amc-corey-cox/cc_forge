#!/bin/bash
set -e

git init -q
git config user.email "eval@forge.local"
git config user.name "Eval Setup"

cat > app.py <<'PY'
def hello(name):
    return f"Hello, {name}"
PY

git add .
git commit -qm "init"
