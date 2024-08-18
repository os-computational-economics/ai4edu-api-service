# Copyright (c) 2024.
# -*-coding:utf-8 -*-
"""
@file: Workspace.py
@author: Jerry(Ruihuang)Yang
@email: rxy216@case.edu
@time: 7/2/24 23:50
"""
import csv
import io
import logging
import chardet
from fastapi import APIRouter, Depends, UploadFile, File, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified

from migrations.models import User, UserWorkspace, Workspace
from migrations.session import get_db
from utils.response import response
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class WorkspaceCreate(BaseModel):
    workspace_id: str
    workspace_name: str
    workspace_password: str
    school_id: int = 0


class StudentJoinWorkspace(BaseModel):
    workspace_id: str
    password: str


class UserRoleUpdate(BaseModel):
    user_id: int
    student_id: str
    workspace_id: str
    role: str  # student, teacher, pending


@router.post("/create_workspace")
def create_workspace(request: Request, workspace: WorkspaceCreate, db: Session = Depends(get_db)):
    if not request.state.user_jwt_content['system_admin']:
        return response(False, status_code=403, message="You do not have access to this resource")
    try:
        new_workspace = Workspace(
            workspace_id=workspace.workspace_id,
            workspace_name=workspace.workspace_name,
            workspace_password=workspace.workspace_password,
            school_id=workspace.school_id
        )
        db.add(new_workspace)
        db.commit()
        return response(True, message="Workspace created successfully")
    except IntegrityError:
        db.rollback()
        return response(False, status_code=400, message="Workspace with this name already exists")
    except Exception as e:
        logger.error(f"Error creating workspace: {e}")
        db.rollback()
        return response(False, status_code=500, message=str(e))


