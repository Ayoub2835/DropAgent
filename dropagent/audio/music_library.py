"""Picks a royalty-free background music track for a given genre/mood.

DropAgent does not download or bundle third-party music (that would risk
shipping tracks with unclear licensing). Instead, it manages a *local*
library at ``assets/music`` that you populate yourself from a royalty-free
source (see ``assets/music/README.md`` for recommended sources) and tag
via ``assets/music/manifest.json``:

    {
      "tracks": [
        {"file": "tense_pulse.mp3", "moods": ["horror", "suspense", "thriller"]},
        {"file": "warm_piano.mp3", "moods": ["drama", "romance", "wholesome"]},
        {"file": "epic_rise.mp3", "moods": ["adventure", "motivational", "action"]}
      ]
    }

If no manifest or no matching track is found, ``select`` returns ``None``
and the video assembler simply skips background music rather than failing
the whole run.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dropagent.logging_config import get_logger

log = get_logger(__name__)

_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg"}


@dataclass
class MusicTrack:
    path: Path
    moods: list[str]


class MusicLibrary:
    """Loads ``manifest.json`` and resolves a track for a requested mood/genre."""

    def __init__(self, music_dir: Path):
        self._music_dir = music_dir
        self._tracks: list[MusicTrack] = self._load_manifest()

    def _load_manifest(self) -> list[MusicTrack]:
        manifest_path = self._music_dir / "manifest.json"
        if not manifest_path.exists():
            log.warning(
                "No music manifest found at %s -- background music will be skipped. "
                "See assets/music/README.md to add royalty-free tracks.",
                manifest_path,
            )
            return self._discover_untagged_tracks()

        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            log.error("Could not parse %s: %s", manifest_path, exc)
            return []

        tracks: list[MusicTrack] = []
        for entry in data.get("tracks", []):
            track_path = self._music_dir / entry["file"]
            if not track_path.exists():
                log.warning("Manifest references missing file %s -- skipping", track_path)
                continue
            tracks.append(MusicTrack(path=track_path, moods=[m.lower() for m in entry.get("moods", [])]))
        return tracks

    def _discover_untagged_tracks(self) -> list[MusicTrack]:
        if not self._music_dir.exists():
            return []
        return [
            MusicTrack(path=path, moods=[])
            for path in sorted(self._music_dir.iterdir())
            if path.suffix.lower() in _AUDIO_EXTENSIONS
        ]

    def select(self, genre: str, seed: Optional[int] = None) -> Optional[Path]:
        """Return a track path matching ``genre``, or any track, or ``None``."""
        if not self._tracks:
            return None

        genre_lower = genre.lower()
        rng = random.Random(seed)

        matching = [t for t in self._tracks if genre_lower in t.moods]
        if matching:
            return rng.choice(matching).path

        untagged = [t for t in self._tracks if not t.moods]
        if untagged:
            return rng.choice(untagged).path

        log.info("No music tagged for genre=%r; picking any available track.", genre)
        return rng.choice(self._tracks).path
