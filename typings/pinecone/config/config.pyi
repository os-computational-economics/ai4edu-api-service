"""This type stub file was generated by pyright."""

from typing import NamedTuple

from pinecone.core.openapi.shared.configuration import (
    Configuration as OpenApiConfiguration,
)

class Config(NamedTuple):
    api_key: str = ...
    host: str = ...
    proxy_url: str | None = ...
    proxy_headers: dict[str, str] | None = ...
    ssl_ca_certs: str | None = ...
    ssl_verify: bool | None = ...
    additional_headers: dict[str, str] | None = ...
    source_tag: str | None = ...

class ConfigBuilder:
    """Configurations are resolved in the following order:

    - configs passed as keyword parameters
    - configs specified in environment variables
    - default values (if applicable)
    """

    @staticmethod
    def build(
        api_key: str | None = ...,
        host: str | None = ...,
        proxy_url: str | None = ...,
        proxy_headers: dict[str, str] | None = ...,
        ssl_ca_certs: str | None = ...,
        ssl_verify: bool | None = ...,
        additional_headers: dict[str, str] | None = ...,
        **kwargs,
    ) -> Config: ...
    @staticmethod
    def build_openapi_config(
        config: Config,
        openapi_config: OpenApiConfiguration | None = ...,
        **kwargs,
    ) -> OpenApiConfiguration: ...
