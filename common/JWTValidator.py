# Copyright (c) 2024.
"""Methods for creating and validating JWTs."""

from datetime import datetime
from typing import Any, TypedDict
from zoneinfo import ZoneInfo

from fastapi.datastructures import State

from common.EnvManager import getenv

CONFIG = getenv()


class UserJWTContent(TypedDict):
    """Structure representing the parsed JWT content"""

    user_id: int
    first_name: str
    last_name: str
    student_id: str
    # !TODO: Type check the workspace role type
    workspace_role: dict[str, str]
    system_admin: bool
    workspace_admin: bool
    email: str
    iat: datetime
    exp: datetime


def default_jwt() -> UserJWTContent:
    """Creates the default empty JWT

    Returns:
        A UserJWTContent object with default values

    """
    return UserJWTContent(
        user_id=-1,
        first_name="",
        last_name="",
        student_id="",
        workspace_role={},
        system_admin=False,
        workspace_admin=False,
        email="",
        iat=datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"])),
        exp=datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"])),
    )


def get_jwt(state: State) -> UserJWTContent:
    """Get a parsed JWT from a state object

    Args:
        state: The FastAPI state object

    Returns:
        A UserJWTContent object if the JWT is valid and has the expected structure,
        otherwise None

    """
    return (
        parse_jwt(state.user_jwt_content) or default_jwt()  # pyright: ignore[reportAny]
    )


def parse_jwt(user_jwt_content: dict[str, Any] | Any) -> UserJWTContent | None:  # noqa: ANN401 # pyright: ignore[reportExplicitAny]
    """Parses a JWT and returns its content as a UserJWTContent object

    Args:
        user_jwt_content: The parsed JSON from a client

    Returns:
        A UserJWTContent object if the JWT is valid and has the expected structure,
        otherwise None

    """
    ret = None
    try:
        ret = UserJWTContent(
            user_id=int(user_jwt_content["user_id"]),  # pyright: ignore[reportAny]
            first_name=str(
                user_jwt_content["first_name"],  # pyright: ignore[reportAny]
            ),
            last_name=str(user_jwt_content["last_name"]),  # pyright: ignore[reportAny]
            student_id=str(
                user_jwt_content["student_id"],  # pyright: ignore[reportAny]
            ),
            workspace_role={
                i: str(
                    user_jwt_content["workspace_role"][i],  # pyright: ignore[reportAny]
                )
                for i in user_jwt_content[  # pyright: ignore[reportAny]
                    "workspace_role"
                ]
            },
            system_admin=bool(user_jwt_content["system_admin"]),  # pyright: ignore[reportAny]
            workspace_admin=bool(user_jwt_content["workspace_admin"]),  #pyright: ignore[reportAny]
            email=str(user_jwt_content["email"]),  # pyright: ignore[reportAny]
            iat=datetime.fromtimestamp(
                user_jwt_content["iat"],  # pyright: ignore[reportAny]
                tz=ZoneInfo(CONFIG["TIMEZONE"]),
            ),
            exp=datetime.fromtimestamp(
                user_jwt_content["exp"],  # pyright: ignore[reportAny]
                tz=ZoneInfo(CONFIG["TIMEZONE"]),
            ),
        )
    except Exception as _:
        return None
    return ret
