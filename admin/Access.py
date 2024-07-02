import logging
from migrations.models import User, RefreshToken

from fastapi import APIRouter, Depends, Request
from utils.response import response

from sqlalchemy.orm import Session
from migrations.session import get_db

from pydantic import BaseModel
from typing import Dict


class RoleUpdate(BaseModel):
    student_id: str
    role: Dict[str, bool]


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/get_user_list")
def get_user_list(
        request: Request,
        db: Session = Depends(get_db),
        page: int = 1,
        page_size: int = 10,
        workspace_id: str = None
):
    """
    Get a list of all users with pagination.
    :param request: Request object
    :param db: Database session
    :param page: Page number.
    :param page_size: Number of users per page.
    :param workspace_id: Workspace ID, "all" for all workspaces
    """
    if workspace_id == "all" and request.state.user_jwt_content['system_admin'] is not True:
        return response(False, status_code=403, message="You do not have access to this resource")
    if request.state.user_jwt_content['workspace_role'].get(workspace_id, None) is None:
        return response(False, status_code=403, message="You do not have access to this resource")

    is_teacher_or_admin = False
    if request.state.user_jwt_content['workspace_role'].get(workspace_id, None) == 'teacher' or \
            request.state.user_jwt_content['system_admin']:
        is_teacher_or_admin = True
    try:
        query = db.query(User)
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


@router.post("/grant_access")
def grant_access(
        role_update: RoleUpdate,
        db: Session = Depends(get_db)
):
    """
    Grant access to a user by updating their role.
    """
    try:
        user = db.query(User).filter(User.student_id == role_update.student_id).first()
        if not user:
            return response(False, status_code=404, message="User not found")

        user.role = role_update.role
        db.commit()

        return response(True, message="User role updated successfully")
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        db.rollback()
        return response(False, status_code=500, message=str(e))
