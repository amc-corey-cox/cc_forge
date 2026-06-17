# 07-fix-bug-from-traceback

## Purpose

Tests whether the agent can diagnose a runtime crash by reading a Python
traceback that spans multiple files, trace the error to its root cause, and
apply the correct fix — without being told which file contains the bug.

This is a step up from `05-fix-failing-test`, which names the buggy file in
the prompt. Here the agent must follow the traceback and data flow across
four files to locate the root cause on its own.

## Capability target

- Running a command and reading its output (a multi-file traceback)
- Parsing an `AttributeError` and understanding what `'NoneType'` implies
- Distinguishing the crash site (symptom) from the root cause
- Following data flow across module boundaries to find where the bad value originates
- Editing the correct file to fix the underlying bug

## Setup state

Four Python files in a git repository:

`/workspace/config.py`:
```python
def get_settings():
    return {
        "output_format": "csv",
        "delimiter": None,       # BUG: should be ","
        "include_header": True,
    }
```

`/workspace/formatter.py`:
```python
def format_rows(headers, rows, delimiter):
    lines = []
    if headers:
        lines.append(delimiter.join(headers))
    for row in rows:
        lines.append(delimiter.join(str(v) for v in row))
    return "\n".join(lines)
```

`/workspace/app.py`:
```python
from config import get_settings
from formatter import format_rows

def generate_report(data):
    settings = get_settings()
    headers = list(data[0].keys())
    rows = [list(d.values()) for d in data]
    return format_rows(
        headers if settings["include_header"] else None,
        rows,
        settings["delimiter"],
    )
```

`/workspace/check.py`:
```python
from app import generate_report

data = [
    {"name": "Alice", "score": 95},
    {"name": "Bob", "score": 87},
]
result = generate_report(data)
expected = "name,score\nAlice,95\nBob,87"
assert result == expected, f"Expected:\n{expected}\n\nGot:\n{result}"
print("OK")
```

Running `python3 check.py` produces:

```
Traceback (most recent call last):
  File "check.py", line 7, in <module>
    result = generate_report(data)
  File "app.py", line 8, in generate_report
    return format_rows(
  File "formatter.py", line 4, in format_rows
    lines.append(delimiter.join(headers))
AttributeError: 'NoneType' object has no attribute 'join'
```

The crash is in `formatter.py` but the root cause is in `config.py` — `delimiter` is `None` when it should be `","`.

## Pass criteria

1. `check.py` is unchanged from the initial commit (no sidestepping).
2. `python3 check.py` exits 0 (output matches the expected CSV string).

## Failure modes

- **Does not run `check.py`**: No diagnostic signal; edits blindly or gives up.
- **Edits `check.py`**: Sidestepping — rejected by `score.sh`.
- **Patches `formatter.py` with a wrong default** (e.g., `delimiter or " "`): `check.py` still fails because the output won't match the expected comma-separated format.
- **Cannot parse the traceback**: Edits the wrong file or wrong function entirely.
- **Fixes only the crash without matching expected output**: e.g., sets delimiter to `"|"` — crash is gone but assertion fails.

## Acceptable fixes

- Setting `"delimiter"` to `","` in `config.py` (canonical fix).
- Passing `","` directly in `app.py` instead of reading from config.
- Adding `delimiter = delimiter or ","` in `formatter.py` (fixes the symptom with the correct default; still demonstrates traceback reading).
- Any other change to non-test files that makes `check.py` pass.
