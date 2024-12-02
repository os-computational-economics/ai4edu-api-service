import logging
from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from uuid import UUID

from common.JWTValidator import getJWT
from utils.response import response
from common.MessageStorageHandler import MessageStorageHandler

from migrations.session import get_db

from sqlalchemy.orm import Session

from migrations.models import Thread, Agent, ThreadValue, Workspace

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize the MessageStorageHandler
message_handler = MessageStorageHandler()


class ThreadListQuery(BaseModel):
    user_id: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    agent_name: str | None = None
    course_id: str | None = None


class ThreadContent(BaseModel):
    thread_id: str
    user_id: str
    created_at: str
    agent_id: str


@router.get("/get_thread/{thread_id}")
def get_thread_by_id(thread_id: UUID):
    """
    Fetch all entries for a specific thread by its UUID, sorted by creation time.
    """
    try:
        thread_messages = message_handler.get_thread(str(thread_id))
        if not thread_messages:
            return response(False, status_code=404, message="Thread messages not found")

        # Sort the messages by 'created_at' time in descending order
        sorted_messages = sorted(thread_messages, key=lambda x: x.created_at)
        return response(
            True, data={"thread_id": thread_id, "messages": sorted_messages}
        )
    except Exception as e:
        logger.error(f"Error fetching thread content: {e}")
        return response(False, status_code=500, message=str(e))


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
):
    """
    List threads with pagination, filtered by agent creator.
    """
    user_jwt_content = getJWT(request.state)
    user_workspace_role = user_jwt_content["workspace_role"].get(workspace_id, None)
    if (
        user_workspace_role != "teacher"
        and user_jwt_content["student_id"] != student_id
    ):
        return response(
            False, status_code=403, message="You do not have access to this resource"
        )
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
        .filter(Workspace.status != 2, Thread.workspace_id == workspace_id)
    )  # even the agent is deleted, the thread still exists

    if agent_name:
        query = query.filter(Agent.agent_name.ilike(f"%{agent_name}%"))
    if student_id:
        if student_id != "all":
            query = query.filter(Thread.student_id == student_id)
    if start_date:
        try:
            start_datetime = datetime.fromisoformat(start_date)
            query = query.filter(Thread.created_at >= start_datetime)
        except ValueError:
            return response(
                False,
                status_code=400,
                message="Invalid start_date format. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS",
            )
    if end_date:
        try:
            end_datetime = datetime.fromisoformat(end_date)
            query = query.filter(Thread.created_at <= end_datetime)
        except ValueError:
            return response(
                False,
                status_code=400,
                message="Invalid end_date format. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS",
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
    return response(True, data={"threads": results, "total": total})
