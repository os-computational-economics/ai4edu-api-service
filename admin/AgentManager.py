import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime

from migrations.session import get_db
from migrations.models import Agent

logger = logging.getLogger(__name__)

router = APIRouter()

class AgentCreate(BaseModel):
    agent_name: str
    course_id: Optional[str] = None
    creator: Optional[str] = None
    voice: bool = Field(default=False)
    status: int = Field(default=1, description='1-active, 0-inactive, 2-deleted')
    allow_model_choice: bool = Field(default=True)
    model: Optional[str] = None

class AgentDelete(BaseModel):
    agent_id: UUID

class AgentUpdate(BaseModel):
    agent_id: UUID
    agent_name: Optional[str] = None
    course_id: Optional[str] = None
    creator: Optional[str] = None
    voice: Optional[bool] = None
    status: Optional[int] = None
    allow_model_choice: Optional[bool] = None
    model: Optional[str] = None


@router.post("/add_agent", response_model=AgentCreate)
def create_agent(
    agent_data: AgentCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new agent record in the database.
    """
    new_agent = Agent(
        agent_id=uuid4(),
        created_at=datetime.now(),
        agent_name=agent_data.agent_name,
        course_id=agent_data.course_id,
        creator=agent_data.creator,
        updated_at=datetime.now(),
        voice=agent_data.voice,
        status=agent_data.status,
        allow_model_choice=agent_data.allow_model_choice,
        model=agent_data.model
    )
    db.add(new_agent)

    try:
        db.commit()
        db.refresh(new_agent)
        logger.info(f"Inserted new agent: {new_agent.agent_id} - {new_agent.agent_name}")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to insert new agent: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    return new_agent

@router.post("/delete_agent", response_model=AgentDelete)
def delete_agent(
    delete_data: AgentDelete,
    db: Session = Depends(get_db)
):
    """
    Delete an existing agent record in the database.
    """
    agent_to_delete = db.query(Agent).filter(Agent.agent_id == delete_data.agent_id).first()
    if not agent_to_delete:
        logger.error(f"Agent not found: {delete_data.agent_id}")
        raise HTTPException(status_code=404, detail="Agent not found")

    try:
        db.delete(agent_to_delete)
        db.commit()
        logger.info(f"Deleted agent: {delete_data.agent_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete agent: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    return {"agent_id": delete_data.agent_id}

@router.post("/edit_agent", response_model=AgentUpdate)
def edit_agent(
    update_data: AgentUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing agent record in the database.
    """
    agent_to_update = db.query(Agent).filter(Agent.agent_id == update_data.agent_id).first()
    if not agent_to_update:
        logger.error(f"Agent not found: {update_data.agent_id}")
        raise HTTPException(status_code=404, detail="Agent not found")

    # Update the agent fields if provided
    if update_data.agent_name is not None:
        agent_to_update.agent_name = update_data.agent_name
    if update_data.course_id is not None:
        agent_to_update.course_id = update_data.course_id
    if update_data.creator is not None:
        agent_to_update.creator = update_data.creator
    if update_data.voice is not None:
        agent_to_update.voice = update_data.voice
    if update_data.status is not None:
        agent_to_update.status = update_data.status
    if update_data.allow_model_choice is not None:
        agent_to_update.allow_model_choice = update_data.allow_model_choice
    if update_data.model is not None:
        agent_to_update.model = update_data.model

    try:
        db.commit()
        db.refresh(agent_to_update)
        logger.info(f"Updated agent: {agent_to_update.agent_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update agent: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    return agent_to_update
