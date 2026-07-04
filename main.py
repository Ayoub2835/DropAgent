#!/usr/bin/env python3
"""DropAgent CLI entrypoint.

Usage:
    python main.py generate --topic "a lighthouse keeper who finds a message in a bottle" \\
        --genre mystery --platforms youtube tiktok snapchat

    python main.py publish --project output/my-story-20260704-101500 --platforms youtube

Run `python main.py --help` for the full option list.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dropagent.config import get_settings
from dropagent.exceptions import DropAgentError
from dropagent.logging_config import get_logger, setup_logging
from dropagent.models import ProjectResult
from dropagent.pipeline import StoryPipeline

log = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dropagent",
        description="Generate original AI stories as ready-to-publish social videos.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate a full story-to-video project.")
    generate.add_argument("--topic", required=True, help="Topic/theme to inspire an original story.")
    generate.add_argument("--genre", default="general", help="Story genre/mood (e.g. horror, drama).")
    generate.add_argument("--language", default="en", help="Language code for narration/subtitles.")
    generate.add_argument(
        "--platforms",
        nargs="+",
        default=None,
        choices=["youtube", "tiktok", "snapchat"],
        help="Platforms to export for (default: from EXPORT_PLATFORMS env var).",
    )
    generate.add_argument(
        "--publish",
        action="store_true",
        help="Attempt to publish via configured official APIs after generation.",
    )

    publish = subparsers.add_parser("publish", help="Publish an already-generated project.")
    publish.add_argument("--project", required=True, help="Path to a project folder under output/.")
    publish.add_argument(
        "--platforms",
        nargs="+",
        default=["youtube"],
        choices=["youtube", "tiktok", "snapchat"],
    )

    return parser


def run_generate(args: argparse.Namespace) -> ProjectResult:
    pipeline = StoryPipeline()
    result = pipeline.run(
        topic=args.topic,
        genre=args.genre,
        language=args.language,
        platforms=args.platforms,
    )
    _print_summary(result)

    if args.publish:
        _publish_result(result, args.platforms or pipeline.settings.export_platforms)

    return result


def _publish_result(result: ProjectResult, platforms: list[str]) -> None:
    from dropagent.publishing.factory import get_publisher

    for export in result.exports:
        if export.platform not in platforms:
            continue
        publisher = get_publisher(export.platform)
        metadata = result.metadata.get(export.platform)
        if metadata is None:
            log.warning("No metadata generated for platform %s; skipping publish.", export.platform)
            continue
        if not publisher.is_configured():
            log.warning(
                "Publisher for %s is not configured (missing credentials); skipping.",
                export.platform,
            )
            continue
        try:
            url = publisher.publish(export.path, result.thumbnail_path, metadata)
            log.info("Published to %s: %s", export.platform, url)
        except DropAgentError as exc:
            log.error("Publishing to %s failed: %s", export.platform, exc)


def _print_summary(result: ProjectResult) -> None:
    print("\n" + "=" * 60)
    print(f"Story: {result.story.title}")
    print(f"Project folder: {result.paths.root}")
    print(f"Master video: {result.master_video_path}")
    print(f"Thumbnail: {result.thumbnail_path}")
    print(f"Subtitles: {result.subtitle_path}")
    print("Exports:")
    for export in result.exports:
        print(f"  - {export.platform} ({export.aspect_ratio}): {export.path}")
    print("Metadata:")
    for platform, meta in result.metadata.items():
        print(f"  - {platform}: {meta.title}")
    print("=" * 60 + "\n")


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    get_settings()

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "generate":
            run_generate(args)
        elif args.command == "publish":
            from dropagent.models import ExportedVideo, PlatformMetadata
            from dropagent.publishing.factory import get_publisher

            project_root = Path(args.project)
            for platform in args.platforms:
                video_path = project_root / "exports" / f"{platform}.mp4"
                thumbnail_path = project_root / "thumbnails" / "thumbnail.jpg"
                metadata_path = project_root / "metadata" / f"{platform}.json"
                if not video_path.exists() or not metadata_path.exists():
                    log.error("Missing export or metadata for %s in %s", platform, project_root)
                    continue

                import json

                data = json.loads(metadata_path.read_text(encoding="utf-8"))
                metadata = PlatformMetadata(**data)
                publisher = get_publisher(platform)
                if not publisher.is_configured():
                    log.warning("Publisher for %s is not configured; skipping.", platform)
                    continue
                url = publisher.publish(video_path, thumbnail_path, metadata)
                log.info("Published to %s: %s", platform, url)
        return 0
    except DropAgentError as exc:
        log.error("DropAgent error: %s", exc)
        return 1
    except KeyboardInterrupt:
        log.warning("Interrupted by user.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
