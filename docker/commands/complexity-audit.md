---
description: Audit your change for complexity that isn't earning its keep
---

Look at the change you just made through the lens of the **complexity-to-utility
trade-off**. It's easy to add complexity quickly without proportional gains in utility
— audit your own diff with fresh eyes and flag anything where the complexity isn't
worth it.

Look for:

1. **Needless abstraction** — layers, wrappers, or generality beyond what the task
   actually needs.
2. **Should be combined** — pieces you split apart that share so much context they'd be
   simpler as one.
3. **Should be split** — anything you made do too many unrelated jobs.
4. **Overguarding** — handling for edge cases that are vanishingly unlikely or
   low-impact, obscuring the happy path.
5. **Overtesting** — tests that lock in implementation details rather than catch real
   bugs, or that overlap heavily.
6. **Dead or speculative code** — anything unused or built for a future that hasn't
   arrived.

Be direct — "delete this" beats "consider simplifying." Make the simplifications worth
making before you open the PR.
