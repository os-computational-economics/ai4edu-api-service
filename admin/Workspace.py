# Copyright (c) 2024.
"""Workspace related classes."""

import csv
import io
import logging
import uuid
from uuid import UUID as UUID_TYPE
from http import HTTPStatus
from typing import Annotated
from random import randrange

import chardet
from fastapi import APIRouter, BackgroundTasks, Depends, Request, UploadFile
from fastapi import Response as FastAPIResponse
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlalchemy.exc import IntegrityError, MultipleResultsFound, NoResultFound
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from common.JWTValidator import get_jwt
from migrations.models import (
    User,
    UserValue,
    UserWorkspace,
    UserWorkspaceValue,
    Workspace,
    WorkspaceReturn,
    WorkspaceStatus,
    WorkspaceValue,
    workspace_return,
)
from migrations.session import get_db
from utils.response import APIListReturnPage, Response, Responses

logger = logging.getLogger(__name__)

router = APIRouter()


class WorkspaceCreate(BaseModel):
    """A Class describing the object sent to create a new workspace."""

    workspace_name: str
    school_id: int = 0
    user_id: int
    workspace_prompt: str
    workspace_comment: str


class WorkspaceUpdateStatus(BaseModel):
    """A Class describing the object sent to update the status of a workspace."""

    workspace_id: UUID_TYPE
    workspace_status: WorkspaceStatus


class StudentAddWorkspace(BaseModel):
    """A Class describing the object sent to create a new workspace."""

    students: list[str]


class WorkspaceAdminRoleUpdate(BaseModel):
    """A Class describing the object set to update one's workspace admin role"""

    user_id: int
    workspace_admin: bool


class StudentJoinWorkspace(BaseModel):
    """A Class describing the object sent to join a workspace as a student."""

    workspace_id: UUID_TYPE
    workspace_join_code: str


class UserRoleUpdate(BaseModel):
    """A Class describing the object sent to update a user role in a workspace."""

    calling_user_id: int
    user_id: int
    workspace_id: UUID_TYPE
    role: str  # student, teacher, pending


class UserDelete(BaseModel):
    """A Class describing the object sent to update a user role in a workspace."""

    user_id: int
    workspace_id: UUID_TYPE


def gen_random_join_code(join_code_len: int=8):
    """Generate a random join code for a workspace

    Args:
        join_code_len: the length of the join code. Defaults to 8

    Returns:
        The new workspace join code
    """

    # Defines the length of the join code
    new_join_code = ""
    
    for _ in range(0, join_code_len):
        # Add a random digit to the join code
        new_join_code = new_join_code + str(randrange(10))

    logger.info(f"Join code: {new_join_code}")
    
    return new_join_code


