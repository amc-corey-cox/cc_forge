#!/bin/bash
# `gh` CLI shim for the forge agent container.
#
# The agent's training prior is to reach for `gh`. We install this script as
# /usr/local/bin/gh so that `gh pr create`, `gh issue view`, etc. translate
# to the right backend instead of failing.
#
# Unified number-space (offset model):
#   FORGEJO_OFFSET=10000
#   N > 10000  → Forgejo (subtract offset for real number)
#   N <= 10000 → GitHub first; fall back to Forgejo if GitHub 404s/missing
#   -R given   → explicit GitHub, no offset, no fallback
#
# Supported commands:
#   pr create .......... Forgejo workspace (writes; -R rejected)
#   pr view <N> ........ offset-routed
#   pr list ............ merged listing (both backends)
#   pr checks <N> ...... offset-routed (PR → SHA → GitHub check-runs / Forgejo statuses)
#   pr diff <N> ........ offset-routed (raw diff text)
#   issue create ....... Forgejo workspace (writes; -R rejected)
#   issue view <N> ..... offset-routed
#   issue list ......... merged listing (both backends)
#   repo view .......... Forgejo default, GitHub with -R
#
# Output is the raw underlying API's JSON response (except pr diff which
# returns raw diff text). Anything outside the allowlist exits with a clear
# message naming what's supported.

set -euo pipefail

FORGEJO_OFFSET=10000
SUPPORTED_COMMANDS="pr create, pr view, pr list, pr checks, pr diff, issue create, issue view, issue list, repo view"

die() {
    echo "gh: $*" >&2
    exit 1
}

# Credentials (Forgejo + GitHub URLs/tokens, GitHub routing config) live in a
# file written by forge at container start — not in env vars, so they are not
# visible to `docker inspect` or other processes. Override with
# $FORGE_SHIM_CREDS_FILE for testing.
SHIM_CREDS_FILE="${FORGE_SHIM_CREDS_FILE:-/home/agent/.config/forge-shim/credentials}"
if [ -f "$SHIM_CREDS_FILE" ]; then
    set -a; . "$SHIM_CREDS_FILE"; set +a
fi

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

# ---- Helpers for offset routing and fallback ----

has_github_creds() {
    [ -n "${FORGE_GITHUB_TOKEN:-}" ]
}

has_forgejo_creds() {
    [ -n "${FORGEJO_URL:-}" ] && [ -n "${FORGEJO_TOKEN:-}" ]
}

# Like github_get but returns empty string on any error (for fallback logic).
github_get_or_empty() {
    local path="$1"
    curl -sSf \
        -H "Authorization: token $FORGE_GITHUB_TOKEN" \
        -H "Accept: application/vnd.github+json" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        "https://api.github.com/$path" 2>/dev/null || true
}

# Fetch raw content from Forgejo web endpoint (no /api/v1/ prefix).
forgejo_get_raw() {
    local path="$1"
    curl -sSf \
        -H "Authorization: token $FORGEJO_TOKEN" \
        "$FORGEJO_URL/$path"
}

# Fetch diff from GitHub using the diff Accept header.
github_get_diff() {
    local path="$1"
    curl -sSf \
        -H "Authorization: token $FORGE_GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3.diff" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        "https://api.github.com/$path"
}

is_forgejo_number() {
    [ "$1" -gt "$FORGEJO_OFFSET" ] 2>/dev/null
}

real_forgejo_number() {
    echo $(( $1 - FORGEJO_OFFSET ))
}

# Pipe filter: add offset to .number in a single JSON object.
apply_offset() {
    jq -c ".number += $FORGEJO_OFFSET"
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
                [ -n "$2" ] || die "$1 needs a non-empty value"
                dash_R="$2"; shift 2 ;;
            -R=*)
                dash_R="${1#-R=}"
                [ -n "$dash_R" ] || die "-R= needs a non-empty value"
                shift ;;
            --repo=*)
                dash_R="${1#--repo=}"
                [ -n "$dash_R" ] || die "--repo= needs a non-empty value"
                shift ;;
            *) positional+=("$1"); shift ;;
        esac
    done
}

# Strip flags that agents commonly pass but the shim ignores (--json, --jq, -q).
# Operates on the `positional` array set by parse_dash_R.
strip_ignored_flags() {
    local filtered=()
    local i=0
    while [ $i -lt ${#positional[@]} ]; do
        case "${positional[$i]}" in
            --json|--jq|-q)
                # These take a following value (e.g. `-q <jq-expr>`) — skip it too.
                i=$(( i + 2 )) ;;
            --json=*|--jq=*|-q=*)
                i=$(( i + 1 )) ;;
            *)
                filtered+=("${positional[$i]}")
                i=$(( i + 1 )) ;;
        esac
    done
    positional=("${filtered[@]+"${filtered[@]}"}")
}

