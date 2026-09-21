"""Tests for the forge local workflow (prepare_local_directory)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import click
import pytest

from cc_forge.git import is_git_repo
from cc_forge.session import prepare_local_directory, pull_local_directory


def _make_config(**kwargs):
    from cc_forge.config import ForgeConfig

    defaults = dict(
        forgejo_url="http://localhost:3000",
        forgejo_token="fj-token",
        ollama_cpu_url="http://localhost:11434",
        agent_image="test",
        agent_model="test-model",
        agent_api_key="",
        compose_file="",
        github_token="",
        github_repo="",
        github_owner="",
        agent_mem_limit="4g",
        agent_pids_limit=4096,
    )
    defaults.update(kwargs)
    return ForgeConfig(**defaults)


@pytest.fixture()
def source_dir(tmp_path: Path) -> Path:
    """Create a sample directory with loose text files."""
    d = tmp_path / "my-docs"
    d.mkdir()
    (d / "notes.txt").write_text("some notes")
    (d / "todo.md").write_text("# TODO\n- item 1\n")
    sub = d / "subdir"
    sub.mkdir()
    (sub / "deep.txt").write_text("deep file")
    return d


@pytest.fixture(autouse=True)
def _local_repos_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point _LOCAL_REPOS_DIR at a temp path so tests don't touch the real home."""
    import cc_forge.session as session_mod
    monkeypatch.setattr(session_mod, "_LOCAL_REPOS_DIR", tmp_path / "local-repos")


def test_prepare_creates_git_repo(source_dir: Path) -> None:
    repo = prepare_local_directory(source_dir)
    assert is_git_repo(repo)
    assert repo.name.startswith(source_dir.name)


def test_prepare_copies_files(source_dir: Path) -> None:
    repo = prepare_local_directory(source_dir)
    assert (repo / "notes.txt").read_text() == "some notes"
    assert (repo / "todo.md").exists()
    assert (repo / "subdir" / "deep.txt").read_text() == "deep file"


def test_prepare_skips_hidden_files(source_dir: Path) -> None:
    (source_dir / ".secret").write_text("hidden")
    (source_dir / "subdir" / ".nested-secret").write_text("also hidden")
    hidden_dir = source_dir / ".hidden-dir"
    hidden_dir.mkdir()
    (hidden_dir / "inside.txt").write_text("should not be copied")

    repo = prepare_local_directory(source_dir)

    assert not (repo / ".secret").exists()
    assert not (repo / "subdir" / ".nested-secret").exists()
    assert not (repo / ".hidden-dir").exists()


def test_prepare_excludes_symlinks(source_dir: Path, tmp_path: Path) -> None:
    """Symlinks are dropped, not followed — they can resolve outside the source."""
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("must not leave the machine")
    (source_dir / "link.txt").symlink_to(outside)
    (source_dir / "subdir" / "nested-link.txt").symlink_to(outside)

    repo = prepare_local_directory(source_dir)

    assert not (repo / "link.txt").exists()
    assert not (repo / "subdir" / "nested-link.txt").exists()
    copied = [
        p.read_text()
        for p in repo.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(repo).parts
    ]
    assert "must not leave the machine" not in copied


def test_prepare_is_idempotent(source_dir: Path) -> None:
    repo1 = prepare_local_directory(source_dir)
    # Modify source and re-prepare
    (source_dir / "notes.txt").write_text("updated notes")
    repo2 = prepare_local_directory(source_dir)
    assert repo1 == repo2
    assert (repo2 / "notes.txt").read_text() == "updated notes"


def test_prepare_removes_deleted_source_files(source_dir: Path) -> None:
    repo = prepare_local_directory(source_dir)
    assert (repo / "notes.txt").exists()
    # Delete a file from source and re-prepare
    (source_dir / "notes.txt").unlink()
    prepare_local_directory(source_dir)
    assert not (repo / "notes.txt").exists()
    # The deletion must also be committed, not just applied to the working tree
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.split()
    assert "notes.txt" not in tracked


def test_prepare_distinct_repos_for_same_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Two directories with the same basename but different paths get separate repos."""
    import cc_forge.session as session_mod
    monkeypatch.setattr(session_mod, "_LOCAL_REPOS_DIR", tmp_path / "local-repos-2")

    dir_a = tmp_path / "a" / "docs"
    dir_a.mkdir(parents=True)
    (dir_a / "file.txt").write_text("from a")

    dir_b = tmp_path / "b" / "docs"
    dir_b.mkdir(parents=True)
    (dir_b / "file.txt").write_text("from b")

    repo_a = prepare_local_directory(dir_a)
    repo_b = prepare_local_directory(dir_b)
    assert repo_a != repo_b
    assert (repo_a / "file.txt").read_text() == "from a"
    assert (repo_b / "file.txt").read_text() == "from b"


def test_local_requests_private_forgejo_repo(
    source_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """forge local must create its Forgejo repo private -- the feature's premise."""
    import cc_forge.config as config_mod
    import cc_forge.session as session_mod
    from cc_forge.cli import local

    captured: dict[str, object] = {}
    monkeypatch.setattr(
        session_mod, "start_session", lambda config, **kwargs: captured.update(kwargs)
    )
    monkeypatch.setattr(config_mod, "load_config", _make_config)

    local.callback(directory=str(source_dir), agent="aider", pull_into=None, branch=None)

    assert captured["private"] is True
    assert captured["passthrough"] is False


