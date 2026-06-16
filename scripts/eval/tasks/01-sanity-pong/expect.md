# 01-sanity-pong

## Purpose

Smoke test the harness end-to-end with a prompt expecting trivial output (~3 tokens). Verifies that:

- The agent image starts cleanly
- `claude -p` produces structured JSON
- The model follows a simple instruction
- Total elapsed time is reasonable when warm

## Pass criteria

The captured `output.json` shows:

- `is_error: false`
- `result` is the string `"PONG"` (case-insensitive match acceptable; trailing whitespace acceptable)
- `usage.output_tokens` ≤ 10

## Notes

This is intentionally not a meaningful capability test. Use it to confirm the harness works before adding real tasks. A model that fails this task is broken or misconfigured, not weak.
