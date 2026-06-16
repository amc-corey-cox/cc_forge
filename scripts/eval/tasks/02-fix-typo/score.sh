#!/bin/bash
# Pass if README.md contains "Hello World" (typo fixed). Runs in /workspace.
set -e

[ -f README.md ] || { echo "README.md missing"; exit 2; }
grep -q "Hello World" README.md
