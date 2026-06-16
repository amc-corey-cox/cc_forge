# 02-fix-typo

## Purpose

The first real capability task — tests whether the model can drive Claude Code through a complete read-edit-verify loop on a tiny, well-defined target. Exercises:

- Workspace discovery (find README.md without being told where it is)
- Reading a file's contents
- Recognizing a typo without it being pointed out explicitly
- Producing a correct file edit
- Leaving the workspace in a state the score check will accept

## Setup state

A git repo at `/workspace/` with a single file `README.md` containing exactly:

```
# Hello Wrold
```

(committed; the typo is "Wrold" which should be "World")

## Pass criteria

`grep -q "Hello World" README.md` succeeds after the agent run. The score script enforces this automatically.

Acceptable: any edit that produces a line containing "Hello World". The model doesn't have to remove the "#" or change anything else; only "Wrold" → "World" matters.

## Notes

Intentionally small enough that wall-clock cost stays bounded on slow CPU paths — useful as a sanity check on whether a model can drive Claude Code at all before investing time in heavier tasks.