# ---- Commands ----

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
            --json|--jq|-q) shift; if [ $# -gt 0 ]; then shift; fi ;;  # ignored (takes a value)
            --json=*|--jq=*|-q=*) shift ;;                             # ignored
            *) die "unknown flag for 'pr create': $1" ;;
        esac
    done
    [ -n "$title" ] || die "--title is required for 'pr create'"

    # Auto-detect --head from current branch if not provided.
    if [ -z "$head" ]; then
        head=$(git -C "$WORKSPACE" branch --show-current 2>/dev/null) \
            || die "could not detect current branch for --head (detached HEAD?)"
        [ -n "$head" ] || die "could not detect current branch for --head (detached HEAD?)"
    fi

    local owner_repo payload
    owner_repo=$(detect_forgejo_repo)
    payload=$(jq -nc \
        --arg title "$title" \
        --arg head "$head" \
        --arg base "$base" \
        --arg body "$body" \
        '{title: $title, head: $head, base: $base, body: $body}')
    forgejo_post "repos/$owner_repo/pulls" "$payload" | apply_offset
}

cmd_pr_view() {
    local dash_R; local positional
    parse_dash_R "$@"
    strip_ignored_flags
    set -- "${positional[@]+"${positional[@]}"}"
    [ $# -eq 1 ] || die "'pr view' takes exactly one argument (the PR number)"
    if [ -n "$dash_R" ]; then
        # -R given → explicit GitHub, no offset
        require_github_env
        github_get "repos/$dash_R/pulls/$1"
    elif is_forgejo_number "$1"; then
        # N > 10000 → Forgejo directly
        require_forgejo_env
        local owner_repo real_n
        owner_repo=$(detect_forgejo_repo)
        real_n=$(real_forgejo_number "$1")
        forgejo_get "repos/$owner_repo/pulls/$real_n" | apply_offset
    elif has_github_creds; then
        # Try GitHub first
        local response target
        target=$(detect_github_repo 2>/dev/null) || target=""
        if [ -n "$target" ]; then
            response=$(github_get_or_empty "repos/$target/pulls/$1")
        fi
        if [ -n "${response:-}" ]; then
            echo "$response"
        elif has_forgejo_creds; then
            local owner_repo
            owner_repo=$(detect_forgejo_repo)
            forgejo_get "repos/$owner_repo/pulls/$1" | apply_offset
        else
            die "PR $1 not found on GitHub and Forgejo credentials not configured"
        fi
    else
        # No GitHub creds → Forgejo only
        require_forgejo_env
        local owner_repo
        owner_repo=$(detect_forgejo_repo)
        forgejo_get "repos/$owner_repo/pulls/$1" | apply_offset
    fi
}

cmd_pr_list() {
    local dash_R; local positional
    parse_dash_R "$@"
    strip_ignored_flags
    set -- "${positional[@]+"${positional[@]}"}"
    [ $# -eq 0 ] || die "'pr list' takes no arguments"
    if [ -n "$dash_R" ]; then
        require_github_env
        github_get "repos/$dash_R/pulls?state=open"
    else
        local gh_json="" fj_json=""
        if has_github_creds; then
            local target
            target=$(detect_github_repo 2>/dev/null) || target=""
            if [ -n "$target" ]; then
                gh_json=$(github_get_or_empty "repos/$target/pulls?state=open")
            fi
        fi
        if has_forgejo_creds; then
            local owner_repo
            owner_repo=$(detect_forgejo_repo)
            fj_json=$(forgejo_get "repos/$owner_repo/pulls?state=open" 2>/dev/null || true)
        fi
        if [ -z "$gh_json" ] && [ -z "$fj_json" ]; then
            die "no credentials configured for either GitHub or Forgejo"
        fi
        # Merge: tag with _source, apply offset to Forgejo items
        local gh_tagged fj_tagged
        gh_tagged=$(echo "${gh_json:-[]}" | jq '[.[]? | . + {_source: "github"}]' 2>/dev/null || echo '[]')
        fj_tagged=$(echo "${fj_json:-[]}" | jq "[.[]? | .number += $FORGEJO_OFFSET | . + {_source: \"forgejo\"}]" 2>/dev/null || echo '[]')
        jq -nc --argjson gh "$gh_tagged" --argjson fj "$fj_tagged" '$gh + $fj'
    fi
}

cmd_pr_checks() {
    local dash_R; local positional
    parse_dash_R "$@"
    strip_ignored_flags
    set -- "${positional[@]+"${positional[@]}"}"
    [ $# -eq 1 ] || die "'pr checks' takes exactly one argument (the PR number)"
    local pr_json sha
    if [ -n "$dash_R" ]; then
        require_github_env
        pr_json=$(github_get "repos/$dash_R/pulls/$1")
        sha=$(echo "$pr_json" | jq -r '.head.sha')
        github_get "repos/$dash_R/commits/$sha/check-runs"
    elif is_forgejo_number "$1"; then
        require_forgejo_env
        local owner_repo real_n
        owner_repo=$(detect_forgejo_repo)
        real_n=$(real_forgejo_number "$1")
        pr_json=$(forgejo_get "repos/$owner_repo/pulls/$real_n")
        sha=$(echo "$pr_json" | jq -r '.head.sha')
        forgejo_get "repos/$owner_repo/commits/$sha/statuses"
    elif has_github_creds; then
        local target
        target=$(detect_github_repo 2>/dev/null) || target=""
        if [ -n "$target" ]; then
            pr_json=$(github_get_or_empty "repos/$target/pulls/$1")
        fi
        if [ -n "${pr_json:-}" ]; then
            sha=$(echo "$pr_json" | jq -r '.head.sha')
            github_get "repos/$target/commits/$sha/check-runs"
        elif has_forgejo_creds; then
            local owner_repo
            owner_repo=$(detect_forgejo_repo)
            pr_json=$(forgejo_get "repos/$owner_repo/pulls/$1")
            sha=$(echo "$pr_json" | jq -r '.head.sha')
            forgejo_get "repos/$owner_repo/commits/$sha/statuses"
        else
            die "PR $1 not found on GitHub and Forgejo credentials not configured"
        fi
    else
        require_forgejo_env
        local owner_repo
        owner_repo=$(detect_forgejo_repo)
        pr_json=$(forgejo_get "repos/$owner_repo/pulls/$1")
        sha=$(echo "$pr_json" | jq -r '.head.sha')
        forgejo_get "repos/$owner_repo/commits/$sha/statuses"
    fi
}

cmd_pr_diff() {
    local dash_R; local positional
    parse_dash_R "$@"
    strip_ignored_flags
    set -- "${positional[@]+"${positional[@]}"}"
    [ $# -eq 1 ] || die "'pr diff' takes exactly one argument (the PR number)"
    if [ -n "$dash_R" ]; then
        require_github_env
        github_get_diff "repos/$dash_R/pulls/$1"
    elif is_forgejo_number "$1"; then
        require_forgejo_env
        local owner_repo real_n
        owner_repo=$(detect_forgejo_repo)
        real_n=$(real_forgejo_number "$1")
        forgejo_get_raw "$owner_repo/pulls/$real_n.diff"
    elif has_github_creds; then
        local target
        target=$(detect_github_repo 2>/dev/null) || target=""
        local response=""
        if [ -n "$target" ]; then
            response=$(github_get_diff "repos/$target/pulls/$1" 2>/dev/null || true)
        fi
        if [ -n "$response" ]; then
            echo "$response"
        elif has_forgejo_creds; then
            local owner_repo
            owner_repo=$(detect_forgejo_repo)
            forgejo_get_raw "$owner_repo/pulls/$1.diff"
        else
            die "PR $1 not found on GitHub and Forgejo credentials not configured"
        fi
    else
        require_forgejo_env
        local owner_repo
        owner_repo=$(detect_forgejo_repo)
        forgejo_get_raw "$owner_repo/pulls/$1.diff"
    fi
}

cmd_issue_create() {
    # Writes never target GitHub.
    for arg in "$@"; do
        case "$arg" in
            -R|--repo|-R=*|--repo=*)
                die "'issue create' writes to your Forgejo workspace; -R/--repo is not supported on writes" ;;
        esac
    done
    require_forgejo_env
    local title="" body=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --title) [ $# -ge 2 ] || die "--title needs a value"; title="$2"; shift 2 ;;
            --body)  [ $# -ge 2 ] || die "--body needs a value";  body="$2";  shift 2 ;;
            --json|--jq|-q) shift; if [ $# -gt 0 ]; then shift; fi ;;  # ignored (takes a value)
            --json=*|--jq=*|-q=*) shift ;;                             # ignored
            *) die "unknown flag for 'issue create': $1" ;;
        esac
    done
    [ -n "$title" ] || die "--title is required for 'issue create'"

    local owner_repo payload
    owner_repo=$(detect_forgejo_repo)
    payload=$(jq -nc \
        --arg title "$title" \
        --arg body "$body" \
        '{title: $title, body: $body}')
    forgejo_post "repos/$owner_repo/issues" "$payload" | apply_offset
}

cmd_issue_view() {
    local dash_R; local positional
    parse_dash_R "$@"
    strip_ignored_flags
    set -- "${positional[@]+"${positional[@]}"}"
    [ $# -eq 1 ] || die "'issue view' takes exactly one argument (the issue number)"
    if [ -n "$dash_R" ]; then
        # -R given → explicit GitHub, no offset
        require_github_env
        github_get "repos/$dash_R/issues/$1"
    elif is_forgejo_number "$1"; then
        # N > 10000 → Forgejo directly
        require_forgejo_env
        local owner_repo real_n
        owner_repo=$(detect_forgejo_repo)
        real_n=$(real_forgejo_number "$1")
        forgejo_get "repos/$owner_repo/issues/$real_n" | apply_offset
    elif has_github_creds; then
        # Try GitHub first
        local response target
        target=$(detect_github_repo 2>/dev/null) || target=""
        if [ -n "$target" ]; then
            response=$(github_get_or_empty "repos/$target/issues/$1")
        fi
        if [ -n "${response:-}" ]; then
            echo "$response"
        elif has_forgejo_creds; then
            local owner_repo
            owner_repo=$(detect_forgejo_repo)
            forgejo_get "repos/$owner_repo/issues/$1" | apply_offset
        else
            die "issue $1 not found on GitHub and Forgejo credentials not configured"
        fi
    else
        # No GitHub creds → Forgejo only
        require_forgejo_env
        local owner_repo
        owner_repo=$(detect_forgejo_repo)
        forgejo_get "repos/$owner_repo/issues/$1" | apply_offset
    fi
}

cmd_issue_list() {
    local dash_R; local positional
    parse_dash_R "$@"
    strip_ignored_flags
    set -- "${positional[@]+"${positional[@]}"}"
    [ $# -eq 0 ] || die "'issue list' takes no arguments"
    if [ -n "$dash_R" ]; then
        require_github_env
        github_get "repos/$dash_R/issues"
    else
        local gh_json="" fj_json=""
        if has_github_creds; then
            local target
            target=$(detect_github_repo 2>/dev/null) || target=""
            if [ -n "$target" ]; then
                gh_json=$(github_get_or_empty "repos/$target/issues")
            fi
        fi
        if has_forgejo_creds; then
            local owner_repo
            owner_repo=$(detect_forgejo_repo)
            fj_json=$(forgejo_get "repos/$owner_repo/issues?state=open" 2>/dev/null || true)
        fi
        if [ -z "$gh_json" ] && [ -z "$fj_json" ]; then
            die "no credentials configured for either GitHub or Forgejo"
        fi
        # Merge: tag with _source, apply offset to Forgejo items
        local gh_tagged fj_tagged
        gh_tagged=$(echo "${gh_json:-[]}" | jq '[.[]? | . + {_source: "github"}]' 2>/dev/null || echo '[]')
        fj_tagged=$(echo "${fj_json:-[]}" | jq "[.[]? | .number += $FORGEJO_OFFSET | . + {_source: \"forgejo\"}]" 2>/dev/null || echo '[]')
        jq -nc --argjson gh "$gh_tagged" --argjson fj "$fj_tagged" '$gh + $fj'
    fi
}

cmd_repo_view() {
    local dash_R; local positional
    parse_dash_R "$@"
    strip_ignored_flags
    set -- "${positional[@]+"${positional[@]}"}"
    [ $# -eq 0 ] || die "'repo view' takes no arguments"
    if [ -n "$dash_R" ]; then
        require_github_env
        github_get "repos/$dash_R"
    else
        require_forgejo_env
        local owner_repo
        owner_repo=$(detect_forgejo_repo)
        forgejo_get "repos/$owner_repo"
    fi
}

# ---- Dispatch ----

case "${1:-}" in
    pr)
        case "${2:-}" in
            create) shift 2; cmd_pr_create "$@" ;;
            view)   shift 2; cmd_pr_view "$@" ;;
            list)   shift 2; cmd_pr_list "$@" ;;
            checks) shift 2; cmd_pr_checks "$@" ;;
            diff)   shift 2; cmd_pr_diff "$@" ;;
            *) die "'pr ${2:-}' not supported; supported: $SUPPORTED_COMMANDS" ;;
        esac
        ;;
    issue)
        case "${2:-}" in
            create) shift 2; cmd_issue_create "$@" ;;
            view)   shift 2; cmd_issue_view "$@" ;;
            list)   shift 2; cmd_issue_list "$@" ;;
            *) die "'issue ${2:-}' not supported; supported: $SUPPORTED_COMMANDS" ;;
        esac
        ;;
    repo)
        case "${2:-}" in
            view) shift 2; cmd_repo_view "$@" ;;
            *) die "'repo ${2:-}' not supported; supported: $SUPPORTED_COMMANDS" ;;
        esac
        ;;
    "") die "no subcommand; supported: $SUPPORTED_COMMANDS" ;;
    *) die "'$1' not supported by the forge shim; supported: $SUPPORTED_COMMANDS" ;;
esac
