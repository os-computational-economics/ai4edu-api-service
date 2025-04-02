# Copyright (c) 2024.
"""Class containing utility functions to generate FastAPI responses."""

from collections.abc import Mapping
from http import HTTPStatus
from typing import Generic, TypeVar

from fastapi import Response as FastAPIResponse
from pydantic import BaseModel

from migrations.models import (
    ModelReturn,
)

Q = TypeVar("Q", bound=ModelReturn)


class APIListReturn(ModelReturn, Generic[Q]):
    """Generic API response for list of objects"""

    items: list[Q]
    total: int


class APIListReturnPage(APIListReturn[Q]):
    """API response for list of objects with metadata"""

    page: int
    page_size: int


ResponseData = ModelReturn | APIListReturn[ModelReturn] | APIListReturnPage[ModelReturn]
T = TypeVar("T", bound=ResponseData | None)


class Response(BaseModel, Generic[T]):
    """Response structure for API responses."""

    data: T | None = None
    message: str = ""
    success: bool = True

    def __init__(
        self,
        data: T | None = None,
        message: str = "",
        success: bool = True,
    ) -> None:
        """Initializes a Response object."""
        super().__init__()
        self.data = data
        self.message = message
        self.success = success


class Responses(Generic[T]):
    """Class for generating FastAPI responses."""

    @staticmethod
    def forbidden(
        response_obj: FastAPIResponse,
        data: T = None,
    ) -> Response[T]:
        """Sets the default no-access response

        Returns:
            No-access JSON response

        """
        return Responses[T].response(
            response_obj,
            success=False,
            data=data,
            message="You do not have access to this resource",
            status=HTTPStatus.FORBIDDEN,
        )

    @staticmethod
    def forbidden_list(
        response_obj: FastAPIResponse,
        data: APIListReturn[Q] | None = None,
    ) -> Response[APIListReturn[Q]]:
        """Sets the default no-access response for a list

        Args:
            response_obj: FastAPIResponse to update.
            data: List of data to return in case of success.

        Returns:
            No-access JSON response for a list

        """
        ret_data: APIListReturn[Q] = data if data else {"items": [], "total": 0}
        return Responses[APIListReturn[Q]].forbidden(response_obj, data=ret_data)

    @staticmethod
    def forbidden_list_page(
        response_obj: FastAPIResponse,
        data: APIListReturnPage[Q] | None = None,
    ) -> Response[APIListReturnPage[Q]]:
        """Sets the default no-access response for a list

        Args:
            response_obj: FastAPIResponse to update.
            data: List of data to return in case of success.

        Returns:
            No-access JSON response for a list

        """
        ret_data: APIListReturnPage[Q] = (
            data if data else {"items": [], "total": 0, "page": 0, "page_size": 0}
        )
        return Responses[APIListReturnPage[Q]].forbidden(response_obj, data=ret_data)

    @staticmethod
    def response(
        response_obj: FastAPIResponse,
        success: bool,
        status: HTTPStatus | None,
        data: T = None,
        message: str = "Success",
        headers: Mapping[str, str] | None = None,
    ) -> Response[T]:
        """Generates a response for FastAPI

        Args:
            response_obj: The FastAPI response object to update.
            success: Indicates if the request was successful.
            data: The payload to return in case of success.
            message: Optional message describing the success or the reason for error.
            status: HTTP status code to use for errors.
            headers: Optional headers to include in the response.

        Returns:
            A JSONResponse if fail, or response if success.

        """
        return_status = (
            status
            if status
            else (HTTPStatus.OK if success else HTTPStatus.INTERNAL_SERVER_ERROR)
        )
        response_obj.status_code = return_status
        if headers:
            response_obj.headers.update(headers)
        return Response[T](success=success, data=data, message=message)
