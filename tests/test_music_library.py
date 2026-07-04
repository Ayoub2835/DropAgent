"""Tests for MusicLibrary manifest parsing and mood-based selection."""

from __future__ import annotations

import json

from dropagent.audio.music_library import MusicLibrary


def _touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake-audio")


def test_returns_none_when_music_dir_is_empty(tmp_path):
    library = MusicLibrary(tmp_path / "music")
    assert library.select("horror") is None


def test_selects_track_matching_genre(tmp_path):
    music_dir = tmp_path / "music"
    _touch(music_dir / "tense.mp3")
    _touch(music_dir / "warm.mp3")
    manifest = {
        "tracks": [
            {"file": "tense.mp3", "moods": ["horror", "suspense"]},
            {"file": "warm.mp3", "moods": ["romance"]},
        ]
    }
    (music_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    library = MusicLibrary(music_dir)
    selected = library.select("horror")
    assert selected is not None
    assert selected.name == "tense.mp3"


def test_falls_back_to_untagged_track_when_genre_not_found(tmp_path):
    music_dir = tmp_path / "music"
    _touch(music_dir / "generic.mp3")
    manifest = {"tracks": [{"file": "generic.mp3", "moods": []}]}
    (music_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    library = MusicLibrary(music_dir)
    selected = library.select("scifi")
    assert selected is not None
    assert selected.name == "generic.mp3"
