---
description: Review your own change before opening a pull request
---

Review the change you just made as if a colleague wrote it and you're deciding whether
to approve it. Look at your diff against the branch you started from.

First, the question that matters most: **did you deliver what the task asked, and can
you prove it?** Be suspicious of your own work — it's easy to generate plausible change
that drifts off the goal.

- Is the core deliverable actually done, or did you build helpers, scaffolding, or
  tangential tooling around a goal that's still unproven?
- Is it backed by a test that would fail if the change were wrong — not just a manual
  "looks right"?

Then check the change itself:

1. **Correct** — does it handle the main path and the edges? Run the tests.
2. **Focused** — did you change only what the task needs? Remove or split out the rest.
3. **Clear** — will the next person understand it from the code or a brief comment?
4. **Safe** — no secrets committed, no obvious security hole in what you touched.

If anything is wrong, incomplete, or murky, fix it and review again before opening the PR.
