"""Assembles narrated scenes into a single master video using FFmpeg.

Pipeline for the master video:

1. Each scene's still image becomes a silent video clip with a gentle
   Ken Burns zoom, held for exactly that scene's narration duration.
2. Scene clips are concatenated with professional crossfade (``xfade``)
   transitions.
3. Scene narration clips are concatenated with matching audio crossfades
   (``acrossfade``) so voice and picture stay in sync.
4. Optional royalty-free background music is looped, trimmed and mixed
   under the narration at a configurable volume.
5. Auto-generated subtitles (SRT) are burned into the final video as
   styled captions.

The result is one 9:16 "master" file that :mod:`dropagent.video.exporter`
then reframes for each target platform.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Optional

from dropagent.config import Settings, get_settings
from dropagent.exceptions import VideoAssemblyError
from dropagent.logging_config import get_logger
from dropagent.models import Scene
from dropagent.video.ffmpeg_utils import get_media_duration, run_ffmpeg

log = get_logger(__name__)

MASTER_WIDTH = 1080
MASTER_HEIGHT = 1920


class VideoAssembler:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def assemble(
        self,
        scenes: list[Scene],
        subtitle_path: Path,
        output_path: Path,
        music_path: Optional[Path] = None,
    ) -> Path:
        if not scenes:
            raise VideoAssemblyError("Cannot assemble a video with zero scenes.")
        for scene in scenes:
            if not scene.image_path or not scene.narration_audio_path:
                raise VideoAssemblyError(
                    f"Scene {scene.index} is missing its image or narration audio."
                )

        with tempfile.TemporaryDirectory(prefix="dropagent_assemble_") as tmp:
            tmp_dir = Path(tmp)
            clip_paths = [self._build_scene_clip(scene, tmp_dir) for scene in scenes]
            durations = [scene.narration_duration for scene in scenes]

            silent_video = tmp_dir / "master_silent.mp4"
            self._concat_video_with_transitions(clip_paths, durations, silent_video)

            narration_track = tmp_dir / "narration.mp3"
            self._concat_audio_with_transitions(
                [scene.narration_audio_path for scene in scenes], durations, narration_track
            )

            final_audio = narration_track
            if music_path is not None:
                final_audio = tmp_dir / "final_audio.mp3"
                self._mix_music(narration_track, music_path, final_audio)

            combined_video = tmp_dir / "combined.mp4"
            self._mux(silent_video, final_audio, combined_video)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            self._burn_subtitles(combined_video, subtitle_path, output_path)

        log.info("Master video assembled at %s", output_path)
        return output_path

    def _build_scene_clip(self, scene: Scene, tmp_dir: Path) -> Path:
        duration = max(scene.narration_duration, self._settings.scene_min_duration)
        fps = self._settings.video_fps
        frames = max(int(round(duration * fps)), 1)
        clip_path = tmp_dir / f"scene_{scene.index:03d}.mp4"

        zoompan = (
            f"scale={MASTER_WIDTH}:{MASTER_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={MASTER_WIDTH}:{MASTER_HEIGHT},"
            f"zoompan=z='min(zoom+0.0008,1.15)':d={frames}:s={MASTER_WIDTH}x{MASTER_HEIGHT}:fps={fps}"
        )
        run_ffmpeg(
            [
                "-loop", "1",
                "-i", str(scene.image_path),
                "-t", f"{duration:.3f}",
                "-vf", zoompan,
                "-r", str(fps),
                "-pix_fmt", "yuv420p",
                "-an",
                str(clip_path),
            ],
            description=f"scene {scene.index} clip render",
        )
        return clip_path

    def _concat_video_with_transitions(
        self, clip_paths: list[Path], durations: list[float], output_path: Path
    ) -> None:
        transition = self._settings.transition_duration
        args: list[str] = []
        for clip in clip_paths:
            args += ["-i", str(clip)]

        if len(clip_paths) == 1:
            run_ffmpeg([*args, "-c", "copy", str(output_path)], description="single-scene video copy")
            return

        filter_parts = []
        prev_label = "0:v"
        cumulative = durations[0]
        for i in range(1, len(clip_paths)):
            out_label = f"v{i}" if i < len(clip_paths) - 1 else "vout"
            offset = max(cumulative - transition, 0.0)
            filter_parts.append(
                f"[{prev_label}][{i}:v]xfade=transition=fade:duration={transition:.3f}:"
                f"offset={offset:.3f}[{out_label}]"
            )
            cumulative = cumulative + durations[i] - transition
            prev_label = out_label

        run_ffmpeg(
            [
                *args,
                "-filter_complex", ";".join(filter_parts),
                "-map", f"[{prev_label}]",
                "-pix_fmt", "yuv420p",
                str(output_path),
            ],
            description="video crossfade concatenation",
        )

    def _concat_audio_with_transitions(
        self, audio_paths: list[Path], durations: list[float], output_path: Path
    ) -> None:
        transition = self._settings.transition_duration
        args: list[str] = []
        for audio in audio_paths:
            args += ["-i", str(audio)]

        if len(audio_paths) == 1:
            run_ffmpeg(
                [*args, "-ar", "44100", "-ac", "2", str(output_path)],
                description="single-scene audio normalize",
            )
            return

        normalize = ";".join(
            f"[{i}:a]aformat=sample_rates=44100:channel_layouts=stereo[a{i}n]"
            for i in range(len(audio_paths))
        )
        filter_parts = [normalize]
        prev_label = "a0n"
        for i in range(1, len(audio_paths)):
            out_label = f"ax{i}" if i < len(audio_paths) - 1 else "aout"
            filter_parts.append(
                f"[{prev_label}][a{i}n]acrossfade=d={transition:.3f}:c1=tri:c2=tri[{out_label}]"
            )
            prev_label = out_label

        run_ffmpeg(
            [
                *args,
                "-filter_complex", ";".join(filter_parts),
                "-map", f"[{prev_label}]",
                str(output_path),
            ],
            description="audio crossfade concatenation",
        )

    def _mix_music(self, narration_path: Path, music_path: Path, output_path: Path) -> None:
        narration_duration = get_media_duration(narration_path)
        db = self._settings.music_volume_db
        run_ffmpeg(
            [
                "-i", str(narration_path),
                "-stream_loop", "-1",
                "-i", str(music_path),
                "-filter_complex",
                (
                    f"[1:a]aformat=sample_rates=44100:channel_layouts=stereo,"
                    f"volume={db}dB,atrim=0:{narration_duration:.3f}[music];"
                    f"[0:a]aformat=sample_rates=44100:channel_layouts=stereo[voice];"
                    "[voice][music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
                ),
                "-map", "[aout]",
                str(output_path),
            ],
            description="background music mixing",
        )

    def _mux(self, video_path: Path, audio_path: Path, output_path: Path) -> None:
        run_ffmpeg(
            [
                "-i", str(video_path),
                "-i", str(audio_path),
                "-map", "0:v",
                "-map", "1:a",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                str(output_path),
            ],
            description="video/audio mux",
        )

    def _burn_subtitles(self, video_path: Path, subtitle_path: Path, output_path: Path) -> None:
        escaped_srt = str(subtitle_path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        style = (
            "FontName=DejaVu Sans,FontSize=20,Bold=1,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,BorderStyle=3,Outline=2,Shadow=0,"
            "Alignment=2,MarginV=140"
        )
        run_ffmpeg(
            [
                "-i", str(video_path),
                "-vf", f"subtitles='{escaped_srt}':force_style='{style}'",
                "-c:v", "libx264",
                "-crf", "20",
                "-preset", "medium",
                "-c:a", "copy",
                str(output_path),
            ],
            description="subtitle burn-in",
        )


def ffmpeg_available() -> bool:
    return shutil.which(get_settings().ffmpeg_binary) is not None
