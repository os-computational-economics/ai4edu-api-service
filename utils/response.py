# Copyright (c) 2024.
"""Class containing utility functions to generate FastAPI responses."""

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from starlette.background import BackgroundTask
from starlette.responses import JSONResponse

from migrations.models import AgentValue

Data = dict[str, Any] | AgentValue  # pyright: ignore[reportExplicitAny]
T = TypeVar("T", bound=Data | None)


class ResponseContent(BaseModel, Generic[T]):
    """Response structure for API responses."""

    status: HTTPStatus = HTTPStatus.OK
    data: T | None = None
    message: str = ""
    success: bool = True

    def __init__(
        self,
        status: HTTPStatus = HTTPStatus.OK,
        data: T | None = None,
        message: str = "",
        success: bool = True,
    ) -> None:
        """Initializes a Response object."""
        super().__init__()
        self.status = status
        self.data = data
        self.message = message
        self.success = success


class Response(JSONResponse, Generic[T]):
    """Typed JSONResponse Type"""

    def __init__(
        self,
        content: ResponseContent[T],
        status_code: HTTPStatus,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        """Initializes a JSON response object"""
        super().__init__(
            content.model_dump(), status_code, headers, media_type, background
        )


def forbidden() -> Response[None]:
    """Sets the default no-access response

    Returns:
        No-access JSON response

    """
    return response(
        success=False,
        message="You do not have access to this resource",
        status=HTTPStatus.FORBIDDEN,
    )


def response(
    success: bool,
    status: HTTPStatus,
    data: T = None,
    message: str = "Success",
) -> Response[T]:
    """Generates a response for FastAPI

    Args:
        success: Indicates if the request was successful.
        data: The payload to return in case of success.
        message: Optional message describing the success or the reason for error.
        status: HTTP status code to use for errors.

    Returns:
        A JSONResponse if fail, or response if success.

    """
    return_status = HTTPStatus.OK if success else status
    return Response[T](
        content=ResponseContent(
            status=return_status, success=success, data=data, message=message
        ),
        status_code=return_status,
    )
