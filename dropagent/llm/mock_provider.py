"""Deterministic, offline text provider.

Used as the default fallback when no LLM API key is configured, and in the
test suite so the pipeline can be exercised end-to-end without network
access or paid API calls. It produces structurally valid (if formulaic)
output that downstream parsers can rely on.
"""

from __future__ import annotations

from dropagent.llm.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    name = "mock"

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.9,
        max_tokens: int = 1500,
    ) -> str:
        lowered = f"{system_prompt}\n{user_prompt}".lower()

        if "json" in lowered and "hashtag" in lowered:
            return self._mock_metadata()
        if "scene" in lowered and "split" in lowered:
            return self._mock_scenes()
        if "hook" in lowered and "resolution" in lowered:
            return self._mock_script()
        return self._mock_story()

    @staticmethod
    def _mock_story() -> str:
        return (
            "TITLE: The Last Signal\n\n"
            "SYNOPSIS: A lone radio operator on an abandoned arctic station picks up a "
            "transmission that should not exist, and must decide whether to answer it.\n\n"
            "STORY: For six months Mara had heard nothing on channel 9 but static and her "
            "own breathing. Then, at 3 a.m., a voice came through -- calm, familiar, using "
            "her call sign. It said it was already inside the station with her. Mara checked "
            "every door twice, then a third time, before she understood the voice was coming "
            "from the recorder she had used to log her own shifts. It was her voice, "
            "answering questions she had not asked yet. She finally broke the silence and "
            "asked the recorder what came next; it told her, word for word, what she would "
            "say in return."
        )

    @staticmethod
    def _mock_script() -> str:
        return (
            "HOOK: What if the last voice you ever heard on the radio was your own, "
            "answering a question you hadn't asked yet?\n\n"
            "DEVELOPMENT: Mara had been alone at the arctic station for six months when "
            "channel 9 crackled to life at 3 a.m. The voice used her call sign. It said it "
            "was already inside with her.\n\n"
            "CLIMAX: She searched every room twice before realizing the voice matched the "
            "station's old shift recorder -- playing back a log she hadn't recorded yet.\n\n"
            "RESOLUTION: She pressed record and asked the machine what happened next. It "
            "answered in her own voice, word for word, before she could finish the question."
        )

    @staticmethod
    def _mock_scenes() -> str:
        return (
            "1. NARRATION: What if the last voice you ever heard on the radio was your own, "
            "answering a question you hadn't asked yet? || VISUAL: A lone woman in a "
            "fur-lined parka sits at a frost-covered radio console inside a dim arctic "
            "station, blue monitor light on her face, snowstorm visible through a small "
            "window.\n"
            "2. NARRATION: Mara had been alone at the arctic station for six months when "
            "channel 9 crackled to life at 3 a.m. The voice used her call sign. It said it "
            "was already inside with her. || VISUAL: Close-up of an old radio speaker "
            "vibrating with static in a dark room, a digital clock reading 3:00 AM glowing "
            "beside it.\n"
            "3. NARRATION: She searched every room twice before realizing the voice matched "
            "the station's old shift recorder -- playing back a log she hadn't recorded yet. "
            "|| VISUAL: A flashlight beam sweeping across empty metal corridors of an "
            "isolated research station, frost on the walls, long shadows.\n"
            "4. NARRATION: She pressed record and asked the machine what happened next. It "
            "answered in her own voice, word for word, before she could finish the question. "
            "|| VISUAL: Trembling hand pressing the record button on a vintage reel-to-reel "
            "recorder, red light blinking, tense close-up framing."
        )

    @staticmethod
    def _mock_metadata() -> str:
        return (
            '{"title": "The Radio Signal That Knew Her Name", '
            '"description": "A lone arctic radio operator receives a transmission that '
            'shouldn\'t exist -- in her own voice. A short horror story, 100% AI-generated.", '
            '"hashtags": ["horrorstory", "scarystories", "aistory", "shortfilm", "creepy"], '
            '"keywords": ["horror story", "scary story", "AI generated story", "arctic '
            'station", "short horror film"]}'
        )
