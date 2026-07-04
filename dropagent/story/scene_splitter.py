"""Splits a finished Script into narratable Scenes, each with its own visual prompt."""

from __future__ import annotations

import re

from dropagent.exceptions import LLMGenerationError
from dropagent.llm.base import BaseLLMProvider
from dropagent.logging_config import get_logger
from dropagent.models import Scene, Script

log = get_logger(__name__)

SYSTEM_PROMPT = """You break a short-form video narration script into individual \
scenes for production.

For EACH scene provide:
- The exact narration text for that scene (a contiguous slice of the script, verbatim \
or lightly split for pacing -- do not rewrite the wording).
- A vivid, concrete visual description suitable as a prompt for an AI image/video \
generator (describe subject, action, setting, lighting, mood -- no text overlays, no \
copyrighted characters or logos).

Produce between 4 and 8 scenes covering the ENTIRE script in order, with no gaps and \
no repeated text.

Respond with ONLY a numbered list, one scene per line, in exactly this format:
1. NARRATION: <narration text> || VISUAL: <visual prompt>
2. NARRATION: <narration text> || VISUAL: <visual prompt>
...
"""

_LINE_RE = re.compile(
    r"^\s*\d+\.\s*NARRATION:\s*(?P<narration>.+?)\s*\|\|\s*VISUAL:\s*(?P<visual>.+?)\s*$",
    re.IGNORECASE,
)


class SceneSplitter:
    """Splits a :class:`Script` into a list of :class:`Scene` objects."""

    def __init__(self, llm: BaseLLMProvider):
        self._llm = llm

    def split(self, script: Script) -> list[Scene]:
        user_prompt = f"Script:\n{script.as_single_text()}\n\nSplit this into scenes now."
        log.info("Splitting script into scenes")
        raw = self._llm.complete(SYSTEM_PROMPT, user_prompt, temperature=0.6, max_tokens=1200)
        scenes = self._parse(raw)
        if not scenes:
            log.warning("LLM scene split produced no parsable lines; falling back to naive split")
            scenes = self._naive_fallback(script)
        return scenes

    @staticmethod
    def _parse(raw: str) -> list[Scene]:
        scenes: list[Scene] = []
        for line in raw.splitlines():
            match = _LINE_RE.match(line)
            if not match:
                continue
            scenes.append(
                Scene(
                    index=len(scenes),
                    text=match.group("narration").strip(),
                    visual_prompt=match.group("visual").strip(),
                )
            )
        return scenes

    @staticmethod
    def _naive_fallback(script: Script) -> list[Scene]:
        """Best-effort split used only if the LLM output could not be parsed."""
        sections = [script.hook, script.development, script.climax, script.resolution]
        scenes = []
        for i, text in enumerate(sections):
            text = text.strip()
            if not text:
                continue
            scenes.append(
                Scene(
                    index=i,
                    text=text,
                    visual_prompt=f"Cinematic, atmospheric shot illustrating: {text[:160]}",
                )
            )
        if not scenes:
            raise LLMGenerationError("Unable to derive any scenes from the script.")
        return scenes
