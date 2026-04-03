class JobScoutError(Exception):
    """Base error for the project."""


class UnsupportedSourceError(JobScoutError):
    """Raised when the source is not supported."""


class BlockDetectedError(JobScoutError):
    """Raised when the page appears to be blocked/authwalled."""
