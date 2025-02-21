# Copyright (c) 2024.
"""Class containing utility functions to generate FastAPI responses."""

from http import HTTPStatus
from typing import Any

from pydantic import BaseModel
from starlette.responses import JSONResponse

from migrations.models import AgentValue

Data = dict[str, Any] | AgentValue  # pyright: ignore[reportExplicitAny]


class Response(BaseModel):
    """Response structure for API responses."""

    status: int = 200
    data: Data | None = None
    message: str = ""
    success: bool = True

    def __init__(
        self,
        status: int = 200,
        data: Data | None = None,
        message: str = "",
        success: bool = True,
    ) -> None:
        """Initializes a Response object."""
        super().__init__()
        self.status = status
        self.data = data
        self.message = message
        self.success = success


def forbidden() -> JSONResponse:
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
    data: Data | None = None,
    message: str = "Success",
) -> JSONResponse:
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
    return JSONResponse(
        content=Response(
            status=return_status, success=success, data=data, message=message
        ).model_dump(),
        status_code=return_status,
    )
