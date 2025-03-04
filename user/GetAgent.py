# Copyright (c) 2024.
"""Gets an agent by its ID"""

import logging
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi import Response as FastAPIResponse
from sqlalchemy.orm import Session

from migrations.models import Agent, AgentReturn, AgentStatus, AgentValue
from migrations.session import get_db
from utils.response import Response, Responses

router = APIRouter()


# class AgentRequest(BaseModel):
#     agent_id: UUID
#     user_id: UUID | None = None
# I was thinking in the future we may want to track this??


@router.get("/get/{agent_id}")
def get_agent_by_id(
    response: FastAPIResponse,
    agent_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> Response[AgentReturn]:
    """Get the settings of an agent by its ID

    Args:
        response: The FastAPI response object
        agent_id: The ID of the agent
        db: The database session

    Returns:
        The settings of the agent

    """
    if not check_uuid_format(agent_id):
        return Responses[AgentReturn].response(
            response,
            False,
            data={
                "agent_name": "",
                "course_id": "",
                "voice": False,
                "model_choice": False,
                "model": "",
            },
            status=HTTPStatus.BAD_REQUEST,
            message="Invalid UUID format",
        )

    agent: AgentValue | None = (
        db.query(Agent).filter(Agent.agent_id == agent_id).first()
    )  # pyright: ignore[reportAssignmentType]
    logging.info(f"User requested agent settings: {agent}")

    if agent is None:
        return Responses[AgentReturn].response(
            response,
            success=False,
            data={
                "agent_name": "",
                "course_id": "",
                "voice": False,
                "model_choice": False,
                "model": "",
            },
            status=HTTPStatus.NOT_FOUND,
            message="Agent not found",
        )
    if agent.status != AgentStatus.ACTIVE:
        return Responses[AgentReturn].response(
            response,
            success=False,
            data={
                "agent_name": "",
                "course_id": "",
                "voice": False,
                "model_choice": False,
                "model": "",
            },
            status=HTTPStatus.NOT_FOUND,
            message="Agent is inactive",
        )
    return Responses[AgentReturn].response(
        response,
        success=True,
        status=HTTPStatus.OK,
        data={
            "agent_name": agent.agent_name,
            "course_id": agent.workspace_id,
            "voice": agent.voice,
            "model_choice": agent.allow_model_choice,
            "model": agent.model,
        },
    )


def check_uuid_format(agent_id: str) -> bool:
    """Checks if the UUID is in the correct format

    Args:
        agent_id: The UUID to check

    Returns:
        True if the UUID is in the correct format, False otherwise

    """
    try:
        _ = UUID(agent_id)
    except ValueError:
        return False
    return True
