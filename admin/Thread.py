# Copyright (c) 2024.
"""Classes and endpoints related to creating and managing threads/conversations"""

import logging
from datetime import datetime
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from common.EnvManager import getenv
from common.JWTValidator import get_jwt
from common.MessageStorageHandler import MessageStorageHandler
from migrations.models import Agent, Thread, ThreadValue, Workspace, WorkspaceStatus
from migrations.session import get_db
from utils.response import forbidden, response

logger = logging.getLogger(__name__)
router = APIRouter()
CONFIG = getenv()

# Initialize the MessageStorageHandler
message_handler = MessageStorageHandler(config=CONFIG)


class ThreadListQuery(BaseModel):
    """Unused."""

    user_id: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    agent_name: str | None = None
    course_id: str | None = None


class ThreadContent(BaseModel):
    """Unused."""

    thread_id: str
    user_id: str
    created_at: str
    agent_id: str


@router.get("/get_thread/{thread_id}")
def get_thread_by_id(thread_id: UUID) -> JSONResponse:
    """Fetch all entries for a specific thread by its UUID, sorted by creation time.

    Args:
        thread_id: UUID of the thread

    Returns:
        ID and messages if found, 500 if not

    """
    try:
        thread_messages = message_handler.get_thread(str(thread_id))
        if not thread_messages:
            return response(
                False, status=HTTPStatus.NOT_FOUND, message="Thread messages not found"
            )

        # Sort the messages by 'created_at' time in descending order
        sorted_messages = sorted(thread_messages, key=lambda x: x.created_at)
        return response(
            True,
            status=HTTPStatus.OK,
            data={"thread_id": thread_id, "messages": sorted_messages},
        )
    except Exception as e:
        logger.error(f"Error fetching thread content: {e}")
        return response(False, status=HTTPStatus.INTERNAL_SERVER_ERROR, message=str(e))


@router.get("/get_thread_list")
def get_thread_list(
    workspace_id: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    page: int = 1,
    page_size: int = 10,
    student_id: str | None = None,
    agent_name: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> JSONResponse:
    """List threads with pagination, filtered by agent creator.

    Args:
        workspace_id: ID of the workspace
        request: FastAPI request object
        db: SQLAlchemy database session
        page: Page number for pagination
        page_size: Number of threads per page
        student_id: Filter threads by student ID (if provided)
        agent_name: Filter threads by agent name (if provided)
        start_date: Filter threads by start date (if provided)
        end_date: Filter threads by end date (if provided)

    Returns:
        List of threads and total information if found, 403 if not auth

    """
    user_jwt_content = get_jwt(request.state)
    user_workspace_role = user_jwt_content["workspace_role"].get(workspace_id, None)
    if (
        user_workspace_role != "teacher"
        and user_jwt_content["student_id"] != student_id
    ):
        return forbidden()
    query = (
        db.query(
            Thread.thread_id,
            Thread.user_id,
            Thread.created_at,
            Thread.agent_id,
            Thread.agent_name,
            Thread.workspace_id,
            Thread.student_id,
        )
        .join(
            Workspace,
            Thread.workspace_id == Workspace.workspace_id,
        )
        .filter(
            Workspace.status != WorkspaceStatus.DELETED,
            Thread.workspace_id == workspace_id,
        )
    )  # even the agent is deleted, the thread still exists

    if agent_name:
        query = query.filter(Agent.agent_name.ilike(f"%{agent_name}%"))
    if student_id and student_id != "all":
        query = query.filter(Thread.student_id == student_id)
    if start_date:
        try:
            start_datetime = datetime.fromisoformat(start_date)
            # ! May cause issue with timezones
            query = query.filter(Thread.created_at >= start_datetime)
        except ValueError:
            return response(
                False,
                status=HTTPStatus.BAD_REQUEST,
                message="Invalid start_date format. Use YYYY-MM-DD[THH:MM:SS]",
            )
    if end_date:
        try:
            end_datetime = datetime.fromisoformat(end_date)
            # ! May cause issue with timezones
            query = query.filter(Thread.created_at <= end_datetime)
        except ValueError:
            return response(
                False,
                status=HTTPStatus.BAD_REQUEST,
                message="Invalid end_date format. Use YYYY-MM-DD[THH:MM:SS]",
            )

    total = query.count()
    threads: list[ThreadValue] = (
        query.order_by(Thread.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )  # pyright: ignore[reportAssignmentType]
    results = [
        {
            "thread_id": str(t.thread_id),
            "user_id": t.user_id,
            "student_id": t.student_id,
            "created_at": str(t.created_at),
            "agent_id": str(t.agent_id),
            "agent_name": str(t.agent_name),
            "workspace_id": workspace_id,
        }
        for t in threads
    ]
    return response(
        True, status=HTTPStatus.OK, data={"threads": results, "total": total}
    )
