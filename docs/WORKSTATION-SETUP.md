# Workstation Setup: Running `forge` Against a Remote Forgejo

Interim setup that lets you invoke `forge` from a workstation while Forgejo and
the agent image live on a separate server (referred to here as `tesseract`).

This is scaffolding for [issue #42](https://github.com/amc-corey-cox/cc_forge/issues/42).
When forge learns to talk to a remote Forgejo directly, both wrapper scripts and
this document can be deleted.

## Prerequisites

- SSH access to the server, with an alias `tesseract` defined in `~/.ssh/config`.
- A clone of `cc_forge` at `~/Code/cc_forge` on the server.
- `mise` + `uv` available on the server (the wrapper uses the repo's own mise config
  so no global uv pin is needed).
- The agent image built on the server: `docker images cc-forge-agent:latest`.

The install script symlinks the appropriate wrapper into `~/.local/bin/forge`,
so `git pull` in the checkout updates the wrapper automatically.

## Server side

```bash
ssh tesseract
~/Code/cc_forge/scripts/remote-forge/install server
forge --version    # confirm
```

## Workstation side

```bash
# 1. Install the wrapper
~/Code/cc_forge/scripts/remote-forge/install workstation

# 2. Make 'tesseract' resolvable for the Forgejo web UI
#    (derives the IP from your existing ssh config; one-time, requires sudo)
TESSERACT_IP=$(awk '/^Host tesseract/{flag=1; next} /^Host /{flag=0} flag && /HostName/{print $2}' ~/.ssh/config)
if [[ "$TESSERACT_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "$TESSERACT_IP  tesseract" | sudo tee -a /etc/hosts
else
    echo "HostName for tesseract is missing or isn't an IPv4 address — resolve it manually and add the line to /etc/hosts."
fi
```

After that, `forge run --claude` from any git repo on the workstation:

1. rsyncs the repo to `tesseract:~/forge-workspaces/<repo>/`,
2. SSHes to tesseract with a TTY,
3. invokes server-side `forge run --repo ~/forge-workspaces/<repo> --claude`,
4. on session end, adds a `forgejo` remote and fetches agent branches back.

The agent session runs as it always did. You can review the agent's work at
`http://tesseract:3000` from the workstation's browser, and the agent's
branches are available locally via `git branch -r | grep forgejo/`.

## Limitations

- The agent works on the server-side rsync'd copy. Local uncommitted changes
  travel via rsync (good), but the agent's commits land in Forgejo (server).
  The wrapper auto-fetches agent branches after the session ends.
- Override the server hostname, Forgejo user, or port via env vars:
  `FORGE_SERVER`, `FORGE_FORGEJO_USER`, `FORGE_FORGEJO_PORT` (defaults:
  `tesseract`, `cc_forge_admin`, `3000`).
- Workstation `~/.config/forge/config.env` is intentionally absent — the
  workstation wrapper does not run forge locally, so it does not read config.

## Removal

```bash
# Workstation
rm ~/.local/bin/forge    # was a symlink into the checkout — safe to delete
sudo sed -i.bak '/[[:space:]]tesseract$/d' /etc/hosts

# Server
ssh tesseract 'rm ~/.local/bin/forge'
```

The `~/forge-workspaces/` directory on the server holds the rsync'd repos and
can be removed when you are finished with the interim setup.