def test_local_strips_cloud_credentials(
    source_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A GitHub token in the container is an exfiltration path for private files."""
    import cc_forge.config as config_mod
    import cc_forge.session as session_mod
    from cc_forge.cli import local
    from cc_forge.config import ForgeConfig

    loaded = _make_config(
        forgejo_token="keep-me",
        agent_api_key="sk-should-be-dropped",
        github_token="ghp-should-be-dropped",
        github_repo="owner/repo",
        github_owner="owner",
    )
    seen: dict[str, ForgeConfig] = {}
    monkeypatch.setattr(config_mod, "load_config", lambda: loaded)
    monkeypatch.setattr(
        session_mod, "start_session", lambda config, **kw: seen.update(config=config)
    )

    local.callback(directory=str(source_dir), agent="aider", pull_into=None, branch=None)

    cfg = seen["config"]
    assert cfg.github_token == ""
    assert cfg.github_repo == ""
    assert cfg.github_owner == ""
    assert cfg.agent_api_key == ""
    assert cfg.forgejo_token == "keep-me", "Forgejo is local and the session needs it"


def test_normal_run_keeps_cloud_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Only 'local' strips credentials -- ordinary sessions need the gh shim's token."""
    import cc_forge.config as config_mod
    import cc_forge.session as session_mod
    from cc_forge.cli import run

    seen: dict[str, object] = {}
    monkeypatch.setattr(
        config_mod, "load_config", lambda: _make_config(github_token="ghp-keep")
    )
    monkeypatch.setattr(
        session_mod, "start_session", lambda config, **kw: seen.update(config=config)
    )

    run.callback(repo=".", agent="claude", passthrough=False, claude_compat=False)

    assert seen["config"].github_token == "ghp-keep"


def test_rerun_clears_stray_dotfiles_from_managed_repo(source_dir: Path) -> None:
    """Anything but .git is cleared, or add_all() would commit it on the next run."""
    repo = prepare_local_directory(source_dir)
    stray = repo / ".leftover"
    stray.write_text("should not survive")
    stray_dir = repo / ".leftover-dir"
    stray_dir.mkdir()
    (stray_dir / "inner.txt").write_text("nor this")

    prepare_local_directory(source_dir)

    assert not stray.exists()
    assert not stray_dir.exists()
    assert is_git_repo(repo), ".git must survive the clear"


def test_rerun_clears_symlink_in_managed_repo(source_dir: Path, tmp_path: Path) -> None:
    """A symlink-to-directory must not crash the clear loop (rmtree refuses them)."""
    repo = prepare_local_directory(source_dir)
    target = tmp_path / "elsewhere"
    target.mkdir()
    (repo / "dangling-dir").symlink_to(target, target_is_directory=True)

    prepare_local_directory(source_dir)

    assert not (repo / "dangling-dir").exists()
    assert target.exists(), "clearing the link must not delete its target"


def test_rerun_clears_non_regular_file(source_dir: Path) -> None:
    """Anything that isn't a real directory unlinks -- rmtree would raise on a FIFO."""
    repo = prepare_local_directory(source_dir)
    fifo = repo / "a-fifo"
    os.mkfifo(fifo)

    prepare_local_directory(source_dir)

    assert not fifo.exists()


def test_skipped_entries_are_reported(
    source_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Dropping a user's files silently is worse than the noise of saying so."""
    (source_dir / ".topsecret").write_text("hidden")
    (source_dir / "subdir" / ".nested").write_text("also hidden")
    outside = tmp_path / "outside.txt"
    outside.write_text("elsewhere")
    (source_dir / "link.txt").symlink_to(outside)

    prepare_local_directory(source_dir)

    err = capsys.readouterr().err
    assert "Skipped 2 hidden entries" in err
    assert ".topsecret" in err and "subdir/.nested" in err
    assert "Skipped 1 symlink" in err and "link.txt" in err
    assert "loose files" in err


def test_display_path_hides_home(tmp_path: Path) -> None:
    """Managed-repo paths are logged with $HOME collapsed, never a bare username."""
    from cc_forge.session import _display_path

    inside = Path.home() / ".config" / "forge" / "local-repos" / "docs-abc123"
    assert _display_path(inside) == "~/.config/forge/local-repos/docs-abc123"
    assert str(Path.home()) not in _display_path(inside)
    # Paths outside $HOME are returned unchanged rather than mangled
    assert _display_path(tmp_path) == str(tmp_path)


def test_prepare_rejects_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Rejects non-directories, and the message carries no absolute home path."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    f = fake_home / "not-a-dir.txt"
    f.write_text("hello")
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    with pytest.raises(click.ClickException) as exc:
        prepare_local_directory(f)

    assert str(fake_home) not in str(exc.value)
    assert "~/not-a-dir.txt" in str(exc.value)


def _fake_forgejo_session(source: Path, tmp_path: Path, edits) -> Path:
    """Run a prepare, push to a local bare 'forgejo', apply *edits* there.

    Stands in for an agent session: the bare repo is what forge would pull from.
    """
    repo = prepare_local_directory(source)
    bare = tmp_path / "forgejo.git"
    subprocess.run(["git", "init", "--bare", "-q", str(bare)], check=True)
    subprocess.run(["git", "remote", "add", "forgejo", str(bare)], cwd=repo, check=True)
    branch = subprocess.run(
        ["git", "branch", "--show-current"], cwd=repo,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    subprocess.run(["git", "push", "-q", "forgejo", branch], cwd=repo, check=True)

    # "Agent" work: clone, mutate, push back
    work = tmp_path / "agent-work"
    subprocess.run(["git", "clone", "-q", str(bare), str(work)], check=True)
    subprocess.run(["git", "config", "user.email", "a@a"], cwd=work, check=True)
    subprocess.run(["git", "config", "user.name", "agent"], cwd=work, check=True)
    edits(work)
    subprocess.run(["git", "add", "-A"], cwd=work, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "agent work", "--allow-empty"], cwd=work, check=True
    )
    subprocess.run(["git", "push", "-q", "origin", branch], cwd=work, check=True)
    return repo


def test_pull_writes_agent_output_into_empty_target(
    source_dir: Path, tmp_path: Path
) -> None:
    def edits(work: Path) -> None:
        (work / "notes.txt").write_text("rewritten by the agent")
        (work / "new-chapter.txt").write_text("brand new")

    _fake_forgejo_session(source_dir, tmp_path, edits)
    target = tmp_path / "pulled"

    pull_local_directory(source_dir, target)

    assert (target / "notes.txt").read_text() == "rewritten by the agent"
    assert (target / "new-chapter.txt").read_text() == "brand new"
    assert (target / "subdir" / "deep.txt").exists()
    # The source is never written to
    assert (source_dir / "notes.txt").read_text() == "some notes"
    assert not (source_dir / "new-chapter.txt").exists()


def test_pull_refuses_non_empty_target(source_dir: Path, tmp_path: Path) -> None:
    """The whole point: never write over the user's existing files."""
    _fake_forgejo_session(source_dir, tmp_path, lambda w: None)
    target = tmp_path / "occupied"
    target.mkdir()
    (target / "precious.txt").write_text("do not clobber")

    with pytest.raises(click.ClickException) as exc:
        pull_local_directory(source_dir, target)

    assert "not empty" in str(exc.value)
    assert (target / "precious.txt").read_text() == "do not clobber"


def test_pull_reports_removals_without_deleting(
    source_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Agent deletions are reported; the user's copy is never removed."""
    _fake_forgejo_session(
        source_dir, tmp_path, lambda w: (w / "notes.txt").unlink()
    )
    target = tmp_path / "pulled"

    pull_local_directory(source_dir, target)

    err = capsys.readouterr().err
    assert "notes.txt" in err
    assert "untouched" in err
    assert (source_dir / "notes.txt").exists(), "source file must survive"
    assert not (target / "notes.txt").exists()


def test_pull_without_a_session_is_an_error(tmp_path: Path) -> None:
    never_used = tmp_path / "never-used"
    never_used.mkdir()
    with pytest.raises(click.ClickException) as exc:
        pull_local_directory(never_used, tmp_path / "out")
    assert "No forge local session" in str(exc.value)


def test_pull_refuses_target_inside_source(source_dir: Path, tmp_path: Path) -> None:
    """Writing inside the source breaks the never-touch-the-source promise, and
    the output would become the next session's input."""
    _fake_forgejo_session(source_dir, tmp_path, lambda w: None)

    with pytest.raises(click.ClickException) as exc:
        pull_local_directory(source_dir, source_dir / "out")

    assert "inside" in str(exc.value)
    assert not (source_dir / "out").exists(), "must refuse before creating anything"


def test_pull_refuses_target_equal_to_source(source_dir: Path, tmp_path: Path) -> None:
    """Caught by the inside-the-source guard, which runs before the emptiness
    check -- so it holds even for a source that happens to be empty."""
    _fake_forgejo_session(source_dir, tmp_path, lambda w: None)

    with pytest.raises(click.ClickException) as exc:
        pull_local_directory(source_dir, source_dir)

    assert "inside" in str(exc.value)


def test_pull_deletion_report_ignores_later_source_edits(
    source_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The baseline is what was pushed, not the live source -- otherwise a file
    the user adds afterwards is reported as deleted by the agent."""
    _fake_forgejo_session(source_dir, tmp_path, lambda w: None)
    (source_dir / "idea-i-added-later.txt").write_text("mine, written after")

    pull_local_directory(source_dir, tmp_path / "pulled")

    err = capsys.readouterr().err
    assert "idea-i-added-later.txt" not in err
