#!/bin/bash
# `gh` CLI shim for the forge agent container.
#
# The agent's training prior is to reach for `gh`. We install this script as
# /usr/local/bin/gh so that `gh pr create`, `gh issue view`, etc. translate
# to the right backend instead of failing.
#
# Routing rules:
#   pr create ............... Forgejo workspace (writes; -R/--repo is rejected)
#   pr view <N> ............. Forgejo workspace (default), or GitHub if -R given
#   issue view, issue list .. GitHub always; -R picks the specific GitHub repo
#
# Without -R, GitHub-bound commands resolve their target from
# $FORGE_GITHUB_REPO (override) or $FORGE_GITHUB_OWNER + workspace basename.
#
# Output is the raw underlying API's JSON response. Anything outside the
# allowlist exits with a clear message naming what's supported.

set -euo pipefail

die() {
    echo "gh: $*" >&2
    exit 1
}

require_forgejo_env() {
    [ -n "${FORGEJO_URL:-}" ] || die "FORGEJO_URL not set"
    [ -n "${FORGEJO_TOKEN:-}" ] || die "FORGEJO_TOKEN not set"
}

require_github_env() {
    [ -n "${FORGE_GITHUB_TOKEN:-}" ] || die "FORGE_GITHUB_TOKEN not set (required for GitHub access)"
}

# Override with FORGE_WORKSPACE for testing outside the container.
WORKSPACE="${FORGE_WORKSPACE:-/workspace/repo}"

# Derive owner/repo from the workspace origin remote (Forgejo).
detect_forgejo_repo() {
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

# Resolve the GitHub owner/repo for the current workspace.
# Precedence: FORGE_GITHUB_REPO > FORGE_GITHUB_OWNER + workspace repo basename.
detect_github_repo() {
    if [ -n "${FORGE_GITHUB_REPO:-}" ]; then
        echo "$FORGE_GITHUB_REPO"
    elif [ -n "${FORGE_GITHUB_OWNER:-}" ]; then
        local forgejo_repo
        forgejo_repo=$(detect_forgejo_repo)
        echo "$FORGE_GITHUB_OWNER/$(basename "$forgejo_repo")"
    else
        die "cannot route to GitHub: set FORGE_GITHUB_REPO=owner/repo or FORGE_GITHUB_OWNER=owner"
    fi
}

forgejo_get() {
    local path="$1"
    curl -sSf \
        -H "Authorization: token $FORGEJO_TOKEN" \
        -H "Accept: application/json" \
        "$FORGEJO_URL/api/v1/$path"
}

forgejo_post() {
    local path="$1" body="$2"
    curl -sSf -X POST \
        -H "Authorization: token $FORGEJO_TOKEN" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -d "$body" \
        "$FORGEJO_URL/api/v1/$path"
}

github_get() {
    local path="$1"
    curl -sSf \
        -H "Authorization: token $FORGE_GITHUB_TOKEN" \
        -H "Accept: application/vnd.github+json" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        "https://api.github.com/$path"
}

# Strip -R/--repo (and the =value forms) from args into the dash_R variable,
# leaving non-flag args in the positional array. Used by read subcommands.
# Caller must declare `dash_R` and `positional` as local before calling.
parse_dash_R() {
    dash_R=""
    positional=()
    while [ $# -gt 0 ]; do
        case "$1" in
            -R|--repo)
                [ $# -ge 2 ] || die "$1 needs a value"
                dash_R="$2"; shift 2 ;;
            -R=*)     dash_R="${1#-R=}"; shift ;;
            --repo=*) dash_R="${1#--repo=}"; shift ;;
            *) positional+=("$1"); shift ;;
        esac
    done
}

cmd_pr_create() {
    # Writes never target GitHub.
    for arg in "$@"; do
        case "$arg" in
            -R|--repo|-R=*|--repo=*)
                die "'pr create' writes to your Forgejo workspace; -R/--repo is not supported on writes" ;;
        esac
    done
    require_forgejo_env
    local title="" head="" base="main" body=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --title) [ $# -ge 2 ] || die "--title needs a value"; title="$2"; shift 2 ;;
            --head)  [ $# -ge 2 ] || die "--head needs a value";  head="$2";  shift 2 ;;
            --base)  [ $# -ge 2 ] || die "--base needs a value";  base="$2";  shift 2 ;;
            --body)  [ $# -ge 2 ] || die "--body needs a value";  body="$2";  shift 2 ;;
            *) die "unknown flag for 'pr create': $1" ;;
        esac
    done
    [ -n "$title" ] || die "--title is required for 'pr create'"
    [ -n "$head" ]  || die "--head is required for 'pr create'"

    local owner_repo payload
    owner_repo=$(detect_forgejo_repo)
    payload=$(jq -nc \
        --arg title "$title" \
        --arg head "$head" \
        --arg base "$base" \
        --arg body "$body" \
        '{title: $title, head: $head, base: $base, body: $body}')
    forgejo_post "repos/$owner_repo/pulls" "$payload"
}

cmd_pr_view() {
    local dash_R; local positional
    parse_dash_R "$@"
    set -- "${positional[@]+"${positional[@]}"}"
    [ $# -eq 1 ] || die "'pr view' takes exactly one argument (the PR number)"
    if [ -n "$dash_R" ]; then
        # -R given → GitHub upstream lookup
        require_github_env
        github_get "repos/$dash_R/pulls/$1"
    else
        # Default → Forgejo workspace
        require_forgejo_env
        local owner_repo
        owner_repo=$(detect_forgejo_repo)
        forgejo_get "repos/$owner_repo/pulls/$1"
    fi
}

cmd_issue_view() {
    require_github_env
    local dash_R; local positional
    parse_dash_R "$@"
    set -- "${positional[@]+"${positional[@]}"}"
    [ $# -eq 1 ] || die "'issue view' takes exactly one argument (the issue number)"
    local target
    if [ -n "$dash_R" ]; then
        target="$dash_R"
    else
        target=$(detect_github_repo)
    fi
    github_get "repos/$target/issues/$1"
}

cmd_issue_list() {
    require_github_env
    local dash_R; local positional
    parse_dash_R "$@"
    set -- "${positional[@]+"${positional[@]}"}"
    [ $# -eq 0 ] || die "'issue list' takes no arguments"
    local target
    if [ -n "$dash_R" ]; then
        target="$dash_R"
    else
        target=$(detect_github_repo)
    fi
    github_get "repos/$target/issues"
}

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
