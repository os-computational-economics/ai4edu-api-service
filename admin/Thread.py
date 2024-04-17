import logging
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

from utils.response import response
from common.MessageStorageHandler import MessageStorageHandler

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize the MessageStorageHandler
message_handler = MessageStorageHandler()


class ThreadListQuery(BaseModel):
    user_id: Optional[str] = None
    start_date: Optional[
        str] = None  # Dates should be strings in ISO 8601 format
    end_date: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)


class ThreadContent(BaseModel):
    thread_id: str
    user_id: str
    created_at: str
    agent_id: str


@router.get("/get_thread_list")
def get_thread_list(query_params: ThreadListQuery):
    """
    List threads with optional filters: user_id, start_date, and end_date.
    """
    try:
        res = message_handler.get_thread(
            query_params.thread_id)
        if not res:
            response(False, status_code=404,
                     message="No threads found for given parameters.")
        sorted_response = sorted(res, key=lambda x: x.created_at,
                                 reverse=True)
        return response(True, data={"threads": sorted_response})
    except Exception as e:
        logger.error(f"Error fetching thread list: {e}")
        response(False, status_code=500, message=str(e))


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
