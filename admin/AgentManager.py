# Copyright (c) 2024.
"""Classes and endpoints related to creating and managing AI agents"""

import logging
import uuid
from datetime import datetime
from http import HTTPStatus
from typing import Annotated
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Request
from fastapi import Response as FastAPIResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import cast, func, String

from common.AgentPromptHandler import AgentPromptHandler
from common.EmbeddingHandler import embed_file
from common.EnvManager import getenv
from common.FileStorageHandler import FileStorageHandler
from common.JWTValidator import get_jwt
from migrations.models import (
    Agent,
    AgentStatus,
    AgentDashboardReturn,
    AgentValue,
    ModelReturn,
    Workspace,
    WorkspaceStatus,
    agent_dashboard_return,
)
from migrations.session import get_db
from utils.response import APIListReturn, Response, Responses

logger = logging.getLogger(__name__)
CONFIG = getenv()

router = APIRouter()
agent_prompt_handler = AgentPromptHandler(config=CONFIG)


class AgentCreate(BaseModel):
    """An object sent in order to create a new agent on the create_agent endpoint."""

    agent_name: str
    workspace_id: str
    creator: str | None = None
    voice: bool = Field(default=False)  # pyright: ignore[reportAny]
    status: int = Field(
        default=1, description="1-active, 0-inactive, 2-deleted"
    )  # pyright: ignore[reportAny]
    allow_model_choice: bool = Field(default=True)  # pyright: ignore[reportAny]
    model: str | None = None
    system_prompt: str
    agent_files: dict[str, str] | None = {}


class AgentDelete(BaseModel):
    """An object sent in order to delete an agent on the delete_agent endpoint."""

    agent_id: UUID
    workspace_id: str | None = None


class AgentUpdate(BaseModel):
    """An object sent in order to update an agent on the edit_agent endpoint."""

    agent_id: UUID
    workspace_id: str | None = None
    agent_name: str | None = None
    creator: str | None = None
    voice: bool | None = None
    status: AgentStatus | None = None
    allow_model_choice: bool | None = None
    model: str | None = None
    system_prompt: str | None = None
    agent_files: dict[str, str] | None = {}


class AgentResponse(BaseModel):
    """A Class describing a response returning an agent back to the user (unused)."""

    agent_id: UUID
    agent_name: str
    workspace_id: str
    creator: str | None = None
    voice: bool
    status: int
    allow_model_choice: bool
    model: str | None = None
    created_at: datetime
    updated_at: datetime
    system_prompt: str


class AddAgentResponse(ModelReturn):
    """A dictionary representing the response to add an agent."""

    agent_id: str


def add_agent_response(agent_id: str = "") -> AddAgentResponse:
    """Makes an AddAgentResponse object from an agent_id

    Args:
        agent_id: The agent id to return

    Returns:
        A TypedDict of the return object

    """
    return {"agent_id": agent_id}


