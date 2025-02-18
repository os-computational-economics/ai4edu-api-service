# Copyright (c) 2024.
"""Endpoints associated with access"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from common.JWTValidator import get_jwt
from migrations.models import User, UserWorkspace
from migrations.session import get_db
from utils.response import Response, response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/get_user_list")
def get_user_list(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    page: int = 1,
    page_size: int = 10,
    workspace_id: str = "all",
) -> Response | JSONResponse:
    """Get a list of all users with pagination.

    Args:
        request: Request object
        db: Database session
        page: Page number.
        page_size: Number of users per page.
        workspace_id: Workspace ID, "all" for all workspaces

    Returns:
        Response: A list of users

    """
    user_jwt_content = get_jwt(request.state)

    if workspace_id == "all" and user_jwt_content["system_admin"] is not True:
        return response(
            False,
            status_code=403,
            message="You do not have access to this resource",
        )
    if (
        user_jwt_content["workspace_role"].get(workspace_id, None) is None
        and not user_jwt_content["system_admin"]
    ):
        return response(
            False,
            status_code=403,
            message="You do not have access to this resource",
        )

    is_teacher_or_admin = False
    if (
        user_jwt_content["workspace_role"].get(workspace_id, None) == "teacher"
        or user_jwt_content["system_admin"]
    ):
        is_teacher_or_admin = True
    try:
        if workspace_id == "all":
            query = db.query(User)
        else:
            query = (
                db.query(User)
                .join(UserWorkspace, User.user_id == UserWorkspace.user_id)
                .filter(UserWorkspace.workspace_id == workspace_id)
            )
        total = query.count()
        query = query.order_by(User.user_id)
        skip = (page - 1) * page_size
        users = query.offset(skip).limit(page_size).all()

        user_list = [
            {
                "user_id": user.user_id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "student_id": user.student_id,
                "workspace_role": user.workspace_role if is_teacher_or_admin else None,
            }
            for user in users
        ]

        return response(True, data={"user_list": user_list, "total": total})
    except Exception as e:
        logger.error(f"Error fetching user list: {e}")
        return response(False, status_code=500, message=str(e))
