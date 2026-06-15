"""Tests for scripts/remote-forge/workstation-wrapper.

The wrapper shells out to ssh/rsync/git; these tests put shim executables on
PATH that log their invocations and return controlled exit codes, so the
wrapper's branching logic can be exercised without a real server or network.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

WRAPPER = (
    Path(__file__).parents[2] / "scripts" / "remote-forge" / "workstation-wrapper"
)

_SSH_SHIM = """#!/bin/bash
echo "ssh $*" >> "$CALL_LOG"
case "$*" in
    *"forge run"*) exit "${SSH_RUN_RC:-0}";;
    *) exit "${SSH_RC:-0}";;
esac
"""

_RSYNC_SHIM = """#!/bin/bash
echo "rsync $*" >> "$CALL_LOG"
exit "${RSYNC_RC:-0}"
"""

_GIT_SHIM = """#!/bin/bash
echo "git $*" >> "$CALL_LOG"
case "$1 $2" in
    "rev-parse --show-toplevel") echo "${FAKE_REPO_PATH:-/home/u/myrepo}"; exit 0;;
    "remote get-url")
        if [ -n "$GIT_HAS_REMOTE" ]; then echo "$GIT_REMOTE_URL"; exit 0; fi
        exit 2;;
    "fetch forgejo") exit "${GIT_FETCH_RC:-0}";;
    "branch -r") echo "  forgejo/main"; echo "  forgejo/feature/x"; exit 0;;
    *) exit 0;;
esac
"""


@pytest.fixture()
def shim_bin(tmp_path: Path) -> Path:
    """Create a bin/ dir of ssh/rsync/git shims and return it."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (("ssh", _SSH_SHIM), ("rsync", _RSYNC_SHIM), ("git", _GIT_SHIM)):
        shim = bin_dir / name
        shim.write_text(body)
        shim.chmod(0o755)
    return bin_dir


def run_wrapper(shim_bin: Path, tmp_path: Path, args: list[str], **env_overrides):
    """Run the wrapper with shims on PATH. Returns (proc, call_log_text)."""
    call_log = tmp_path / "calls.log"
    env = dict(os.environ)
    env["PATH"] = f"{shim_bin}:{env['PATH']}"
    env["CALL_LOG"] = str(call_log)
    env.setdefault("FAKE_REPO_PATH", "/home/u/myrepo")
    env.update(env_overrides)
    proc = subprocess.run(
        ["bash", str(WRAPPER), *args],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    log = call_log.read_text() if call_log.exists() else ""
    return proc, log


def test_rejects_user_repo_flag(shim_bin, tmp_path):
    proc, log = run_wrapper(shim_bin, tmp_path, ["run", "--repo", "/foo"])
    assert proc.returncode == 1
    assert "do not pass --repo yourself" in proc.stderr
    assert "ssh" not in log  # bailed before touching the server


def test_syncs_then_invokes_remote_run(shim_bin, tmp_path):
    proc, log = run_wrapper(shim_bin, tmp_path, ["run"])
    assert proc.returncode == 0
    assert "rsync" in log
    assert "forge run --repo" in log
    assert "session ended" in proc.stderr


def test_adds_forgejo_remote_when_absent(shim_bin, tmp_path):
    proc, log = run_wrapper(shim_bin, tmp_path, ["run"])  # GIT_HAS_REMOTE unset
    assert "remote add forgejo http://tesseract:3000/cc_forge_admin/myrepo.git" in log
    assert "added 'forgejo' remote" in proc.stderr


def test_updates_forgejo_remote_when_url_differs(shim_bin, tmp_path):
    proc, log = run_wrapper(
        shim_bin,
        tmp_path,
        ["run"],
        GIT_HAS_REMOTE="1",
        GIT_REMOTE_URL="http://old-server:3000/cc_forge_admin/myrepo.git",
    )
    assert "remote set-url forgejo http://tesseract:3000/cc_forge_admin/myrepo.git" in log
    assert "updated 'forgejo' remote" in proc.stderr


def test_leaves_remote_when_url_matches(shim_bin, tmp_path):
    proc, log = run_wrapper(
        shim_bin,
        tmp_path,
        ["run"],
        GIT_HAS_REMOTE="1",
        GIT_REMOTE_URL="http://tesseract:3000/cc_forge_admin/myrepo.git",
    )
    assert "remote add forgejo" not in log
    assert "remote set-url forgejo" not in log


def test_fetch_failure_reports_unreachable(shim_bin, tmp_path):
    proc, _ = run_wrapper(shim_bin, tmp_path, ["run"], GIT_FETCH_RC="1")
    assert "could not fetch from Forgejo" in proc.stderr
    assert "session ended" not in proc.stderr


def test_fetch_runs_after_nonzero_session(shim_bin, tmp_path):
    # A non-zero remote session exit must not skip the best-effort fetch.
    proc, log = run_wrapper(shim_bin, tmp_path, ["run"], SSH_RUN_RC="1")
    assert proc.returncode == 0
    assert "git fetch forgejo" in log
    assert "session ended" in proc.stderr


def test_env_overrides_server_user_port(shim_bin, tmp_path):
    proc, log = run_wrapper(
        shim_bin,
        tmp_path,
        ["run"],
        FORGE_SERVER="prod",
        FORGE_FORGEJO_USER="bob",
        FORGE_FORGEJO_PORT="4000",
    )
    assert "ssh prod" in log
    assert "remote add forgejo http://prod:4000/bob/myrepo.git" in log


def test_passthrough_subcommand_skips_rsync(shim_bin, tmp_path):
    proc, log = run_wrapper(shim_bin, tmp_path, ["status"])
    assert proc.returncode == 0
    assert "rsync" not in log
    assert "forge status" in log