@router.post("/add_agent")
def create_agent(
    request: Request,
    response: FastAPIResponse,
    agent_data: AgentCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Response[AddAgentResponse]:
    """Create a new agent record in the database.

    Args:
        request: FastAPI request object
        response: FastAPI response object
        agent_data: AgentCreate object containing new agent
        db: SQLAlchemy database session

    Returns:
        ID if successful, Error if not

    """
    user_jwt_content = get_jwt(request.state)

    if (
        user_jwt_content["workspace_role"].get(agent_data.workspace_id, None)
        != "teacher"
        and not user_jwt_content["system_admin"]
    ):
        return Responses[AddAgentResponse].forbidden(
            response, data=add_agent_response()
        )
    new_agent_id = uuid4()
    new_agent = Agent(
        agent_id=new_agent_id,
        created_at=datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"])),
        agent_name=agent_data.agent_name,
        workspace_id=agent_data.workspace_id,
        creator=agent_data.creator,
        updated_at=datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"])),
        voice=agent_data.voice,
        status=agent_data.status,
        allow_model_choice=agent_data.allow_model_choice,
        model=agent_data.model,
        agent_files=agent_data.agent_files,
    )
    db.add(new_agent)
    _ = agent_prompt_handler.put_agent_prompt(
        str(new_agent.agent_id),
        agent_data.system_prompt,
    )

    # if there is agent files, embed the files with pinecone
    if agent_data.agent_files:
        fsh = FileStorageHandler(config=CONFIG)
        for file_id, file_name in agent_data.agent_files.items():
            file_path = fsh.get_file(uuid.UUID(hex=file_id))
            if file_path:
                _ = embed_file(
                    "namespace-test",
                    f"{agent_data.workspace_id}-{new_agent_id}",
                    str(file_path),
                    file_id,
                    file_name,
                    "pdf",
                    str(new_agent_id),
                    agent_data.workspace_id,
                )
            else:
                logger.error(f"Failed to embed file: {file_id}")

    try:
        db.commit()
        db.refresh(new_agent)
        logger.info(
            f"Inserted new agent: {new_agent.agent_id} - {new_agent.agent_name}",
        )
        return Responses[AddAgentResponse].response(
            response,
            success=True,
            status=HTTPStatus.OK,
            data=add_agent_response(str(new_agent.agent_id)),
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to insert new agent: {e}")
        return Responses[AddAgentResponse].response(
            response,
            success=False,
            data=add_agent_response(),
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            message=str(e),
        )


@router.post("/delete_agent")
def delete_agent(
    request: Request,
    response: FastAPIResponse,
    delete_data: AgentDelete,
    db: Annotated[Session, Depends(get_db)],
) -> Response[AddAgentResponse]:
    """Delete an existing agent record in the database by marking it as status=2.

    Will not actually delete the record or prompt from the database.

    Args:
        request: FastAPI request object
        response: FastAPI response object
        delete_data: AgentDelete object containing agent_id and workspace_id
        db: SQLAlchemy database session

    Returns:
        ID if successful, Error if not

    """
    agent_workspace: AgentValue = (
        db.query(Agent).filter(Agent.agent_id == delete_data.agent_id).first()
    )  # pyright: ignore[reportAssignmentType]

    ws_id = delete_data.workspace_id or agent_workspace.workspace_id

    user_jwt_content = get_jwt(request.state)
    if (
        user_jwt_content["workspace_role"].get(ws_id, None) != "teacher"
        and not user_jwt_content["system_admin"]
    ):
        return Responses[AddAgentResponse].forbidden(
            response, data=add_agent_response()
        )
    agent_to_delete: AgentValue | None = (
        db.query(Agent).filter(Agent.agent_id == delete_data.agent_id).first()
    )  # pyright: ignore[reportAssignmentType]
    if not agent_to_delete:
        logger.error(f"Agent not found: {delete_data.agent_id}")
        return Responses[AddAgentResponse].response(
            response,
            success=False,
            data=add_agent_response(),
            status=HTTPStatus.NOT_FOUND,
            message="Agent not found",
        )
    try:
        # mark the agent as deleted by setting the status to 2
        agent_to_delete.status = AgentStatus.DELETED
        db.commit()
        logger.info(f"Deleted agent: {delete_data.agent_id}")
        return Responses[AddAgentResponse].response(
            response,
            success=True,
            status=HTTPStatus.OK,
            data=add_agent_response(str(delete_data.agent_id)),
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete agent: {e}")
        return Responses[AddAgentResponse].response(
            response,
            success=False,
            data=add_agent_response(),
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            message=str(e),
        )


@router.post("/update_agent")
def edit_agent(
    request: Request,
    response: FastAPIResponse,
    update_data: AgentUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> Response[AddAgentResponse]:
    """Update an existing agent record in the database.

    Args:
        request: FastAPI request object
        response: FastAPI response object
        update_data: AgentUpdate object with agent id, workspace id, updated fields
        db: SQLAlchemy database session

    Returns:
        ID if successful, Error if not

    """
    user_jwt_content = get_jwt(request.state)
    if (
        user_jwt_content["workspace_role"].get(update_data.workspace_id or "All", None)
        != "teacher"
        and not user_jwt_content["system_admin"]
    ):
        return Responses[AddAgentResponse].forbidden(
            response, data=add_agent_response()
        )
    agent_to_update: AgentValue | None = (
        db.query(Agent).filter(Agent.agent_id == update_data.agent_id).first()
    )  # pyright: ignore[reportAssignmentType]
    if not agent_to_update:
        logger.error(f"Agent not found: {update_data.agent_id}")
        return Responses[AddAgentResponse].response(
            response,
            success=False,
            data=add_agent_response(),
            status=HTTPStatus.NOT_FOUND,
            message="Agent not found",
        )

    # Update the agent fields if provided
    # ! TODO: Fix this block of if statements

    if update_data.agent_name is not None:
        agent_to_update.agent_name = update_data.agent_name
    if update_data.workspace_id is not None:
        agent_to_update.workspace_id = update_data.workspace_id
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
    if update_data.agent_files is not None:
        agent_to_update.agent_files = update_data.agent_files
        # embed the files with pinecone
        fsh = FileStorageHandler(config=CONFIG)
        for file_id, file_name in update_data.agent_files.items():
            file_path = fsh.get_file(uuid.UUID(file_id))
            if file_path:
                _ = embed_file(
                    "namespace-test",
                    f"{update_data.workspace_id}-{update_data.agent_id}",
                    str(file_path),
                    file_id,
                    file_name,
                    "pdf",
                    str(update_data.agent_id),
                    update_data.workspace_id or agent_to_update.workspace_id,
                )
            else:
                logger.error(f"Failed to embed file: {file_id}")
    agent_to_update.updated_at = datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"]))

    if update_data.system_prompt is not None:
        _ = agent_prompt_handler.put_agent_prompt(
            str(agent_to_update.agent_id),
            update_data.system_prompt,
        )

    try:
        db.commit()
        db.refresh(agent_to_update)
        logger.info(f"Updated agent: {agent_to_update.agent_id}")
        return Responses[AddAgentResponse].response(
            response,
            success=True,
            status=HTTPStatus.OK,
            data=add_agent_response(str(agent_to_update.agent_id)),
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update agent: {e}")
        return Responses[AddAgentResponse].response(
            response,
            success=False,
            data=add_agent_response(),
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            message=str(e),
        )


@router.get("/agents")
def list_agents(
    request: Request,
    response: FastAPIResponse,
    workspace_id: str,
    db: Annotated[Session, Depends(get_db)],
    page: int = 1,
    page_size: int = 10,
) -> Response[APIListReturn[AgentDashboardReturn]]:
    """List agents with pagination.

    Args:
        request: FastAPI request object
        response: FastAPI response object
        workspace_id: Workspace ID to filter agents by
        db: SQLAlchemy database session
        page: Page number for pagination
        page_size: Number of agents per page

    Returns:
        List of agents and total count

    """
    user_jwt_content = get_jwt(request.state)
    user_role = user_jwt_content["workspace_role"].get(workspace_id, None)
    if user_role is None:
        return Responses[AgentDashboardReturn].forbidden_list(response)
    query = (
        db.query(
            cast(Agent.agent_id, String).label("agent_id"),  # Cast UUID to string
            Agent.agent_name,
            Agent.workspace_id,
            Agent.voice,
            Agent.status,
            Agent.allow_model_choice,
            Agent.model,
            Agent.created_at,
            Agent.updated_at,
            cast(func.coalesce(Agent.creator, ""), String).label(
                "creator"
            ),  # Handle NULL values
            Agent.agent_files,
        )
        .join(
            Workspace,
            Agent.workspace_id == Workspace.workspace_id,
        )
        .filter(
            Agent.workspace_id == workspace_id,
            Agent.status != AgentStatus.DELETED,
            Workspace.status != WorkspaceStatus.DELETED,
        )
    )  # exclude deleted agents
    total = query.count()
    query = query.order_by(Agent.updated_at.desc())
    skip = (page - 1) * page_size

    # Get raw results as rows
    raw_agents = query.offset(skip).limit(page_size).all()

    # Convert SQLAlchemy result rows to dictionaries
    agents: list[AgentValue] = []
    for row in raw_agents:
        agent_dict = {
            "agent_id": row.agent_id,
            "agent_name": row.agent_name,
            "workspace_id": row.workspace_id,
            "voice": row.voice,
            "status": row.status,
            "allow_model_choice": row.allow_model_choice,
            "model": row.model,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "creator": row.creator,
            "agent_files": row.agent_files or {},
            "system_prompt": "",  # Will be filled later if needed
        }
        av: AgentValue = AgentValue()
        for key, value in agent_dict.items():
            setattr(av, key, value)
        agents.append(av)

    user_is_teacher = user_role == "teacher"

    # get the prompt for each agent
    if user_is_teacher:
        for agent in agents:
            system_prompt = (
                agent_prompt_handler.get_agent_prompt(str(agent.agent_id)) or ""
            )
            agent.system_prompt = system_prompt

    return Responses[APIListReturn[AgentDashboardReturn]].response(
        response,
        success=True,
        status=HTTPStatus.OK,
        data={
            "items": [agent_dashboard_return(agent, is_teacher=user_is_teacher) for agent in agents],
            "total": total,
        },
    )


@router.get("/agent/{agent_id}")
def get_agent_by_id(
    request: Request,
    response: FastAPIResponse,
    agent_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Response[AgentDashboardReturn]:
    """Fetch an agent by its UUID.

    Args:
        request: FastAPI request object
        response: FastAPI response object
        agent_id: Agent UUID to fetch
        db: SQLAlchemy database session

    Returns:
        Agent data if found, Error if not

    """
    agent: AgentValue | None = (
        db.query(Agent)
        .filter(Agent.agent_id == agent_id, Agent.status != AgentStatus.DELETED)
        .first()
    )  # pyright: ignore[reportAssignmentType] exclude deleted agents
    if agent is None:
        return Responses[AgentDashboardReturn].response(
            response,
            success=False,
            data=agent_dashboard_return(),
            status=HTTPStatus.NOT_FOUND,
            message="Agent not found",
        )
    agent_workspace = agent.workspace_id
    user_jwt_content = get_jwt(request.state)
    user_role = user_jwt_content["workspace_role"].get(agent_workspace, None)
    if user_role is None:
        return Responses[AgentDashboardReturn].forbidden(
            response, data=agent_dashboard_return()
        )
    # if user_role != "teacher":
    #     agent.agent_files = {}
    # TODO: not sure if returning data is correct here
    return Responses[AgentDashboardReturn].response(
        response, success=True, status=HTTPStatus.OK, data=agent_dashboard_return(agent)
    )
