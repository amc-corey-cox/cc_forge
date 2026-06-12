#!/bin/bash
# Forgejo-backed `gh` CLI shim for the forge agent container.
#
# The agent's training prior is to reach for `gh`. We install this script as
# /usr/local/bin/gh so that `gh pr create`, `gh issue view`, etc. translate
# to Forgejo REST API calls instead of failing.
#
# Supported subcommands (allowlist):
#   gh pr create --title T --head B [--base B] [--body B]
#   gh pr view <number>
#   gh issue view <number>
#   gh issue list
#
# Output is the raw Forgejo API JSON. Anything outside the allowlist exits
# with a clear message naming what's supported.

set -euo pipefail

die() {
    echo "gh: $*" >&2
    exit 1
}

require_env() {
    [ -n "${FORGEJO_URL:-}" ] || die "FORGEJO_URL not set"
    [ -n "${FORGEJO_TOKEN:-}" ] || die "FORGEJO_TOKEN not set"
}

# Override with FORGE_WORKSPACE for testing outside the container.
WORKSPACE="${FORGE_WORKSPACE:-/workspace/repo}"

# Derive owner/repo from the workspace origin remote.
detect_repo() {
    local url owner_repo
    url=$(git -C "$WORKSPACE" remote get-url origin 2>/dev/null) \
        || die "could not read origin remote from $WORKSPACE"
    # Strip "<proto>://<host[:port]>/" (HTTP) or "user@host:" (SSH) prefix
    # and ".git" suffix.
    owner_repo=$(echo "$url" | sed -E '
        s#^[^/]+//[^/]+/##
        s#^[^@]+@[^:]+:##
        s#\.git$##
    ')
    [ -n "$owner_repo" ] || die "could not parse owner/repo from $url"
    echo "$owner_repo"
}

api_get() {
    local path="$1"
    curl -sf \
        -H "Authorization: token $FORGEJO_TOKEN" \
        -H "Accept: application/json" \
        "$FORGEJO_URL/api/v1/$path"
}

api_post() {
    local path="$1" body="$2"
    curl -sf -X POST \
        -H "Authorization: token $FORGEJO_TOKEN" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -d "$body" \
        "$FORGEJO_URL/api/v1/$path"
}

cmd_pr_create() {
    local title="" head="" base="main" body=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --title) title="$2"; shift 2 ;;
            --head)  head="$2";  shift 2 ;;
            --base)  base="$2";  shift 2 ;;
            --body)  body="$2";  shift 2 ;;
            *) die "unknown flag for 'pr create': $1" ;;
        esac
    done
    [ -n "$title" ] || die "--title is required for 'pr create'"
    [ -n "$head" ]  || die "--head is required for 'pr create'"

    local owner_repo payload
    owner_repo=$(detect_repo)
    payload=$(jq -nc \
        --arg title "$title" \
        --arg head "$head" \
        --arg base "$base" \
        --arg body "$body" \
        '{title: $title, head: $head, base: $base, body: $body}')
    api_post "repos/$owner_repo/pulls" "$payload"
}

cmd_pr_view() {
    local n="${1:-}"
    [ -n "$n" ] || die "'pr view' requires a number"
    local owner_repo
    owner_repo=$(detect_repo)
    api_get "repos/$owner_repo/pulls/$n"
}

cmd_issue_view() {
    local n="${1:-}"
    [ -n "$n" ] || die "'issue view' requires a number"
    local owner_repo
    owner_repo=$(detect_repo)
    api_get "repos/$owner_repo/issues/$n"
}

cmd_issue_list() {
    local owner_repo
    owner_repo=$(detect_repo)
    api_get "repos/$owner_repo/issues"
}

require_env

case "${1:-}" in
    pr)
        case "${2:-}" in
            create) shift 2; cmd_pr_create "$@" ;;
            view)   shift 2; cmd_pr_view "$@" ;;
            *) die "'pr ${2:-}' not supported; supported: pr create, pr view" ;;
        esac
        ;;
    issue)
        case "${2:-}" in
            view) shift 2; cmd_issue_view "$@" ;;
            list) shift 2; cmd_issue_list "$@" ;;
            *) die "'issue ${2:-}' not supported; supported: issue view, issue list" ;;
        esac
        ;;
    "") die "no subcommand; supported: pr create, pr view, issue view, issue list" ;;
    *) die "'$1' not supported by the forge shim; supported: pr create, pr view, issue view, issue list" ;;
esac
