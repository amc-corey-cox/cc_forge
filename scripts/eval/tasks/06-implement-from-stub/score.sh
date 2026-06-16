#!/bin/bash
# Pass if check.py runs cleanly with the model's implementation. Reject edits
# to check.py — the implementation has to live in palindrome.py.
set -e

[ -f palindrome.py ] || { echo "palindrome.py missing"; exit 2; }
[ -f check.py ] || { echo "check.py missing"; exit 2; }

if ! git -C . diff HEAD --exit-code -- check.py > /dev/null 2>&1; then
    echo "check.py was modified — the implementation should be in palindrome.py only"
    exit 3
fi

python3 check.py
