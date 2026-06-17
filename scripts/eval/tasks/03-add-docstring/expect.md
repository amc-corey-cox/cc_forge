# 03-add-docstring

## Purpose

Smallest meaningful code-edit task. Tests that the model can:

- Locate a function in a file
- Insert a docstring in the correct position (between `def` and the body)
- Produce syntactically valid Python that still loads

## Setup state

`/workspace/app.py` contains:

```python
def hello(name):
    return f"Hello, {name}"
```

(in a git repo, committed)

## Pass criteria

`app.hello.__doc__` is non-empty after the agent's edits. The score script imports `app.py` and checks the docstring exists and isn't whitespace-only.

Acceptable: any non-trivial docstring. Content quality is not evaluated — this is a structural test.

## Notes

If `app.py` is no longer valid Python after the edit, the import in `score.sh` raises and the score is treated as fail (exit non-zero). That's the desired behavior — broken syntax is a fail.
