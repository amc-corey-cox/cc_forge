#!/bin/bash
# Pass if:
#   - app.py still imports cleanly
#   - no standalone `count` identifier remains
#   - `total_count` appears at least 4 times (one decl + uses)
set -e

[ -f app.py ] || { echo "app.py missing"; exit 2; }

# Syntax check
python3 -c "import ast; ast.parse(open('app.py').read())"

# No bare `count` identifier (won't match `total_count` because _ is a word char)
if grep -wq count app.py; then
    echo "stray 'count' identifier remains"
    exit 1
fi

# Expect at least 4 occurrences of total_count (decl + global + += + print)
if [ "$(grep -c total_count app.py)" -lt 4 ]; then
    echo "expected ≥4 occurrences of total_count, got $(grep -c total_count app.py)"
    exit 1
fi
