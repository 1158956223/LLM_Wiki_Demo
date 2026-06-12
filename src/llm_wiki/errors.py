class LlmWikiError(Exception):
    """Base error for LLM Wiki operations."""


class ProjectNotInitializedError(LlmWikiError):
    """Raised when a command needs an initialized project."""


class DeepSeekUnavailableError(LlmWikiError):
    """Raised when DeepSeek is required but cannot be used."""


class InvalidProposalError(LlmWikiError):
    """Raised when a proposal is invalid or unsafe to apply."""


class UnsafePathError(LlmWikiError):
    """Raised when a path would escape the project root."""