@router.post("/create_workspace")
def create_workspace(
    request: Request,
    response: FastAPIResponse,
    workspace: WorkspaceCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Response[None]:
    """Create a new workspace record in the database.

    Args:
        request: FastAPI request object
        response: FastAPI response object
        workspace: WorkspaceCreate object containing workspace details
        db: SQLAlchemy database session

    Returns:
        Success message or 400 if exists

    """
    user_jwt_content = get_jwt(request.state)
    if not user_jwt_content["system_admin"] and not user_jwt_content["workspace_admin"]:
        return Responses[None].forbidden(response)
    try:
        # TODO: Determine if the user can enter a custom UUID for the workspace ID
        #       Assumedly, it should be random always
        # NOTE: uuid1 is used since it reduces the chance of a uuid collision to 0
        #       due to it using timestamp data in the generated uuid
        new_workspace_id = str(uuid.uuid1())
        new_workspace_join_code = gen_random_join_code()

        # If this join code would cause an integrity error, regenerate it
        is_join_code_unique = False
        max_attempts = 100  # Cap the maximum number of attempts due to the cost of these queries
        num_iterations = 0
        while not is_join_code_unique and num_iterations < max_attempts:
            existing_workspace: WorkspaceValue | None = (
                db.query(Workspace).filter(Workspace.workspace_join_code == new_workspace_join_code).first()
            ) # pyright: ignore[reportAssignmentType]
            
            if existing_workspace is not None:
                new_workspace_join_code = gen_random_join_code()
            else:
                is_join_code_unique = True
            
            num_iterations += 1

        new_workspace = Workspace(
            workspace_id=new_workspace_id,
            workspace_name=workspace.workspace_name,
            workspace_prompt=workspace.workspace_prompt,
            workspace_comment=workspace.workspace_comment,
            created_by=workspace.user_id,
            workspace_join_code=new_workspace_join_code,
            school_id=workspace.school_id,
        )
        db.add(new_workspace)

        # Add an associated workplace role

        # Update the role of this user to a teacher for this workspace
        user: UserValue | None = (
            db.query(User).filter(User.user_id == workspace.user_id).first()
        )  # pyright: ignore[reportAssignmentType]
        if not user:
            return Responses[None].response(
                response,
                success=False,
                status=HTTPStatus.NOT_FOUND,
                message="User not found",
            )

        # Add an associated workplace role
        new_user_workspace = UserWorkspace(
            user_id=user.user_id,
            workspace_id=new_workspace_id,
            role="teacher",
            student_id=user.student_id
        )

        user.workspace_role[new_workspace_id] = "teacher"
        flag_modified(user, "workspace_role")
        db.add(new_user_workspace)
        logger.info(f"user_workspace role: {new_user_workspace}")
        logger.info(f"user: {user}")
        db.commit()

        return Responses[None].response(
            response,
            success=True,
            status=HTTPStatus.OK,
            message="Workspace created successfully",
        )
    except IntegrityError:
        db.rollback()
        return Responses[None].response(
            response,
            success=False,
            status=HTTPStatus.BAD_REQUEST,
            message="A problem occurred while creating this workspace, try recreating it",
        )
    except Exception as e:
        logger.error(f"Error creating workspace: {e}")
        db.rollback()
        return Responses[None].response(
            response,
            success=False,
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            message=str(e),
        )


@router.post("/set_workspace_status")
def set_workspace_status(
    request: Request,
    response: FastAPIResponse,
    update_workspace: WorkspaceUpdateStatus,
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
) -> Response[None]:
    """Sets the status of a workspace in the database to enabled, disabled, or deleted

    Args:
        request: FastAPI request object
        response: FastAPI response object
        update_workspace: WorkspaceUpdateStatus containing workspace details, new status
        db: SQLAlchemy database session
        background_tasks: FastAPI background tasks object for asynchronous tasks

    Returns:
        Success message or 404 if workspace not found

    """
    # Get JWT and user workspace role for authentication
    user_jwt_content = get_jwt(request.state)
    user_workspace_role = user_jwt_content["workspace_role"].get(
        update_workspace.workspace_id,
        None,
    )

    # Disallow non-admin users and users who are not teachers of the workspace
    # from setting the workspace's status
    if not user_jwt_content["system_admin"] and user_workspace_role != "teacher":
        return Responses[None].response(
            response,
            success=False,
            status=HTTPStatus.FORBIDDEN,
            message="You may not change the status of this workspace",
        )

    # If the user is authorized, update the workspace according to the given status
    try:
        # Attempt to find workspace. If it can't be found, return a 404 exception
        workspace: WorkspaceValue | None = (
            db.query(Workspace)
            .filter(Workspace.workspace_id == update_workspace.workspace_id)
            .first()
        )  # pyright: ignore[reportAssignmentType]

        if not workspace:
            return Responses[None].response(
                response,
                success=False,
                status=HTTPStatus.NOT_FOUND,
                message="Failed to find workspace",
            )

        # Update the workspace status in the database, report success to the user
        workspace.status = WorkspaceStatus(update_workspace.workspace_status)
        db.commit()

        # Sync user workspace cache
        if update_workspace.workspace_status == WorkspaceStatus.INACTIVE:
            background_tasks.add_task(remove_workspace_roles, db, update_workspace)
        else:
            background_tasks.add_task(restore_workspace_roles, db, update_workspace)

        return Responses[None].response(
            response,
            success=True,
            status=HTTPStatus.OK,
            message="Successfully updated workspace status",
        )

    # Report intermittent or external error
    except Exception as e:
        logger.error(f"Error changing workspace status: {e}")
        db.rollback()
        return Responses[None].response(
            response,
            success=False,
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            message=str(e),
        )


def remove_workspace_roles(
    db: Annotated[Session, Depends(get_db)], workspace: WorkspaceUpdateStatus
) -> None:
    """When a workspace is deactivated, remove workspace roles from users

    Args:
        db: SQLAlchemy database session
        workspace: WorkspaceUpdateStatus containing workspace details

    """
    try:
        # Get all users to change workspace values for
        users_to_modify: list[UserValue] = (
            db.query(User)
            .filter(
                func.json_extract_path_text(
                    User.workspace_role, workspace.workspace_id
                ).isnot(None)
            )
            .all()
        )  # pyright: ignore[reportAssignmentType]

        # Remove the workspace role from each associated user
        for user in users_to_modify:
            del user.workspace_role[workspace.workspace_id]
            flag_modified(user, "workspace_role")

        # Commit the changes
        db.commit()
        logger.info("Removed workspace roles from user entries")

    except Exception as e:
        logger.error(f"Error removing workspace roles: {e}")
        db.rollback()


# !TODO: Return status code


def restore_workspace_roles(
    db: Annotated[Session, Depends(get_db)],
    workspace: WorkspaceUpdateStatus,
) -> None:
    """When a workspace is reactivated, restore workspace roles to users

    Args:
        db: SQLAlchemy database session
        workspace: WorkspaceUpdateStatus containing workspace details

    """
    try:
        # Get the previous workspace roles from the "ai_user_workspace" table
        user_workspaces: list[UserWorkspace] = (
            db.query(UserWorkspace)
            .filter(UserWorkspace.workspace_id == workspace.workspace_id)
            .all()
        )

        # For each workspace id, add the associated role back to the associated user id
        for user_workspace in user_workspaces:
            user: UserValue | None = (
                db.query(User).filter(User.user_id == user_workspace.user_id).first()
            )  # pyright: ignore[reportAssignmentType] User could be None

            # If the user exists, then re-add the role
            if user:
                workspace_id_str = str(user_workspace.workspace_id)
                user.workspace_role[workspace_id_str] = user_workspace.role
                flag_modified(user, "workspace_role")
            else:
                logger.info(
                    "User does not exist in ai_users table, skipping this user..."
                )

        # Commit any changes to the database, log a successful operation
        db.commit()
        logger.info("Restored workspace roles for associated user entries")

    except Exception as e:
        logger.error(f"Error restoring workspace roles: {e}")
        db.rollback()


@router.post("/delete_workspace/{workspace}")
def delete_workspace(
    request: Request,
    response: FastAPIResponse,
    workspace: str,
    db: Annotated[Session, Depends(get_db)],
) -> Response[None]:
    """Delete a workspace from the database

    Args:
        request: FastAPI request object
        response: FastAPI response object
        workspace: str representing the workspace ID
        db: SQLAlchemy database session

    Returns:
        Success message or 400 if workspace not found

    """
    user_jwt_content = get_jwt(request.state)
    if not user_jwt_content["system_admin"]:
        return Responses[None].forbidden(response)
    try:
        query: WorkspaceValue = (
            db.query(Workspace).filter(Workspace.workspace_id == workspace).one()
        )  # pyright: ignore[reportAssignmentType]
        query.status = WorkspaceStatus.DELETED
        db.commit()
        return Responses[None].response(
            response,
            success=True,
            status=HTTPStatus.OK,
            message="Workspace deleted successfully",
        )
    except NoResultFound:
        db.rollback()
        return Responses[None].response(
            response,
            success=False,
            status=HTTPStatus.BAD_REQUEST,
            message="Workspace not found",
        )
    except MultipleResultsFound:
        db.rollback()
        return Responses[None].response(
            response,
            success=False,
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            message="Database is broken",
        )
    except Exception as e:
        logger.error(f"Error deleting workspace: {e}")
        db.rollback()
        return Responses[None].response(
            response,
            success=False,
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            message=str(e),
        )


@router.post("/add_users_via_csv")
def add_users_via_csv(
    request: Request,
    response: FastAPIResponse,
    workspace_id: str,
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile | None = None,
) -> Response[None]:
    """Add users to a workspace from a CSV file

    Args:
        request: FastAPI request object
        response: FastAPI response object
        workspace_id: str representing the workspace ID
        db: SQLAlchemy database session
        file: UploadFile representing the CSV file with Network ID column

    Returns:
        Success message or 400 if workspace not found or file is invalid

    """
    if file is None:
        return Responses[None].response(
            response, False, status=HTTPStatus.BAD_REQUEST, message="No File Provided"
        )
    user_jwt_content = get_jwt(request.state)
    user_workspace_role = user_jwt_content["workspace_role"].get(workspace_id, None)
    if user_workspace_role != "teacher" and not user_jwt_content["system_admin"]:
        return Responses[None].forbidden(response)
    try:
        # Read the file to detect encoding
        raw_content = file.file.read()
        result = chardet.detect(raw_content)
        encoding = result["encoding"] or ""

        # Decode the content using the detected encoding
        content = raw_content.decode(encoding)

        reader = csv.DictReader(io.StringIO(content))

        for row in reader:
            student_id = row["Network ID"]

            if not student_id:
                continue

            # Check if the record already exists
            existing_user_workspace = (
                db.query(UserWorkspace)
                .filter_by(workspace_id=workspace_id, student_id=student_id)
                .first()
            )

            if existing_user_workspace:
                continue  # Skip this row if it already exists

            user_workspace = UserWorkspace(
                student_id=student_id,
                workspace_id=workspace_id,
                role="pending",
            )
            db.add(user_workspace)

        db.commit()

        return Responses[None].response(
            response,
            success=True,
            status=HTTPStatus.OK,
            message="Users added via CSV successfully",
        )
    except Exception as e:
        logger.error(
            "Error adding users via CSV: Please make sure you"
            + " save the roster as a CSV file and try again",
        )
        db.rollback()
        return Responses[None].response(
            response, False, status=HTTPStatus.INTERNAL_SERVER_ERROR, message=str(e)
        )


@router.post("/add_users_json")
def add_users_json(
    request: Request,
    response: FastAPIResponse,
    workspace_id: str,
    students: StudentAddWorkspace,
    db: Annotated[Session, Depends(get_db)],
) -> Response[None]:
    """Add users to a workspace from a CSV file

    Args:
        request: FastAPI request object
        response: FastAPI response object
        workspace_id: str representing the workspace ID
        students: Students to add to the workspace
        db: SQLAlchemy database session

    Returns:
        Success message or 400 if workspace not found or file is invalid

    """
    user_jwt_content = get_jwt(request.state)
    user_workspace_role = user_jwt_content["workspace_role"].get(workspace_id, None)
    if user_workspace_role != "teacher" and not user_jwt_content["system_admin"]:
        return Responses[None].forbidden(response)
    try:
        for student in students.students:
            # Check if the record already exists
            existing_user_workspace = (
                db.query(UserWorkspace)
                .filter_by(workspace_id=workspace_id, student_id=student)
                .first()
            )

            if existing_user_workspace:
                continue  # Skip this row if it already exists

            user_workspace = UserWorkspace(
                student_id=student,
                workspace_id=workspace_id,
                role="pending",
            )
            db.add(user_workspace)

        db.commit()

        return Responses[None].response(
            response,
            success=True,
            status=HTTPStatus.OK,
            message="Users added via JSON successfully",
        )
    except Exception as e:
        logger.error(
            "Error adding users via JSON",
        )
        db.rollback()
        return Responses[None].response(
            response, False, status=HTTPStatus.INTERNAL_SERVER_ERROR, message=str(e)
        )


@router.post("/student_join_workspace")
def student_join_workspace(
    request: Request,
    response: FastAPIResponse,
    join_workspace: StudentJoinWorkspace,
    db: Annotated[Session, Depends(get_db)],
) -> Response[None]:
    """Joins a student to a workspace

    Args:
        request: FastAPI request object
        response: FastAPI response object
        join_workspace: StudentJoinWorkspace object containing workspace details
        db: SQLAlchemy database session

    Returns:
        Success message or 404 if user or workspace not found

    """
    user_jwt_content = get_jwt(request.state)
    user_id: int = user_jwt_content["user_id"]
    student_id: str = user_jwt_content["student_id"]
    try:
        user: UserValue | None = (
            db.query(User)
            .filter(User.user_id == user_id, User.student_id == student_id)
            .first()
        )  # pyright: ignore[reportAssignmentType]
        if not user:
            return Responses[None].response(
                response,
                success=False,
                status=HTTPStatus.NOT_FOUND,
                message="User not found",
            )

        workspace: WorkspaceValue = (
            db.query(Workspace)
            .filter(
                Workspace.workspace_id == join_workspace.workspace_id,
                Workspace.status == WorkspaceStatus.ACTIVE,
            )
            .first()
        )  # pyright: ignore[reportAssignmentType]

        if join_workspace.workspace_join_code != workspace.workspace_join_code:
            return Responses[None].response(
                response,
                success=False,
                status=HTTPStatus.BAD_REQUEST,
                message="Failed to join workspace",
            )

        user_workspace: UserWorkspaceValue | None = (
            db.query(UserWorkspace)
            .filter(
                UserWorkspace.student_id == student_id,
                UserWorkspace.workspace_id == join_workspace.workspace_id,
            )
            .first()
        )  # pyright: ignore[reportAssignmentType]

        if not user_workspace:
            return Responses[None].response(
                response,
                success=False,
                status=HTTPStatus.NOT_FOUND,
                message="Not authorized to join this workspace",
            )

        if user_workspace.role != "pending":
            return Responses[None].response(
                response,
                success=False,
                status=HTTPStatus.BAD_REQUEST,
                message="User already in this workspace",
            )

        user_workspace.role = "student"
        user_workspace.user_id = user_id
        user.workspace_role[join_workspace.workspace_id] = "student"
        flag_modified(user, "workspace_role")
        db.commit()

        return Responses[None].response(
            response,
            success=True,
            status=HTTPStatus.OK,
            message="User added to workspace successfully",
        )
    except Exception as e:
        logger.error(f"Error adding user to workspace: {e}")
        db.rollback()
        return Responses[None].response(
            response,
            success=False,
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            message=str(e),
        )


@router.post("/delete_user_from_workspace")
def delete_user_from_workspace(
    request: Request,
    response: FastAPIResponse,
    user_role_update: UserDelete,
    db: Annotated[Session, Depends(get_db)],
) -> Response[None]:
    """Deletes a user from a workspace

    Args:
        request: FastAPI request object
        response: FastAPI response object
        user_role_update: UserDelete object containing user details and workspace ID
        db: SQLAlchemy database session

    Returns:
        Success message or 404 if user or workspace not found

    """
    user_jwt_content = get_jwt(request.state)
    user_workspace_role = user_jwt_content["workspace_role"].get(
        user_role_update.workspace_id,
        None,
    )
    if user_workspace_role != "teacher" and not user_jwt_content["system_admin"]:
        return Responses[None].forbidden(response)
    try:
        user: UserValue | None = (
            db.query(User)
            .filter(
                User.user_id == user_role_update.user_id,
            )
            .first()
        )  # pyright: ignore[reportAssignmentType]
        if not user:
            return Responses[None].response(
                response,
                success=False,
                status=HTTPStatus.NOT_FOUND,
                message="User not found",
            )

        user_workspace: UserWorkspaceValue | None = (
            db.query(UserWorkspace)
            .filter(
                UserWorkspace.user_id == user.user_id,
                UserWorkspace.workspace_id == user_role_update.workspace_id,
            )
            .first()
        )  # pyright: ignore[reportAssignmentType]

        if not user_workspace:
            return Responses[None].response(
                response,
                success=False,
                status=HTTPStatus.NOT_FOUND,
                message="User not in this workspace",
            )

        db.delete(user_workspace)
        del user.workspace_role[user_role_update.workspace_id]
        flag_modified(user, "workspace_role")
        db.commit()

        return Responses[None].response(
            response,
            success=True,
            status=HTTPStatus.OK,
            message="User deleted from workspace successfully",
        )
    except Exception as e:
        logger.error(f"Error deleting user from workspace: {e}")
        db.rollback()
        return Responses[None].response(
            response,
            success=False,
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            message=str(e),
        )


@router.post("/set_user_role_with_user_id")
def set_user_role_with_user_id(
    request: Request,
    response: FastAPIResponse,
    user_role_update: UserRoleUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> Response[None]:
    """Set any user to any role in any workspace, even if not in that workspace

    Args:
        request: FastAPI request object
        response: FastAPI response object
        user_role_update: UserRoleUpdate containing user, workspace ID, and new role
        db: SQLAlchemy database session

    Returns:
        Success message or 404 if user or not found

    """
    user_jwt_content = get_jwt(request.state)
    if not user_jwt_content["system_admin"] and not user_jwt_content("workspace_admin"):
        return Responses[None].forbidden(response)
    try:
        user: UserValue | None = (
            db.query(User).filter(User.user_id == user_role_update.user_id).first()
        )  # pyright: ignore[reportAssignmentType]
        if not user:
            return Responses[None].response(
                response,
                success=False,
                status=HTTPStatus.NOT_FOUND,
                message="User not found",
            )

        user_workspace: UserWorkspaceValue | None = (
            db.query(UserWorkspace)
            .filter(
                UserWorkspace.user_id == user.user_id,
                UserWorkspace.workspace_id == user_role_update.workspace_id,
            )
            .first()
        )  # pyright: ignore[reportAssignmentType]

        logger.info("Reached here")
        logger.info(f"payload: {user_role_update}")

        if user_jwt_content["workspace_admin"] and not user_jwt_content["system_admin"]:
            # Ensure the user that the workspace admin is trying to promote is within this workspace
            calling_user: UserValue | None = (
                db.query(User).filter(User.user_id == user_role_update.calling_user_id).first()
            )  # pyright: ignore[reportAssignmentType]
            if not calling_user:
                return Responses[None].response(
                    response,
                    success=False,
                    status=HTTPStatus.NOT_FOUND,
                    message="User not found",
                )
            
            # If this value is null, then that means that the calling user is not within the
            # workspace of the specified user id
            calling_user_workspace: UserWorkspaceValue = (
                db.query(UserWorkspace)
                .filter(
                    UserWorkspace.user_id == calling_user.user_id,
                    UserWorkspace.workspace_id == user_role_update.workspace_id,
                )
                .first()
            )

            if not calling_user_workspace:
                return Responses[None].response(
                    response,
                    success=False,
                    status=HTTPStatus.FORBIDDEN,
                    message="User not found within this workspace"
                )

        if not user_workspace:
            # create a new user workspace record
            new_user_workspace = UserWorkspace(
                user_id=user.user_id,
                student_id=user.student_id,
                workspace_id=user_role_update.workspace_id,
                role=user_role_update.role,
            )
            db.add(new_user_workspace)
            db.commit()
        else:
            user_workspace.role = user_role_update.role

        user.workspace_role[user_role_update.workspace_id] = user_role_update.role
        flag_modified(user, "workspace_role")
        db.commit()

        return Responses[None].response(
            response,
            success=True,
            status=HTTPStatus.OK,
            message="User role updated successfully",
        )
    except Exception as e:
        logger.error(f"Error setting user role: {e}")
        db.rollback()
        return Responses[None].response(
            response,
            success=False,
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            message=str(e),
        )


@router.get("/get_workspace_list")
def get_workspace_list(
    request: Request,
    response: FastAPIResponse,
    db: Annotated[Session, Depends(get_db)],
    page: int = 1,
    page_size: int = 10,
) -> Response[APIListReturnPage[WorkspaceReturn]]:
    """Returns a list of workspaces with pagination

    Args:
        request: FastAPI request object
        response: FastAPI response object
        db: SQLAlchemy database session
        page: Page number (default: 1)
        page_size: Page size (default: 10)

    Returns:
        List of workspaces with pagination

    """
    user_jwt_content = get_jwt(request.state)
    if not user_jwt_content["system_admin"] and not user_jwt_content["workspace_admin"]:
        return Responses[WorkspaceReturn].forbidden_list_page(response)
    try:
        offset = (page - 1) * page_size
        workspaces: list[WorkspaceValue] = (
            db.query(Workspace)
            .filter(
                (Workspace.status != WorkspaceStatus.DELETED) if user_jwt_content["system_admin"]
                else (Workspace.status != WorkspaceStatus.DELETED and Workspace.created_by == int(user_jwt_content["user_id"]))
            )
            .order_by(desc(Workspace.status))
            .offset(offset)
            .limit(page_size)
            .all()
        )  # pyright: ignore[reportAssignmentType]
        total_workspaces = (
            db.query(Workspace)
            .filter(Workspace.status != WorkspaceStatus.DELETED)
            .count()
        )
        return Responses[APIListReturnPage[WorkspaceReturn]].response(
            response,
            success=True,
            status=HTTPStatus.OK,
            data={
                "items": [workspace_return(workspace) for workspace in workspaces],
                "total": total_workspaces,
                "page": page,
                "page_size": page_size,
            },
        )
    except Exception as e:
        logger.error(f"Error fetching workspace list: {e}")
        return Responses[APIListReturnPage[WorkspaceReturn]].response(
            response,
            success=False,
            data={"items": [], "total": 0, "page": 0, "page_size": 0},
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            message=str(e),
        )


@router.post("/set_workspace_admin_role")
def set_workspace_admin_role(
    request: Request,
    response: FastAPIResponse,
    workspace_admin_update: WorkspaceAdminRoleUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> Response[None]:
    """Modify the workspace admin role for a particular user

    Args:
        request: FastAPI request object
        response: FastAPI response object
        workspace_admin_update: WorkspaceAdminRoleUpdate containing user ID and the value for workspace_admin for that user
        db: SQLAlchemy database session

    Returns:
        Success message or 404 if user or not found

    """
    # Verify authority to perform this action
    logger.info("Entered endpoint")
    user_jwt_content = get_jwt(request.state)
    logger.info(f"system_admin status -> {user_jwt_content['system_admin']}")
    if not user_jwt_content["system_admin"]:
        return Responses[None].forbidden(response)

    try:
        # Get user to change workspace values for
        user: UserValue = (
            db.query(User)
            .filter(User.user_id == workspace_admin_update.user_id)
            .first()
        )  # pyright: ignore[reportAssignmentType]

        # Modify the workspace_admin role
        user.workspace_admin = workspace_admin_update.workspace_admin

        # Commit the changes
        db.commit()
        logger.info(
            f"Updated workspace admin role to {workspace_admin_update.workspace_admin}"
        )

        return Responses[None].response(
            response,
            success=True,
            status=HTTPStatus.OK,
            message="Successfully updated workplace admin role",
        )

    except Exception as e:
        logger.error(f"Error changing workspace admin status: {e}")
        db.rollback()
        return Responses[None].response(
            response,
            success=False,
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            message=str(e),
        )
