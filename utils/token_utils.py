# Copyright (c) 2024.
"""Utility functions for managing tokens and JWTs"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from common.EnvManager import getenv

CONFIG = getenv()

logger = logging.getLogger(__name__)


def fix_key(broken_key: str) -> str:
    """Fix the broken key by removing 'n' every 64 characters, and reformatting the key

    Args:
        broken_key: The broken JWT private key

    Returns:
        The fixed JWT private key

    """
    # Step 1: Find the header and footer
    header_start = broken_key.find("-----BEGIN")
    header_end = broken_key.find("-----", header_start + len("-----BEGIN")) + len(
        "-----",
    )
    header = broken_key[header_start:header_end]

    footer_start = broken_key.find("-----END")
    footer_end = broken_key.find("-----", footer_start + len("-----END")) + len("-----")
    footer = broken_key[footer_start:footer_end]

    # Step 2: Extract the body between header and footer
    body_start = header_end
    body_end = footer_start
    body = broken_key[body_start:body_end]

    # Step 3: Remove 'n' every 64 characters in the body
    body = body[1:]  # remove the first 'n'
    body_chunks = [
        body[i : i + 65] for i in range(0, len(body), 65)
    ]  # split the body into 65-character chunks
    body_chunks = [
        chunk[:-1] for chunk in body_chunks
    ]  # remove the last 'n' in each chunk
    formatted_body = "\n".join(body_chunks)

    # Step 4: Assemble everything
    return f"{header}\n{formatted_body}\n{footer}"


private_key = CONFIG["JWT_PRIVATE_KEY"]
# if the key starts with a lower case n after the header, it is broken
header_start = private_key.find("-----BEGIN")
header_end = private_key.find("-----", header_start + len("-----BEGIN")) + len("-----")
if private_key[header_end] == "n":
    private_key = fix_key(private_key)
public_key = CONFIG["JWT_PUBLIC_KEY"]
# if the key starts with a lower case n after the header, it is broken
header_start = public_key.find("-----BEGIN")
header_end = public_key.find("-----", header_start + len("-----BEGIN")) + len("-----")
if public_key[header_end] == "n":
    public_key = fix_key(public_key)
algorithm = "RS256"


def jwt_generator(
    user_id: str,
    first_name: str,
    last_name: str,
    student_id: str,
    workspace_role: dict[str, Any],  # pyright: ignore[reportExplicitAny]
    system_admin: bool,
    email: str,
) -> str:
    """Generates a JWT token with the given user information

    Args:
        user_id: The unique identifier of the user
        first_name: The first name of the user
        last_name: The last name of the user
        student_id: The student ID of the user
        workspace_role: The role of the user in the workspace
        system_admin: Whether the user is a system admin or not
        email: The email of the user

    Returns:
        The JWT token with the given user information

    """
    payload: dict[str, str | dict[str, Any] | bool | datetime] = {  # pyright: ignore[reportExplicitAny]
        "user_id": user_id,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "student_id": student_id,
        "workspace_role": workspace_role,
        "system_admin": system_admin,
        "iat": datetime.now(tz=UTC),
        "exp": datetime.now(tz=UTC) + timedelta(minutes=30),
    }
    return jwt.encode(payload, private_key, algorithm=algorithm)


def parse_token(jwt_token: str) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Parses the JWT token and returns the decoded payload

    Args:
        jwt_token: The JWT token to be parsed

    Returns:
        The decoded payload of the JWT token,
        or an error message if the token is missing, expired, or invalid.

    """
    if not jwt_token:
        logger.error("Token missing")
        return {"success": False, "status_code": 401000, "message": "Token missing"}
    try:
        decoded: dict[str, Any] = jwt.decode(  # pyright: ignore[reportExplicitAny]
            jwt_token, public_key, algorithms=[algorithm],
        )
        return {"success": True, "status_code": 200, "message": "", "data": decoded}
    except jwt.ExpiredSignatureError:
        logger.error("Token has expired")
        return {"success": False, "status_code": 401001, "message": "Token has expired"}
    except jwt.InvalidTokenError:
        logger.error("Invalid Token")
        return {"success": False, "status_code": 401002, "message": "Invalid token"}
