#!/bin/bash
set -e

git init -q
git config user.email "eval@forge.local"
git config user.name "Eval Setup"

cat > palindrome.py <<'PY'
def is_palindrome(s):
    """Return True if s is a palindrome (reads the same forwards and backwards), False otherwise."""
    pass  # TODO: implement
PY

cat > check.py <<'PY'
from palindrome import is_palindrome

assert is_palindrome("") is True, f'is_palindrome("") expected True, got {is_palindrome("")}'
assert is_palindrome("a") is True
assert is_palindrome("aa") is True
assert is_palindrome("aba") is True
assert is_palindrome("racecar") is True
assert is_palindrome("ab") is False
assert is_palindrome("abc") is False
assert is_palindrome("abba") is True
assert is_palindrome("abca") is False
print("OK")
PY

git add .
git commit -qm "init"
