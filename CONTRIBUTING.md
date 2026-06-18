# Contributing to CC Forge

Contributions are welcome. This document covers the two things you need to know
before opening a pull request: how contributions are licensed, and how to sign
off on them.

## License & the no-rug-pull pledge

CC Forge is licensed under **AGPL-3.0-or-later**. Contributions are accepted under
that same license (inbound = outbound) — by submitting a change, you license it
under AGPL-3.0-or-later.

**The pledge:** the open release of CC Forge will always remain available under
AGPL-3.0. It will never be relicensed into a proprietary or source-available
license. The maintainer may offer commercial licenses for *maintainer-owned* code
in addition to the open release, but that never closes the open version.

We use the DCO rather than a CLA precisely so there's no rights asymmetry: you
keep the copyright to your contribution, and it stays AGPL like everyone else's.

## Sign your work (DCO)

We use the [Developer Certificate of Origin](https://developercertificate.org/) —
a lightweight statement that you wrote the contribution, or otherwise have the
right to submit it under the project's license. There's no CLA to sign.

Add a `Signed-off-by` line to each commit by committing with `-s`:

```bash
git commit -s -m "Your concise commit message"
```

That appends a line matching your git `user.name` and `user.email`:

```
Signed-off-by: Your Name <you@example.com>
```

By signing off you certify the [DCO](https://developercertificate.org/) (v1.1).

## Pull requests

- Branch from `main`; keep the change focused on one thing.
- Match the existing code style; add tests for new behavior.
- One-line commit messages.
- Run the tests before opening the PR: `uv run pytest tests/unit -v`.
