"""Generates an SRT subtitle file synced to the final narration timeline.

Two strategies are supported (``SUBTITLE_MODE`` in settings):

- ``even`` (default, no extra dependency): splits each scene's narration
  text into short caption-sized chunks and distributes them proportionally
  across that scene's known audio duration. Good enough for punchy,
  short-form captions and requires nothing beyond ffprobe.
- ``whisper``: transcribes each scene's narration audio with
  ``faster-whisper`` to get real word-level timing, then falls back to
  ``even`` per-scene if the optional dependency is missing or transcription
  fails for a given clip.
"""

from __future__ import annotations

from pathlib import Path

from dropagent.config import Settings, get_settings
from dropagent.exceptions import SubtitleGenerationError
from dropagent.logging_config import get_logger
from dropagent.models import Scene, SubtitleCue

log = get_logger(__name__)

_WORDS_PER_CUE = 5


class SubtitleGenerator:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def generate(self, scenes: list[Scene], output_path: Path) -> Path:
        if not scenes:
            raise SubtitleGenerationError("Cannot generate subtitles: no scenes provided.")

        cues: list[SubtitleCue] = []
        cursor = 0.0
        use_whisper = self._settings.subtitle_mode == "whisper"

        for scene in scenes:
            duration = scene.narration_duration
            if duration <= 0:
                log.warning("Scene %d has no known duration; skipping in subtitles.", scene.index)
                continue

            scene_cues = None
            if use_whisper and scene.narration_audio_path:
                scene_cues = self._try_whisper(scene, cursor)

            if scene_cues is None:
                scene_cues = self._even_split(scene, cursor, duration)

            cues.extend(scene_cues)
            cursor += duration

        for i, cue in enumerate(cues, start=1):
            cue.index = i

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self._to_srt(cues), encoding="utf-8")
        log.info("Wrote %d subtitle cues to %s", len(cues), output_path)
        return output_path

    def _try_whisper(self, scene: Scene, offset: float) -> list[SubtitleCue] | None:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            log.warning(
                "SUBTITLE_MODE=whisper requested but 'faster-whisper' is not installed; "
                "falling back to even timing. Install it with `pip install faster-whisper`."
            )
            return None

        try:
            model = _get_whisper_model(self._settings.whisper_model_size)
            segments, _ = model.transcribe(str(scene.narration_audio_path), word_timestamps=False)
            cues = []
            for segment in segments:
                cues.append(
                    SubtitleCue(
                        index=0,
                        start=offset + segment.start,
                        end=offset + segment.end,
                        text=segment.text.strip(),
                    )
                )
            return cues or None
        except Exception as exc:  # noqa: BLE001 - fall back rather than fail the run
            log.warning("Whisper transcription failed for scene %d (%s); using even timing.", scene.index, exc)
            return None

    @staticmethod
    def _even_split(scene: Scene, offset: float, duration: float) -> list[SubtitleCue]:
        words = scene.text.split()
        if not words:
            return []

        chunks = [
            words[i : i + _WORDS_PER_CUE] for i in range(0, len(words), _WORDS_PER_CUE)
        ]
        seconds_per_word = duration / len(words)

        cues = []
        cursor = offset
        for chunk in chunks:
            chunk_duration = seconds_per_word * len(chunk)
            cues.append(
                SubtitleCue(index=0, start=cursor, end=cursor + chunk_duration, text=" ".join(chunk))
            )
            cursor += chunk_duration
        return cues

    @staticmethod
    def _to_srt(cues: list[SubtitleCue]) -> str:
        lines = []
        for cue in cues:
            lines.append(str(cue.index))
            lines.append(f"{_format_timestamp(cue.start)} --> {_format_timestamp(cue.end)}")
            lines.append(cue.text)
            lines.append("")
        return "\n".join(lines)


_whisper_model_cache: dict[str, object] = {}


def _get_whisper_model(model_size: str):
    if model_size not in _whisper_model_cache:
        from faster_whisper import WhisperModel

        _whisper_model_cache[model_size] = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _whisper_model_cache[model_size]


def _format_timestamp(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
