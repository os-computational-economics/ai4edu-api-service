"""This type stub file was generated by pyright."""

from .config import Config

logger = ...
DEFAULT_CONTROLLER_HOST = ...

class PineconeConfig:
    @staticmethod
    def build(
        api_key: str | None = ...,
        host: str | None = ...,
        additional_headers: dict[str, str] | None = ...,
        **kwargs,
    ) -> Config: ...
