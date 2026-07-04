"""Adapts a Story into a short-form video script with hook/development/climax/resolution."""

from __future__ import annotations

import re

from dropagent.exceptions import LLMGenerationError
from dropagent.llm.base import BaseLLMProvider
from dropagent.logging_config import get_logger
from dropagent.models import Script, Story

log = get_logger(__name__)

SYSTEM_PROMPT = """You are a short-form video scriptwriter (YouTube Shorts / TikTok / \
Snapchat Spotlight). Adapt the given original story into a tightly-paced narration \
script.

Structure requirements:
- HOOK: 1-2 sentences, the first thing viewers hear. Must create curiosity or tension \
within 3 seconds so viewers don't scroll away.
- DEVELOPMENT: builds the situation and stakes.
- CLIMAX: the turning point / most intense beat.
- RESOLUTION: a satisfying, punchy ending (can be a twist).

Keep the total narration under 200 words. Write in natural spoken language, short \
sentences, present tense where it heightens tension. Do not add scene directions, \
camera notes or emojis -- only the words to be narrated.

Respond in exactly this format:

HOOK: <text>

DEVELOPMENT: <text>

CLIMAX: <text>

RESOLUTION: <text>
"""

_SECTION_RE = {
    "hook": re.compile(r"HOOK:\s*(.+?)(?=\n\s*DEVELOPMENT:)", re.IGNORECASE | re.DOTALL),
    "development": re.compile(r"DEVELOPMENT:\s*(.+?)(?=\n\s*CLIMAX:)", re.IGNORECASE | re.DOTALL),
    "climax": re.compile(r"CLIMAX:\s*(.+?)(?=\n\s*RESOLUTION:)", re.IGNORECASE | re.DOTALL),
    "resolution": re.compile(r"RESOLUTION:\s*(.+)", re.IGNORECASE | re.DOTALL),
}


class ScriptWriter:
    """Converts a :class:`Story` into a structured :class:`Script`."""

    def __init__(self, llm: BaseLLMProvider):
        self._llm = llm

    def write(self, story: Story) -> Script:
        user_prompt = (
            f"Title: {story.title}\n"
            f"Synopsis: {story.synopsis}\n\n"
            f"Original story:\n{story.full_text}\n\n"
            "Adapt this into the required narration script format."
        )
        log.info("Writing script for story %r", story.title)
        raw = self._llm.complete(SYSTEM_PROMPT, user_prompt, temperature=0.8, max_tokens=700)
        return self._parse(raw)

    @staticmethod
    def _parse(raw: str) -> Script:
        sections: dict[str, str] = {}
        for key, pattern in _SECTION_RE.items():
            match = pattern.search(raw)
            if not match:
                raise LLMGenerationError(f"Could not parse '{key.upper()}' section from script:\n{raw}")
            sections[key] = match.group(1).strip()

        return Script(
            hook=sections["hook"],
            development=sections["development"],
            climax=sections["climax"],
            resolution=sections["resolution"],
            raw_text=raw.strip(),
        )
