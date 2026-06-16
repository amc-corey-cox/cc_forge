#!/bin/bash
set -e

git init -q
git config user.email "eval@forge.local"
git config user.name "Eval Setup"

cat > calc.py <<'PY'
def add(a, b):
    return a - b  # bug: should be +
PY

cat > check.py <<'PY'
from calc import add

assert add(2, 3) == 5, f"add(2, 3) expected 5, got {add(2, 3)}"
assert add(0, 0) == 0
assert add(-1, 1) == 0
assert add(10, 20) == 30
print("OK")
PY

git add .
git commit -qm "init"