@router.post("/add_users_via_csv")
def add_users_via_csv(request: Request, workspace_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user_workspace_role = request.state.user_jwt_content['workspace_role'].get(workspace_id, None)
    if user_workspace_role != 'teacher' and not request.state.user_jwt_content['system_admin']:
        return response(False, status_code=403, message="You do not have access to this resource")
    try:
        # Read the file to detect encoding
        raw_content = file.file.read()
        result = chardet.detect(raw_content)
        encoding = result['encoding']

        # Decode the content using the detected encoding
        content = raw_content.decode(encoding)

        reader = csv.DictReader(io.StringIO(content))

        for row in reader:
            student_id = row["Network ID"]

            if not student_id:
                continue

            # Check if the record already exists
            existing_user_workspace = db.query(UserWorkspace).filter_by(workspace_id=workspace_id,
                                                                        student_id=student_id).first()

            if existing_user_workspace:
                continue  # Skip this row if it already exists

            user_workspace = UserWorkspace(
                student_id=student_id,
                workspace_id=workspace_id,
                role="pending"
            )
            db.add(user_workspace)
            db.commit()

        return response(True, message="Users added via CSV successfully")
    except Exception as e:
        logger.error(f"Error adding users via CSV: Please make sure you save the roster as a CSV file and try again")
        db.rollback()
        return response(False, status_code=500, message=str(e))


@router.post("/student_join_workspace")
def student_join_workspace(request: Request, join_workspace: StudentJoinWorkspace, db: Session = Depends(get_db)):
    user_id = request.state.user_jwt_content['user_id']
    student_id = request.state.user_jwt_content['student_id']
    try:
        user = db.query(User).filter(User.user_id == user_id, User.student_id == student_id).first()
        if not user:
            return response(False, status_code=404, message="User not found")

        workspace = db.query(Workspace).filter(Workspace.workspace_id == join_workspace.workspace_id).first()

        if join_workspace.password != workspace.workspace_password:
            return response(False, status_code=400, message="Failed to join workspace")

        user_workspace = db.query(UserWorkspace).filter(
            UserWorkspace.student_id == student_id,
            UserWorkspace.workspace_id == join_workspace.workspace_id
        ).first()

        if not user_workspace:
            return response(False, status_code=404, message="Not authorized to join this workspace")

        if user_workspace.role != "pending":
            return response(False, status_code=400, message="User already in this workspace")

        user_workspace.role = "student"
        user_workspace.user_id = user_id
        user.workspace_role[join_workspace.workspace_id] = "student"
        flag_modified(user, "workspace_role")
        db.commit()

        return response(True, message="User added to workspace successfully")
    except Exception as e:
        logger.error(f"Error adding user to workspace: {e}")
        db.rollback()
        return response(False, status_code=500, message=str(e))


@router.post("/delete_user_from_workspace")
def delete_user_from_workspace(request: Request, user_role_update: UserRoleUpdate, db: Session = Depends(get_db)):
    user_workspace_role = request.state.user_jwt_content['workspace_role'].get(user_role_update.workspace_id, None)
    if user_workspace_role != 'teacher' and not request.state.user_jwt_content['system_admin']:
        return response(False, status_code=403, message="You do not have access to this resource")
    try:
        user = db.query(User).filter(User.user_id == user_role_update.user_id,
                                     User.student_id == user_role_update.student_id).first()
        if not user:
            return response(False, status_code=404, message="User not found")

        user_workspace = db.query(UserWorkspace).filter(
            UserWorkspace.user_id == user.user_id,
            UserWorkspace.student_id == user_role_update.student_id,
            UserWorkspace.workspace_id == user_role_update.workspace_id
        ).first()

        if not user_workspace:
            return response(False, status_code=404, message="User not in this workspace")

        db.delete(user_workspace)
        del user.workspace_role[user_role_update.workspace_id]
        flag_modified(user, "workspace_role")
        db.commit()

        return response(True, message="User deleted from workspace successfully")
    except Exception as e:
        logger.error(f"Error deleting user from workspace: {e}")
        db.rollback()
        return response(False, status_code=500, message=str(e))


@router.post("/set_user_role")
def set_user_role(request: Request, user_role_update: UserRoleUpdate, db: Session = Depends(get_db)):
    user_workspace_role = request.state.user_jwt_content['workspace_role'].get(user_role_update.workspace_id, None)
    if user_workspace_role != 'teacher' and not request.state.user_jwt_content['system_admin']:
        return response(False, status_code=403, message="You do not have access to this resource")
    try:
        user = db.query(User).filter(User.user_id == user_role_update.user_id,
                                     User.student_id == user_role_update.student_id).first()
        if not user:
            return response(False, status_code=404, message="User not found")

        user_workspace = db.query(UserWorkspace).filter(
            UserWorkspace.user_id == user.user_id,
            UserWorkspace.student_id == user_role_update.student_id,
            UserWorkspace.workspace_id == user_role_update.workspace_id
        ).first()

        if not user_workspace:
            return response(False, status_code=404, message="User not in this workspace")

        user_workspace.role = user_role_update.role
        user.workspace_role[user_role_update.workspace_id] = user_role_update.role
        db.commit()

        return response(True, message="User role updated successfully")
    except Exception as e:
        logger.error(f"Error setting user role: {e}")
        db.rollback()
        return response(False, status_code=500, message=str(e))


@router.post("/set_user_role_with_student_id")
def set_user_role_with_student_id(request: Request, user_role_update: UserRoleUpdate, db: Session = Depends(get_db)):
    """
    This should be able to set any user to any role in any workspace, even if the user is not in that workspace
    :param request:
    :param user_role_update:
    :param db:
    :return:
    """
    if not request.state.user_jwt_content['system_admin']:
        return response(False, status_code=403, message="You do not have access to this resource")
    try:
        user = db.query(User).filter(User.student_id == user_role_update.student_id).first()
        if not user:
            return response(False, status_code=404, message="User not found")

        user_workspace = db.query(UserWorkspace).filter(
            UserWorkspace.user_id == user.user_id,
            UserWorkspace.student_id == user_role_update.student_id,
            UserWorkspace.workspace_id == user_role_update.workspace_id
        ).first()

        if not user_workspace:
            # create a new user workspace record
            new_user_workspace = UserWorkspace(
                user_id=user.user_id,
                student_id=user.student_id,
                workspace_id=user_role_update.workspace_id,
                role=user_role_update.role
            )
            db.add(new_user_workspace)
            db.commit()
        else:
            user_workspace.role = user_role_update.role

        user.workspace_role[user_role_update.workspace_id] = user_role_update.role
        flag_modified(user, "workspace_role")
        db.commit()

        return response(True, message="User role updated successfully")
    except Exception as e:
        logger.error(f"Error setting user role: {e}")
        db.rollback()
        return response(False, status_code=500, message=str(e))


@router.get("/get_workspace_list")
def get_workspace_list(request: Request, db: Session = Depends(get_db)):
    if not request.state.user_jwt_content['system_admin']:
        return response(False, status_code=403, message="You do not have access to this resource")
    try:
        workspaces = db.query(Workspace).all()
        workspace_list = [
            {
                "workspace_id": workspace.workspace_id,
                "workspace_name": workspace.workspace_name,
                "school_id": workspace.school_id
            }
            for workspace in workspaces
        ]
        return response(True, data={"workspace_list": workspace_list})
    except Exception as e:
        logger.error(f"Error fetching workspace list: {e}")
        return response(False, status_code=500, message=str(e))
