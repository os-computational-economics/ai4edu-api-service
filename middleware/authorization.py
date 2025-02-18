# Copyright (c) 2024.
"""Toools for authorizing access to endpoints."""

import logging
from typing import TypedDict, override

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from common.JWTValidator import UserJWTContent, parse_jwt
from utils.endpoint_access_map import AccessMap, PersonType, endpoint_access_map
from utils.token_utils import parse_token
from utils.whitelist import whitelist

logger = logging.getLogger(__name__)


class Tokens(TypedDict):
    """An object containing access and refresh tokens."""

    access_token: str | None
    refresh_token: str | None


Role = dict[PersonType, bool]


def extract_token(auth_header: str) -> Tokens:
    """Extract access and refresh tokens from the authentication header.

    Args:
        auth_header: The authentication header containing access and refresh tokens

    Returns:
        An object containing access and refresh tokens.

    """
    access_token = None
    refresh_token = None
    if auth_header and auth_header.startswith("Bearer "):
        # Remove the 'Bearer ' prefix
        token_string = auth_header[7:]
        # Split the token string into key-value pairs
        token_pairs = token_string.split("&")
        # Extract tokens from key-value pairs
        for pair in token_pairs:
            if "=" in pair:
                key, value = pair.split("=")
                if key == "access":
                    access_token = value if value else None
                elif key == "refresh":
                    refresh_token = value if value else None
    return {"access_token": access_token, "refresh_token": refresh_token}


def has_access(
    endpoint_access_map: AccessMap,
    user_access: Role,
    current_path: str,
) -> bool:
    """Check if the user has access to the specified endpoint.

    Args:
        endpoint_access_map: A dictionary mapping endpoint paths to their access roles
        user_access: A dictionary containing the user's roles
        current_path: The path of the endpoint being accessed

    Returns:
        A boolean indicating whether the user has access to the specified endpoint

    """
    # ! vvv FIX 7-NESTED BLOCK BELOW
    # Check if the current path exists in the endpoint_access_map
    if current_path in endpoint_access_map:
        access_roles = endpoint_access_map[current_path]
        # Check if the user has access based on their roles
        for role, has_role in user_access.items():
            if has_role and access_roles.get(role, False):
                return True
    else:
        # Check if the current path matches any dynamic endpoint pattern
        for endpoint_pattern in endpoint_access_map:
            if "{" in endpoint_pattern:
                # Split the endpoint pattern and current path into parts
                pattern_parts = endpoint_pattern.split("/")
                path_parts = current_path.split("/")

                # Check if the number of parts matches
                if len(pattern_parts) == len(path_parts):
                    # Check if all non-dynamic parts match
                    for i in range(len(pattern_parts)):
                        if (
                            "{" not in pattern_parts[i]
                            and pattern_parts[i] != path_parts[i]
                        ):
                            break
                    else:
                        # All non-dynamic parts matched, check user access
                        access_roles = endpoint_access_map[endpoint_pattern]
                        for role, has_role in user_access.items():
                            if has_role and access_roles.get(role, False):
                                return True
    # ! ^^^

    # If no matching endpoint found or user doesn't have access, return False
    return False


def extract_actual_path(path: str) -> str:
    """Extract the actual path from the given path.

    Args:
        path: The original path

    Returns:
        The path extracted from the given path, excluding the first three elements

    """
    # Split the path by the forward slash (/)
    path_parts = path.split("/")
    # Remove the first three elements from the path_parts list
    actual_path_parts = path_parts[4:]
    # Join the remaining elements back together with a forward slash (/)
    return "/" + "/".join(actual_path_parts)


def extract_role(access_token_load: UserJWTContent | None) -> Role:
    """Extract the role from the access token payload

    if the user is system_admin, the role admin is True
    if the user is at least one teacher in a workspace, the role teacher is True
    if the user is at least one student in a workspace, the role student is True

    Args:
        access_token_load: access token payload

    Returns:
        a dictionary mapping roles to whether the user has that role

    """
    if access_token_load is None:
        return {"admin": False, "teacher": False, "student": False}
    default_role: Role = {"admin": False, "teacher": False, "student": True}
    if access_token_load["system_admin"]:
        default_role["admin"] = True
    for _, role in access_token_load["workspace_role"].items():
        if role == "teacher":
            default_role["teacher"] = True
            break
    return default_role


class AuthorizationMiddleware(BaseHTTPMiddleware):
    """A middleware for authorizing access to endpoints."""

    @override
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response | JSONResponse:
        """Check if the user has access to the specified endpoint.

        Args:
            request: The incoming request
            call_next: The next endpoint to be called

        Returns:
            A response or a JSON response indicating the result of the authorization

        """
        path = extract_actual_path(request.url.path)
        print("path", path)
        if path in whitelist:
            return await call_next(request)

        tokens = extract_token(request.headers.get("Authorization", ""))
        if tokens["access_token"] is not None:
            parse_result = parse_token(tokens["access_token"])
            if parse_result["success"] and parse_result["data"] is not None:
                user_access = extract_role(
                    parse_jwt(parse_result["data"]),  # pyright: ignore[reportAny]
                )
                if has_access(endpoint_access_map, user_access, path):
                    request.state.user_jwt_content = parse_result["data"]
                    return await call_next(request)
            else:
                return JSONResponse(
                    content={
                        "success": False,
                        "message": parse_result["message"],
                        "status_code": parse_result["status_code"],
                    },
                    status_code=401,
                )
        return JSONResponse(
            content={"success": False, "message": "unauthorized", "status_code": 401},
            status_code=401,
        )
