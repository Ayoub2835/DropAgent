"""Generates SEO-optimized title/description/hashtags/keywords per platform."""

from __future__ import annotations

import json
import re

from dropagent.exceptions import LLMGenerationError
from dropagent.llm.base import BaseLLMProvider
from dropagent.logging_config import get_logger
from dropagent.models import PlatformMetadata, Story

log = get_logger(__name__)

_PLATFORM_RULES = {
    "youtube": (
        "YouTube Shorts: title under 100 characters, curiosity-driven, keyword-rich. "
        "Description: 2-4 sentences, naturally include primary keywords, end with a soft "
        "call to action, then a line of hashtags. 8-15 hashtags. 10-15 SEO keywords."
    ),
    "tiktok": (
        "TikTok: title/caption under 150 characters, punchy and conversational, can include "
        "1-2 emojis. Description mirrors the caption. 5-8 trending-style hashtags. "
        "8-12 keywords."
    ),
    "snapchat": (
        "Snapchat Spotlight: title under 80 characters, ultra short and intriguing. "
        "Description under 2 sentences. 5-8 hashtags. 6-10 keywords."
    ),
}

_SYSTEM_PROMPT = """You are a social media growth strategist writing publish-ready \
metadata for a short-form video. Respond with ONLY a single valid JSON object (no \
markdown fences, no commentary) with exactly these keys:

{"title": "...", "description": "...", "hashtags": ["...", "..."], "keywords": ["...", "..."]}

Hashtags must NOT include the '#' character (it is added later). Keep everything \
relevant to the story's actual content -- no clickbait unrelated to the plot.
"""

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


class SEOMetadataGenerator:
    def __init__(self, llm: BaseLLMProvider):
        self._llm = llm

    def generate(self, story: Story, platforms: list[str]) -> dict[str, PlatformMetadata]:
        results: dict[str, PlatformMetadata] = {}
        for platform in platforms:
            platform_key = platform.lower()
            rules = _PLATFORM_RULES.get(platform_key, _PLATFORM_RULES["youtube"])
            user_prompt = (
                f"Platform rules: {rules}\n\n"
                f"Story title: {story.title}\n"
                f"Synopsis: {story.synopsis}\n"
                f"Genre: {story.genre}\n\n"
                "Generate the JSON metadata now."
            )
            log.info("Generating %s metadata for %r", platform_key, story.title)
            raw = self._llm.complete(_SYSTEM_PROMPT, user_prompt, temperature=0.8, max_tokens=500)
            results[platform_key] = self._parse(raw, platform_key)
        return results

    @staticmethod
    def _parse(raw: str, platform: str) -> PlatformMetadata:
        match = _JSON_BLOCK_RE.search(raw)
        if not match:
            raise LLMGenerationError(f"Could not find a JSON object in metadata response:\n{raw}")
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise LLMGenerationError(f"Invalid JSON in metadata response: {exc}\n{raw}") from exc

        return PlatformMetadata(
            platform=platform,
            title=str(data.get("title", "")).strip(),
            description=str(data.get("description", "")).strip(),
            hashtags=[str(tag).strip().lstrip("#") for tag in data.get("hashtags", [])],
            keywords=[str(kw).strip() for kw in data.get("keywords", [])],
        )
