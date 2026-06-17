# 06-implement-from-stub

## Purpose

Hardest of the initial screening tasks. Tests whether the model can:

- Read a stub + tests and derive what the function should do
- Produce a correct implementation (not just "something that returns True")
- Get edge cases right (empty string, single char) without being told about them explicitly

## Setup state

`/workspace/palindrome.py`:
```python
def is_palindrome(s):
    """Return True if s is a palindrome (reads the same forwards and backwards), False otherwise."""
    pass  # TODO: implement
```

`/workspace/check.py` (multiple assertions including empty-string and odd/even length cases).

## Pass criteria

1. `check.py` is unchanged from initial state
2. `python3 check.py` exits 0

All assertions in `check.py` must pass — including the edge cases:
- empty string `""` → True
- single char `"a"` → True
- equal pair `"aa"` → True
- odd-length palindrome `"aba"`, `"racecar"` → True
- non-palindrome `"ab"`, `"abc"`, `"abca"` → False
- even-length palindrome `"abba"` → True

## Notes

A model returning hardcoded `True` would fail the negative cases. A model checking only `s == s[::-1]` would pass everything (and is the canonical solution). The empty-string case catches implementations that index into `s[0]` without guarding.
