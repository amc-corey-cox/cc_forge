"""Tests for cc_forge.config helpers."""

from __future__ import annotations

import pytest

from cc_forge.config import _resolve_int


def test_resolve_int_parses_valid(monkeypatch):
    monkeypatch.setenv("FORGE_AGENT_PIDS_LIMIT", "1024")
    assert _resolve_int("FORGE_AGENT_PIDS_LIMIT") == 1024


def test_resolve_int_reports_bad_value(monkeypatch):
    monkeypatch.setenv("FORGE_AGENT_PIDS_LIMIT", "lots")
    with pytest.raises(ValueError, match="FORGE_AGENT_PIDS_LIMIT must be an integer"):
        _resolve_int("FORGE_AGENT_PIDS_LIMIT")
