# Agent Environment Notes

For repository, pull request, and issue operations, prefer `gh` — it's the only tool here pre-configured with the credentials needed to reach Forgejo and GitHub. `gh` in this environment is a custom shim that attempts to behave like the real GitHub CLI but routes commands to your workspace's Forgejo or to read-only GitHub as appropriate. Output is always the underlying API's JSON response — Forgejo's or GitHub's — not `gh`'s human-readable text or `--json` shape. Use the JSON as-is; don't restructure or reformat it.
