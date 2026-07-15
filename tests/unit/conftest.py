"""Shared fixtures for unit tests.

Unit tests must run against a clean, predictable environment. Because forge runs
its own CI *inside* the forge loop, the job environment can carry ambient
FORGE_*/FORGEJO_* (and agent ANTHROPIC_*/OLLAMA_*) variables. Left in place they
leak into config loading and the gh-shim, so a test behaves differently there
than on a dev machine. Strip them before every unit test so hermeticity is the
default rather than something each test has to remember.
"""

from __future__ import annotations

import os

import pytest

_FORGE_ENV_PREFIXES = ("FORGE_", "FORGEJO_", "ANTHROPIC_", "OLLAMA_")


@pytest.fixture(autouse=True)
def _clean_forge_env(monkeypatch):
    for key in list(os.environ):
        if key.startswith(_FORGE_ENV_PREFIXES):
            monkeypatch.delenv(key, raising=False)
