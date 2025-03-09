# Copyright (c) 2024.
"""Classes and endpoints related to creating and managing threads/conversations"""

import logging
from datetime import datetime
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi import Response as FastAPIResponse
from pydantic import BaseModel, Field
from sqlalchemy import String, cast
from sqlalchemy.orm import Session

from common.EnvManager import getenv
from common.JWTValidator import get_jwt
from common.MessageStorageHandler import Message, MessageStorageHandler
from migrations.models import (
    Agent,
    ModelReturn,
    Thread,
    ThreadReturn,
    ThreadValue,
    Workspace,
    WorkspaceStatus,
    thread_return,
)
from migrations.session import get_db
from utils.response import APIListReturn, Response, Responses

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
    page: int = Field(default=1, ge=1)  # pyright: ignore[reportAny]
    page_size: int = Field(default=10, ge=1, le=100)  # pyright: ignore[reportAny]
    agent_name: str | None = None
    course_id: str | None = None


class ThreadContent(BaseModel):
    """Unused."""

    thread_id: str
    user_id: str
    created_at: str
    agent_id: str


class ListAgentsResponse(ModelReturn):
    """Return type for Getting Full Thread"""

    thread_id: str
    messages: list[Message]


def list_agents_response(
    thread_id: str = "", messages: list[Message] | None = None
) -> ListAgentsResponse:
    """Makes an ListAgentsResponse object from a python object

    Args:
        thread_id: The thread id to return
        messages: The list of messages to return

    Returns:
        A TypedDict of the return object

    """
    if messages is None:
        messages = []
    return {"messages": messages, "thread_id": thread_id}


@router.get("/get_thread/{thread_id}")
def get_thread_by_id(
    response: FastAPIResponse,
    thread_id: UUID,
) -> Response[ListAgentsResponse]:
    """Fetch all entries for a specific thread by its UUID, sorted by creation time.

    Args:
        response: FastAPI response object
        thread_id: UUID of the thread

    Returns:
        ID and messages if found, 500 if not

    """
    try:
        thread_messages: list[Message] = message_handler.get_thread(str(thread_id))
        if not thread_messages:
            return Responses[ListAgentsResponse].response(
                response,
                success=False,
                data=list_agents_response(),
                status=HTTPStatus.NOT_FOUND,
                message="Thread messages not found",
            )

        # Sort the messages by 'created_at' time in descending order
        sorted_messages: list[Message] = sorted(
            thread_messages, key=lambda x: x.created_at
        )
        return Responses[ListAgentsResponse].response(
            response,
            success=True,
            status=HTTPStatus.OK,
            data=list_agents_response(str(thread_id), sorted_messages),
        )
    except Exception as e:
        logger.error(f"Error fetching thread content: {e}")
        return Responses[ListAgentsResponse].response(
            response,
            success=False,
            data=list_agents_response(),
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            message=str(e),
        )


@router.get("/get_thread_list")
def get_thread_list(  # noqa: PLR0913, PLR0917
    workspace_id: str,
    request: Request,
    response: FastAPIResponse,
    db: Annotated[Session, Depends(get_db)],
    page: int = 1,
    page_size: int = 10,
    user_id: int | None = None,
    agent_name: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Response[APIListReturn[ThreadReturn]]:
    """List threads with pagination, filtered by agent creator.

    Args:
        workspace_id: ID of the workspace
        request: FastAPI request object
        response: FastAPI response object
        db: SQLAlchemy database session
        page: Page number for pagination
        page_size: Number of threads per page
        user_id: Filter threads by student ID (if provided)
        agent_name: Filter threads by agent name (if provided)
        start_date: Filter threads by start date (if provided)
        end_date: Filter threads by end date (if provided)

    Returns:
        List of threads and total information if found, 403 if not auth

    """
    user_jwt_content = get_jwt(request.state)
    user_workspace_role = user_jwt_content["workspace_role"].get(workspace_id, None)
    if user_workspace_role != "teacher" and user_jwt_content["user_id"] != user_id:
        return Responses[ThreadReturn].forbidden_list(response)
    query = (
        db.query(
            cast(Thread.thread_id, String).label("thread_id"),  # Cast UUID to string
            Thread.user_id,
            Thread.created_at,
            cast(Thread.agent_id, String).label("agent_id"),  # Cast UUID to string
            Thread.agent_name,
            Thread.workspace_id,
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

    # casting UUID to string for thread_id and agent_id, because
    # the response is a string

    if agent_name:
        query = query.filter(Agent.agent_name.ilike(f"%{agent_name}%"))
    if user_id and user_id != -1:
        # -1 indicates all records should be shown
        query = query.filter(Thread.user_id == user_id)
    if start_date:
        try:
            start_datetime = datetime.fromisoformat(start_date)
            # ! May cause issue with timezones
            query = query.filter(Thread.created_at >= start_datetime)
        except ValueError:
            return Responses[APIListReturn[ThreadReturn]].response(
                response,
                success=False,
                data={"items": [], "total": 0},
                status=HTTPStatus.BAD_REQUEST,
                message="Invalid start_date format. Use YYYY-MM-DD[THH:MM:SS]",
            )
    if end_date:
        try:
            end_datetime = datetime.fromisoformat(end_date)
            # ! May cause issue with timezones
            query = query.filter(Thread.created_at <= end_datetime)
        except ValueError:
            return Responses[APIListReturn[ThreadReturn]].response(
                response,
                success=False,
                data={"items": [], "total": 0},
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
    return Responses[APIListReturn[ThreadReturn]].response(
        response,
        success=True,
        status=HTTPStatus.OK,
        data={"items": [thread_return(t) for t in threads], "total": total},
    )
