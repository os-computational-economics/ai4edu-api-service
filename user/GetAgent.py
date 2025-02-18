# Copyright (c) 2024.
"""Gets an agent by its ID"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from starlette.responses import JSONResponse

from migrations.session import get_db
from utils.response import Response, response

router = APIRouter()


# class AgentRequest(BaseModel):
#     agent_id: UUID
#     user_id: UUID | None = None #I was thinking in the future we may want to track this??


@router.get("/get/{agent_id}")
def get_agent_by_id(
        agent_id: str, db: Annotated[Session, Depends(get_db)],
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
    conn = db.connection()
    # ! Fix this to not have an SQL injection vulnerability
    result = conn.execute(
        text("select * from ai_agents where agent_id = '" + str(agent_id) + "'"),
    )
    row = result.first()
    logging.info(f"User requested agent settings: {row}")

    if row is None:
        return response(False, status_code=404, message="Agent not found")
    if row[7] != 1:  # the row[7] -= 1 checks if the model is not active
        return response(False, status_code=404, message="Agent is inactive")
    return response(
        True,
        data={
            "agent_name": row[2],
            "course_id": row[3],
            "voice": row[6],
            "model_choice": row[8],
            "model": row[9],
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
