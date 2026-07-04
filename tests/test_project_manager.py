"""Tests for ProjectManager's folder layout and slugify helper."""

from __future__ import annotations

from dropagent.storage.project_manager import ProjectManager, slugify


def test_slugify_normalizes_title():
    assert slugify("The Last Signal!") == "the-last-signal"
    assert slugify("  Weird   Spacing__Here  ") == "weird-spacing-here"


def test_create_project_builds_expected_subfolders(isolated_settings):
    manager = ProjectManager(isolated_settings)
    paths = manager.create_project("The Last Signal")

    assert paths.root.exists()
    for sub in (
        paths.scenes_dir,
        paths.audio_dir,
        paths.subtitles_dir,
        paths.video_dir,
        paths.exports_dir,
        paths.thumbnails_dir,
        paths.metadata_dir,
    ):
        assert sub.exists() and sub.is_dir()
