import logging
from typing import Any
from migrations.models import User, UserWorkspace

from fastapi import APIRouter, Depends, Request
from utils.response import response

from sqlalchemy.orm import Session
from migrations.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/get_user_list")
def get_user_list(
    request: Request,
    db: Session | None,  # pyright: ignore[reportRedeclaration]
    page: int = 1,
    page_size: int = 10,
    workspace_id: str = "all",
):
    """
    Get a list of all users with pagination.
    :param request: Request object
    :param db: Database session
    :param page: Page number.
    :param page_size: Number of users per page.
    :param workspace_id: Workspace ID, "all" for all workspaces
    """
    if db is None:
        db: Session = Depends(get_db)

    user_jwt_content: dict[str, Any] = (
        request.state.user_jwt_content
    )  # pyright: ignore[reportAny]

    if workspace_id == "all" and user_jwt_content["system_admin"] is not True:
        return response(
            False, status_code=403, message="You do not have access to this resource"
        )
    if (
        user_jwt_content["workspace_role"].get(workspace_id, None) is None
        and not user_jwt_content["system_admin"]
    ):
        return response(
            False, status_code=403, message="You do not have access to this resource"
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
