import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID

from utils.response import response
from common.MessageStorageHandler import MessageStorageHandler

from migrations.session import get_db

from sqlalchemy.orm import Session

from migrations.models import Thread, Agent


logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize the MessageStorageHandler
message_handler = MessageStorageHandler()


class ThreadListQuery(BaseModel):
    user_id: Optional[str] = None
    start_date: Optional[
        str] = None
    end_date: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)


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
            return response(False, status_code=404, message="Thread not found")

        # Sort the messages by 'created_at' time in descending order
        sorted_messages = sorted(thread_messages, key=lambda x: x.created_at,
                                 reverse=True)
        return response(True, data={"thread_id": thread_id,
                                    "messages": sorted_messages})
    except Exception as e:
        logger.error(f"Error fetching thread content: {e}")
        response(False, status_code=500, message=str(e))


@router.get("/get_thread_list")
def get_thread_list(
    creator: str,
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 10
):
    """
    List threads with pagination, filtered by agent creator.
    """
    query = (db.query(Thread.thread_id, Thread.user_id, Thread.created_at, Thread.agent_id).
             join(Agent, Agent.agent_id == Thread.agent_id).
             filter(Agent.creator == creator, Agent.status != 2))

    total = query.count()
    threads = (query.order_by(Thread.created_at.desc()).
               offset((page - 1) * page_size).
               limit(page_size).all())

    results = [{"thread_id": str(t.thread_id),
                "user_id": t.user_id,
                "created_at": str(t.created_at),
                "agent_id": str(t.agent_id)} for t in threads]
    return response(True, data={"threads": results, "total": total})