"""Custom exception hierarchy for the extractor project."""


class ExtractorError(Exception):
    """Base exception for the entire project."""


class ConfigurationError(ExtractorError):
    """Configuration error (env vars, paths, etc.)."""


class TemplateError(ExtractorError):
    """Template parsing/validation error."""


class VLMClientError(ExtractorError):
    """Error when calling VLM API."""


class VLMAuthError(VLMClientError):
    """Invalid API key."""


class VLMRateLimitError(VLMClientError):
    """Rate limited (429)."""


class VLMResponseError(VLMClientError):
    """Invalid response from VLM (JSON parse fail, missing fields)."""


class ValidationError(VLMResponseError):
    """Missing fields in response compared to template."""


class ImageLoadError(ExtractorError):
    """Error when loading/encoding images."""
