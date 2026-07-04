"""Orchestrates the full story -> multi-platform video pipeline end to end."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from dropagent.audio.music_library import MusicLibrary
from dropagent.config import Settings, get_settings
from dropagent.exceptions import DropAgentError
from dropagent.llm.factory import get_llm_provider
from dropagent.logging_config import get_logger
from dropagent.metadata.seo_generator import SEOMetadataGenerator
from dropagent.models import ProjectResult
from dropagent.storage.project_manager import ProjectManager
from dropagent.story.generator import StoryGenerator
from dropagent.story.scene_splitter import SceneSplitter
from dropagent.story.script_writer import ScriptWriter
from dropagent.subtitles.generator import SubtitleGenerator
from dropagent.video.assembler import VideoAssembler
from dropagent.video.exporter import VideoExporter
from dropagent.video.ffmpeg_utils import get_media_duration
from dropagent.video.thumbnail import ThumbnailGenerator
from dropagent.visuals.factory import get_image_provider
from dropagent.voice.factory import get_tts_provider

log = get_logger(__name__)


class StoryPipeline:
    """Runs every stage described in the project brief, in order.

    1. Original story generation
    2. Script writing (hook / development / climax / resolution)
    3. Scene splitting
    4. Narration synthesis (TTS) per scene
    5. Scene image/video generation
    6. Royalty-free background music selection
    7. Automatic subtitle generation
    8. FFmpeg assembly with transitions
    9. Thumbnail generation
    10. SEO metadata generation per platform
    11. Multi-platform export (YouTube 16:9, TikTok 9:16, Snapchat 9:16)
    12. Organized project folder output
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.llm = get_llm_provider(self.settings)
        self.tts = get_tts_provider(self.settings)
        self.image_provider = get_image_provider(self.settings)
        self.music_library = MusicLibrary(self.settings.assets_dir / "music")
        self.project_manager = ProjectManager(self.settings)

    def run(
        self,
        topic: str,
        genre: str = "general",
        language: str = "en",
        platforms: Optional[list[str]] = None,
    ) -> ProjectResult:
        platforms = platforms or self.settings.export_platforms
        log.info("=== Starting DropAgent pipeline: topic=%r genre=%r ===", topic, genre)

        try:
            story = StoryGenerator(self.llm).generate(topic, genre, language)
            log.info("Step 1/12 done: story generated -> %r", story.title)

            script = ScriptWriter(self.llm).write(story)
            log.info("Step 2/12 done: script written")

            scenes = SceneSplitter(self.llm).split(script)
            log.info("Step 3/12 done: split into %d scenes", len(scenes))

            paths = self.project_manager.create_project(story.title)

            for scene in scenes:
                audio_stub = paths.audio_dir / f"scene_{scene.index:03d}"
                narration_path = self.tts.synthesize(scene.text, audio_stub)
                scene.narration_audio_path = narration_path
                scene.narration_duration = get_media_duration(narration_path)

                image_stub = paths.scenes_dir / f"scene_{scene.index:03d}"
                scene.image_path = self.image_provider.generate(
                    scene.visual_prompt,
                    image_stub,
                    self.settings.image_width,
                    self.settings.image_height,
                )
            log.info("Steps 4-5/12 done: narration + visuals generated for all scenes")

            self.project_manager.save_story_and_script(paths, story, script, scenes)

            music_path = self.music_library.select(genre)
            log.info("Step 6/12 done: background music %s", music_path or "none available")

            subtitle_path = SubtitleGenerator(self.settings).generate(
                scenes, paths.subtitles_dir / "captions.srt"
            )
            log.info("Step 7/12 done: subtitles generated -> %s", subtitle_path)

            master_video_path = VideoAssembler(self.settings).assemble(
                scenes,
                subtitle_path,
                paths.video_dir / "master.mp4",
                music_path=music_path,
            )
            log.info("Step 8/12 done: master video assembled -> %s", master_video_path)

            thumbnail_path = ThumbnailGenerator().generate(
                scenes[0].image_path, story.title, paths.thumbnails_dir / "thumbnail.jpg"
            )
            log.info("Step 9/12 done: thumbnail generated -> %s", thumbnail_path)

            metadata = SEOMetadataGenerator(self.llm).generate(story, platforms)
            self.project_manager.save_platform_metadata(paths, metadata)
            log.info("Step 10/12 done: SEO metadata generated for %s", ", ".join(platforms))

            exports = VideoExporter(self.settings).export_all(master_video_path, paths.exports_dir, platforms)
            log.info("Step 11/12 done: exported %d platform videos", len(exports))

            log.info("Step 12/12 done: project organized at %s", paths.root)
            log.info("=== Pipeline finished successfully ===")

            return ProjectResult(
                paths=paths,
                story=story,
                script=script,
                scenes=scenes,
                master_video_path=master_video_path,
                thumbnail_path=thumbnail_path,
                subtitle_path=subtitle_path,
                metadata=metadata,
                exports=exports,
            )
        except DropAgentError:
            log.exception("Pipeline failed")
            raise
