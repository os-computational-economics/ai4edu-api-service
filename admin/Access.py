# Copyright (c) 2024.
"""Endpoints associated with access"""

import logging
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi import Response as FastAPIResponse
from sqlalchemy.orm import Session

from common.JWTValidator import get_jwt
from migrations.models import (
    PrivilegedUserReturn,
    User,
    UserReturn,
    UserValue,
    UserWorkspace,
    Workspace,
    privileged_user_return,
)
from migrations.session import get_db
from utils.response import APIListReturn, Response, Responses

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/get_user_list")
def get_user_list(
    request: Request,
    response: FastAPIResponse,
    db: Annotated[Session, Depends(get_db)],
    page: int = 1,
    page_size: int = 10,
    workspace_id: str = "all",
) -> Response[APIListReturn[UserReturn]]:
    """Get a list of all users with pagination.

    Args:
        request: Request object
        response: Response object
        db: Database session
        page: Page number.
        page_size: Number of users per page.
        workspace_id: Workspace ID, "all" for all workspaces

    Returns:
        Response: A list of users

    """
    user_jwt_content = get_jwt(request.state)

    if workspace_id == "all" and user_jwt_content["system_admin"] is not True:
        return Responses[UserReturn].forbidden_list(response)
    if (
        user_jwt_content["workspace_role"].get(workspace_id, None) is None
        and not user_jwt_content["system_admin"]
    ):
        return Responses[UserReturn].forbidden_list(response)

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
        users: list[UserValue] = query.offset(skip).limit(page_size).all()  # pyright: ignore[reportAssignmentType]

        user_list: list[UserReturn] = [
            {
                "user_id": user.user_id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "student_id": user.student_id,
                "workspace_role": {
                    workspace_id: user.workspace_role.get(workspace_id, "")
                }
                if is_teacher_or_admin and workspace_id != "all"
                else {},
            }
            for user in users
        ]

        return Responses[APIListReturn[UserReturn]].response(
            response,
            success=True,
            status=HTTPStatus.OK,
            data={"items": user_list, "total": total},
        )
    except Exception as e:
        logger.error(f"Error fetching user list: {e}")
        return Responses[APIListReturn[UserReturn]].response(
            response,
            data={"items": [], "total": 0},
            success=False,
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            message=str(e),
        )


@router.get("/get_privileged_user_list")
def get_privileged_user_list(
    request: Request,
    response: FastAPIResponse,
    db: Annotated[Session, Depends(get_db)],
    page: int = 1,
    page_size: int = 10,
) -> Response[APIListReturn[PrivilegedUserReturn]]:
    """Get a list of privileged users (system admins and workspace admins) with pagination.

    Args:
        request: Request object
        response: Response object
        db: Database session
        page: Page number.
        page_size: Number of users per page.

    Returns:
        Response: A list of privileged users with their admin status and created workspaces

    """
    user_jwt_content = get_jwt(request.state)

    if not user_jwt_content["system_admin"]:
        return Responses[PrivilegedUserReturn].forbidden_list(response)

    try:
        # Get privileged users
        query = db.query(User).filter(
            (User.system_admin == True) | (User.workspace_admin == True)
        )
        total = query.count()
        query = query.order_by(User.user_id)
        skip = (page - 1) * page_size
        users: list[UserValue] = query.offset(skip).limit(page_size).all()  # pyright: ignore[reportAssignmentType]

        # Get created workspaces for all users in one query
        user_ids = [user.user_id for user in users]
        workspaces = (
            db.query(
                Workspace.workspace_id, Workspace.workspace_name, Workspace.created_by
            )
            .filter(Workspace.created_by.in_(user_ids))
            .all()
        )

        # Group workspaces by creator
        user_workspaces: dict[int, dict[UUID, str]] = {}
        for workspace_id, workspace_name, created_by in workspaces:
            if created_by not in user_workspaces:
                user_workspaces[created_by] = {}
            user_workspaces[created_by][workspace_id] = workspace_name

        user_list: list[PrivilegedUserReturn] = [
            privileged_user_return(
                user, created_workspaces=user_workspaces.get(user.user_id, {})
            )
            for user in users
        ]

        return Responses[APIListReturn[PrivilegedUserReturn]].response(
            response,
            success=True,
            status=HTTPStatus.OK,
            data={"items": user_list, "total": total},
        )
    except Exception as e:
        logger.error(f"Error fetching privileged user list: {e}")
        return Responses[APIListReturn[PrivilegedUserReturn]].response(
            response,
            data={"items": [], "total": 0},
            success=False,
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            message=str(e),
        )
