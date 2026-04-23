class AIWebError(Exception):
    """Base exception for browser AI automation."""


class AIWebPromptInputNotFound(AIWebError):
    """Raised when prompt input cannot be located."""


class AIWebResponseNotFound(AIWebError):
    """Raised when a new response block cannot be located."""
