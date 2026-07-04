"""Custom exception hierarchy for DropAgent.

Keeping a small, explicit exception tree makes failures in the pipeline
easy to catch, log and report at the right granularity instead of leaking
raw third-party exceptions (requests.HTTPError, subprocess.CalledProcessError...)
all the way up to the CLI.
"""


class DropAgentError(Exception):
    """Base class for all DropAgent errors."""


class ConfigurationError(DropAgentError):
    """Raised when required configuration/environment variables are missing or invalid."""


class LLMGenerationError(DropAgentError):
    """Raised when story/script/metadata text generation fails."""


class TTSGenerationError(DropAgentError):
    """Raised when narration audio synthesis fails."""


class VisualGenerationError(DropAgentError):
    """Raised when scene image/video generation fails."""


class SubtitleGenerationError(DropAgentError):
    """Raised when subtitle (SRT) generation fails."""


class VideoAssemblyError(DropAgentError):
    """Raised when FFmpeg fails to assemble, mux or export a video."""


class PublishingError(DropAgentError):
    """Raised when publishing to an external platform fails."""


class ProviderNotAvailableError(DropAgentError):
    """Raised when a requested provider cannot be used (missing key/dependency)."""
