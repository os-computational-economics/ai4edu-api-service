# Copyright (c) 2024.
"""Create a new thread"""

import logging
import uuid
from http import HTTPStatus

from fastapi import Request
from fastapi import Response as FastAPIResponse

from common.JWTValidator import get_jwt
from migrations.models import Agent, ModelReturn, Thread
from migrations.session import get_db
from utils.response import Response, Responses

logger = logging.getLogger(__name__)


class NewThreadReturn(ModelReturn):
    """Thread return type"""

    thread_id: str


def new_thread_return(thread_id: str = "") -> NewThreadReturn:
    """Makes an NewThreadReturn object from a thread_id

    Args:
        thread_id: The thread ID to return

    Returns:
        A TypedDict of the return object

    """
    return {"thread_id": thread_id}


def new_thread(
    request: Request,
    response: FastAPIResponse,
    agent_id: str,
    workspace_id: str,
) -> Response[NewThreadReturn]:
    """Creates a newe thread with the given agent_id and workspace_id

    Args:
        request: Request: FastAPI request object
        response: FastAPI response object
        agent_id: Agent ID
        workspace_id: Workspace ID

    Returns:
        Response object if successful, None otherwise

    """
    user_jwt_content = get_jwt(request.state)

    for db in get_db():
        user_id = user_jwt_content["user_id"]
        student_id = user_jwt_content["student_id"]
        workspace_role = user_jwt_content["workspace_role"]
        is_user_in_workspace: bool = bool(workspace_role.get(workspace_id, False))
        if not is_user_in_workspace:
            logger.error(f"User {user_id} is not in workspace {workspace_id}")
            return Responses[NewThreadReturn].response(
                response,
                success=False,
                data=new_thread_return(),
                status=HTTPStatus.FORBIDDEN,
                message="User is not in workspace",
            )
        thread_id = str(uuid.uuid4())
        agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
        if not agent:
            logger.error(f"Agent not found: {agent_id}")
            return Responses[NewThreadReturn].response(
                response,
                success=False,
                status=HTTPStatus.NOT_FOUND,
                data=new_thread_return(),
                message="Agent not found",
            )
        thread = Thread(
            thread_id=thread_id,
            user_id=user_id,
            agent_id=agent_id,
            student_id=student_id,
            workspace_id=workspace_id,
            agent_name=agent.agent_name,
        )
        db.add(thread)

        try:
            db.commit()
            logger.info(f"New thread created: {thread_id}")
            return Responses[NewThreadReturn].response(
                response,
                success=True,
                status=HTTPStatus.OK,
                data=new_thread_return(thread_id),
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create new thread: {e!s}")
            return Responses[NewThreadReturn].response(
                response,
                success=False,
                data=new_thread_return(),
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
                message="Failed to create new thread",
            )

    return Responses[NewThreadReturn].response(
        response,
        success=False,
        data=new_thread_return(),
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
        message="An unknown error occurred",
    )
