from datetime import datetime
from typing import Any, TypedDict

from fastapi.datastructures import State


class UserJWTContent(TypedDict):
    user_id: int
    first_name: str
    last_name: str
    student_id: str
    workspace_role: dict[str, str]
    system_admin: bool
    email: str
    iat: datetime
    exp: datetime


def defaultJWT() -> UserJWTContent:
    return UserJWTContent(
        user_id=-1,
        first_name="",
        last_name="",
        student_id="",
        workspace_role={},
        system_admin=False,
        email="",
        iat=datetime.now(),
        exp=datetime.now(),
    )


def getJWT(state: State) -> UserJWTContent:
    return (
        parseJWT(state.user_jwt_content) or defaultJWT()  # pyright: ignore[reportAny]
    )


def parseJWT(user_jwt_content: dict[str, Any] | Any) -> UserJWTContent | None:
    ret = None
    try:
        ret = UserJWTContent(
            user_id=int(user_jwt_content["user_id"]),  # pyright: ignore[reportAny]
            first_name=str(
                user_jwt_content["first_name"]  # pyright: ignore[reportAny]
            ),
            last_name=str(user_jwt_content["last_name"]),  # pyright: ignore[reportAny]
            student_id=str(
                user_jwt_content["student_id"]  # pyright: ignore[reportAny]
            ),
            workspace_role=dict(
                [
                    (
                        i,
                        str(
                            user_jwt_content["workspace_role"][
                                i
                            ]  # pyright: ignore[reportAny]
                        ),
                    )
                    for i in user_jwt_content[  # pyright: ignore[reportAny]
                        "workspace_role"
                    ]
                ]
            ),
            system_admin=not not user_jwt_content["student_id"],
            email=str(user_jwt_content["student_id"]),  # pyright: ignore[reportAny]
            iat=datetime.fromtimestamp(
                user_jwt_content["iat"]  # pyright: ignore[reportAny]
            ),
            exp=datetime.fromtimestamp(
                user_jwt_content["exp"]  # pyright: ignore[reportAny]
            ),
        )
    except:
        return None
    return ret
