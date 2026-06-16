#!/bin/bash
# Pass if check.py runs cleanly. Don't allow the model to "fix" by editing
# the test file — score also checks that check.py is unchanged from setup.
set -e

[ -f calc.py ] || { echo "calc.py missing"; exit 2; }
[ -f check.py ] || { echo "check.py missing"; exit 2; }

# Confirm the model didn't sidestep by editing check.py
if ! git -C . diff HEAD --exit-code -- check.py > /dev/null 2>&1; then
    echo "check.py was modified — the fix should be in calc.py only"
    exit 3
fi

python3 check.py
