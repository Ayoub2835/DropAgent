"""Generates a 100% original story concept from a topic and genre.

The system prompt explicitly instructs the model to avoid reproducing or
closely paraphrasing existing copyrighted works (books, movies, published
authors' plots) and to invent original characters, settings and plot
beats instead.
"""

from __future__ import annotations

import re

from dropagent.exceptions import LLMGenerationError
from dropagent.llm.base import BaseLLMProvider
from dropagent.logging_config import get_logger
from dropagent.models import Story

log = get_logger(__name__)

SYSTEM_PROMPT = """You are an award-winning short-fiction writer who creates 100% \
ORIGINAL stories for short-form video (YouTube Shorts, TikTok, Snapchat Spotlight).

Hard rules:
- Never copy, closely paraphrase or reuse plots, characters, settings or lines \
from any existing copyrighted book, film, show or published author.
- Invent original characters and an original premise every time.
- Write in vivid, concrete, sensory language suited for narration over video.
- Keep the story self-contained: a clear beginning, middle and end.
- Target 45-90 seconds of spoken narration (roughly 130-230 words).

Always respond in exactly this format, with no extra commentary:

TITLE: <a short, punchy title>

SYNOPSIS: <one or two sentences summarizing the premise>

STORY: <the full story text, ready to be narrated>
"""

_TITLE_RE = re.compile(r"TITLE:\s*(.+)", re.IGNORECASE)
_SYNOPSIS_RE = re.compile(r"SYNOPSIS:\s*(.+?)(?=\n\s*STORY:)", re.IGNORECASE | re.DOTALL)
_STORY_RE = re.compile(r"STORY:\s*(.+)", re.IGNORECASE | re.DOTALL)


class StoryGenerator:
    """Turns a topic/genre pair into a structured, original :class:`Story`."""

    def __init__(self, llm: BaseLLMProvider):
        self._llm = llm

    def generate(self, topic: str, genre: str = "general", language: str = "en") -> Story:
        user_prompt = (
            f"Genre: {genre}\n"
            f"Topic / theme to inspire an ORIGINAL story: {topic}\n"
            f"Language: {language}\n\n"
            "Write one original short story following the required format."
        )
        log.info("Generating original story for topic=%r genre=%r", topic, genre)
        raw = self._llm.complete(SYSTEM_PROMPT, user_prompt, temperature=1.0, max_tokens=900)
        return self._parse(raw, topic=topic, genre=genre, language=language)

    @staticmethod
    def _parse(raw: str, *, topic: str, genre: str, language: str) -> Story:
        title_match = _TITLE_RE.search(raw)
        synopsis_match = _SYNOPSIS_RE.search(raw)
        story_match = _STORY_RE.search(raw)

        if not story_match:
            raise LLMGenerationError(f"Could not parse STORY section from LLM output:\n{raw}")

        title = title_match.group(1).strip() if title_match else topic.title()
        synopsis = synopsis_match.group(1).strip() if synopsis_match else ""
        full_text = story_match.group(1).strip()

        return Story(
            topic=topic,
            genre=genre,
            title=title,
            synopsis=synopsis,
            full_text=full_text,
            language=language,
        )
