"""Unit tests for the text stages (story, script, scenes, SEO) using the mock LLM."""

from __future__ import annotations

from dropagent.llm.mock_provider import MockLLMProvider
from dropagent.metadata.seo_generator import SEOMetadataGenerator
from dropagent.story.generator import StoryGenerator
from dropagent.story.scene_splitter import SceneSplitter
from dropagent.story.script_writer import ScriptWriter


def test_story_generator_parses_title_synopsis_and_text():
    story = StoryGenerator(MockLLMProvider()).generate("an arctic radio station", genre="horror")
    assert story.title
    assert story.synopsis
    assert len(story.full_text.split()) > 20


def test_script_writer_produces_all_four_sections():
    story = StoryGenerator(MockLLMProvider()).generate("an arctic radio station", genre="horror")
    script = ScriptWriter(MockLLMProvider()).write(story)
    assert script.hook and script.development and script.climax and script.resolution
    assert "hook" not in script.as_single_text().lower().split()[0:1]


def test_scene_splitter_produces_ordered_scenes_with_visual_prompts():
    story = StoryGenerator(MockLLMProvider()).generate("an arctic radio station", genre="horror")
    script = ScriptWriter(MockLLMProvider()).write(story)
    scenes = SceneSplitter(MockLLMProvider()).split(script)

    assert len(scenes) >= 4
    for i, scene in enumerate(scenes):
        assert scene.index == i
        assert scene.text
        assert scene.visual_prompt


def test_seo_metadata_generator_returns_valid_metadata_per_platform():
    story = StoryGenerator(MockLLMProvider()).generate("an arctic radio station", genre="horror")
    metadata = SEOMetadataGenerator(MockLLMProvider()).generate(story, ["youtube", "tiktok", "snapchat"])

    assert set(metadata.keys()) == {"youtube", "tiktok", "snapchat"}
    for platform, meta in metadata.items():
        assert meta.platform == platform
        assert meta.title
        assert isinstance(meta.hashtags, list) and meta.hashtags
        assert isinstance(meta.keywords, list) and meta.keywords
        assert meta.hashtags_line().startswith("#")
