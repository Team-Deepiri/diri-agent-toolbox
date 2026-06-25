"""Structured errors for diri-agent-toolbox."""


class ToolboxError(Exception):
    """Base error for toolbox operations."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__


class ValidationToolboxError(ToolboxError):
    """Invalid input or failed schema validation."""


class HttpToolboxError(ToolboxError):
    """HTTP client or transport failure."""


class FileToolboxError(ToolboxError):
    """Sandboxed file operation violation or I/O error."""


class ConfigurationToolboxError(ToolboxError):
    """Missing or invalid toolbox configuration."""


class DatabaseToolboxError(ToolboxError):
    """Database operation failure."""


class CacheToolboxError(ToolboxError):
    """Cache operation failure."""


class StreamingToolboxError(ToolboxError):
    """Streaming/event operation failure."""


class DeviceToolboxError(ToolboxError):
    """Device or hardware detection failure."""


class ConfidenceToolboxError(ToolboxError):
    """Confidence calculation failure."""
