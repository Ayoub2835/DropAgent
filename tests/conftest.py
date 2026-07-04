"""Shared pytest fixtures: force every provider to its offline/mock variant."""

from __future__ import annotations

import pytest

from dropagent.config import get_settings


@pytest.fixture
def isolated_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("TTS_PROVIDER", "pyttsx3")
    monkeypatch.setenv("IMAGE_PROVIDER", "placeholder")
    monkeypatch.setenv("SUBTITLE_MODE", "even")
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setenv("ASSETS_DIR", str(tmp_path / "assets"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    return get_settings(refresh=True)
