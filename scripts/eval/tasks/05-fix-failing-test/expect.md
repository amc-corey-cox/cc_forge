# 05-fix-failing-test

## Purpose

Tests whether the model can use test output as a diagnostic signal. Exercises:

- Running a command (`python3 check.py`) to see failure
- Reading an assertion error message to localize the bug
- Tracing from `check.py`'s `add(...)` call back to `calc.py`'s `add` implementation
- Fixing the bug in the *right* file (not by editing the test)

## Setup state

`/workspace/calc.py`:
```python
def add(a, b):
    return a - b  # bug: should be +
```

`/workspace/check.py`:
```python
from calc import add
assert add(2, 3) == 5, f"add(2, 3) expected 5, got {add(2, 3)}"
assert add(0, 0) == 0
assert add(-1, 1) == 0
assert add(10, 20) == 30
print("OK")
```

Both committed in a git repo.

## Pass criteria

1. `check.py` is unchanged from initial state (no sidestepping by editing assertions)
2. `python3 check.py` exits 0

## Notes

A common failure mode for weaker models: they "fix" by relaxing the assertions in `check.py` so they pass against the broken `calc.py`. The score check rejects that explicitly. Another mode: they edit `calc.py` to return a hardcoded value matching the asserted result, which would happen to satisfy `check.py` here — that's actually acceptable as a "fix" by these criteria. The task is about whether the model can locate and modify the right file, not whether it produces a deeply correct fix.
