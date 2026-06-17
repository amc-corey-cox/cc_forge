# 04-rename-variable

## Purpose

Tests the model's ability to do a consistent symbol rename across multiple usages in a single file. Exercises:

- Identifying *all* uses of an identifier (decl, mutation, read)
- Not over-matching (e.g., touching unrelated tokens that happen to contain `count`)
- Producing syntactically valid Python

## Setup state

`/workspace/app.py` contains:

```python
count = 0


def increment():
    global count
    count += 1


def show():
    print(count)
```

(in a git repo, committed)

## Pass criteria

1. `app.py` parses as valid Python after edit
2. No bare `count` identifier remains (whole-word match — `total_count` is fine)
3. At least 4 occurrences of `total_count` (the declaration + global statement + `+=` + `print`)

## Notes

A model that only renames *some* of the occurrences (e.g., the declaration but not the `global` statement) will leave bare `count` references and fail. That's the test.
