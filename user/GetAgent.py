# Copyright (c) 2024.
"""Gets an agent by its ID"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from migrations.models import Agent, AgentStatus, AgentValue
from migrations.session import get_db
from utils.response import Response, response

router = APIRouter()


# class AgentRequest(BaseModel):
#     agent_id: UUID
#     user_id: UUID | None = None
# I was thinking in the future we may want to track this??


@router.get("/get/{agent_id}")
def get_agent_by_id(
    agent_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> Response | JSONResponse:
    """Get the settings of an agent by its ID

    Args:
        agent_id: The ID of the agent
        db: The database session

    Returns:
        The settings of the agent

    """
    if not check_uuid_format(agent_id):
        return response(False, status_code=400, message="Invalid UUID format")

    agent: AgentValue | None = (
        db.query(Agent).filter(Agent.agent_id == agent_id).first()
    )  # pyright: ignore[reportAssignmentType]
    logging.info(f"User requested agent settings: {agent}")

    if agent is None:
        return response(False, status_code=404, message="Agent not found")
    if agent.status != AgentStatus.ACTIVE:
        return response(False, status_code=404, message="Agent is inactive")
    return response(
        True,
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
