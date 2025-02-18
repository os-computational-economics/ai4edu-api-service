# Copyright (c) 2024.
"""Class containing utility functions to generate FastAPI responses."""

from typing import Any, TypedDict

from starlette.responses import JSONResponse

from migrations.models import AgentValue

Data = dict[str, Any] | AgentValue  # pyright: ignore[reportExplicitAny]


class Response(TypedDict):
    """Response structure for API responses."""

    status: int
    data: Data | None
    message: str


def response(
    success: bool,
    data: Data | None = None,
    message: str = "Success",
    status_code: int = 400,
) -> Response | JSONResponse:
    """Generates a response for FastAPI

    Args:
        success: Indicates if the request was successful.
        data: The payload to return in case of success.
        message: Optional message describing the success or the reason for error.
        status_code: HTTP status code to use for errors.

    Returns:
        A JSONResponse if fail, or response if success.

    """
    if success:
        return {"status": 200, "data": data, "message": message or "Success"}
    return JSONResponse(
        content={"success": False, "message": message, "status_code": status_code},
        status_code=status_code,
    )
