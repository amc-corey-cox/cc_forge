#!/bin/bash
set -e

git init -q
git config user.email "eval@forge.local"
git config user.name "Eval Setup"

cat > app.py <<'PY'
count = 0


def increment():
    global count
    count += 1


def show():
    print(count)
PY

git add .
git commit -qm "init"
