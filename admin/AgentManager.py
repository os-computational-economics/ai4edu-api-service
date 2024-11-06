import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime

from common.JWTValidator import getJWT
from migrations.session import get_db
from migrations.models import Agent, AgentTeacherResponse, AgentValue, Workspace

from utils.response import response
from common.AgentPromptHandler import AgentPromptHandler
from common.EmbeddingHandler import embed_file
from common.FileStorageHandler import FileStorageHandler

logger = logging.getLogger(__name__)

router = APIRouter()
agent_prompt_handler = AgentPromptHandler()


class AgentCreate(BaseModel):
    agent_name: str
    workspace_id: str
    creator: str | None = None
    voice: bool = Field(default=False)
    status: int = Field(default=1, description="1-active, 0-inactive, 2-deleted")
    allow_model_choice: bool = Field(default=True)
    model: str | None = None
    system_prompt: str
    agent_files: dict[str, str] | None = {}


class AgentDelete(BaseModel):
    agent_id: UUID
    workspace_id: str | None = None


class AgentUpdate(BaseModel):
    agent_id: UUID
    workspace_id: str | None = None
    agent_name: str | None = None
    creator: str | None = None
    voice: bool | None = None
    status: int | None = None
    allow_model_choice: bool | None = None
    model: str | None = None
    system_prompt: str | None = None
    agent_files: dict[str, str] | None = {}


class AgentResponse(BaseModel):
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


@router.post("/add_agent")
def create_agent(
    request: Request,
    agent_data: AgentCreate,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Create a new agent record in the database.
    """

    user_jwt_content = getJWT(request.state)

    if (
        user_jwt_content["workspace_role"].get(agent_data.workspace_id, None)
        != "teacher"
        and not user_jwt_content["system_admin"]
    ):
        return response(
            False, status_code=403, message="You do not have access to this resource"
        )
    new_agent_id = uuid4()
    new_agent = Agent(
        agent_id=new_agent_id,
        created_at=datetime.now(),
        agent_name=agent_data.agent_name,
        workspace_id=agent_data.workspace_id,
        creator=agent_data.creator,
        updated_at=datetime.now(),
        voice=agent_data.voice,
        status=agent_data.status,
        allow_model_choice=agent_data.allow_model_choice,
        model=agent_data.model,
        agent_files=agent_data.agent_files,
    )
    db.add(new_agent)
    _ = agent_prompt_handler.put_agent_prompt(
        str(new_agent.agent_id), agent_data.system_prompt
    )

    # if there is agent files, embed the files with pinecone
    if agent_data.agent_files:
        fsh = FileStorageHandler()
        for file_id, file_name in agent_data.agent_files.items():
            file_path = fsh.get_file(file_id)
            if file_path:
                _ = embed_file(
                    "namespace-test",
                    f"{agent_data.workspace_id}-{new_agent_id}",
                    file_path,
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
            f"Inserted new agent: {new_agent.agent_id} - {new_agent.agent_name}"
        )
        return response(True, {"agent_id": str(new_agent.agent_id)})
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to insert new agent: {e}")
        return response(False, message=str(e))


@router.post("/delete_agent")
def delete_agent(
    request: Request, delete_data: AgentDelete, db: Annotated[Session, Depends(get_db)]
):
    """
    Delete an existing agent record in the database by marking it as status=2.
    Will not actually delete the record or prompt from the database..
    """

    agent_workspace: AgentValue = (
        db.query(Agent).filter(Agent.agent_id == delete_data.agent_id).first()
    )  # pyright: ignore[reportAssignmentType]

    wsID = delete_data.workspace_id or agent_workspace.workspace_id

    user_jwt_content = getJWT(request.state)
    if (
        user_jwt_content["workspace_role"].get(wsID, None) != "teacher"
        and not user_jwt_content["system_admin"]
    ):
        return response(
            False, status_code=403, message="You do not have access to this resource"
        )
    agent_to_delete: AgentValue | None = (
        db.query(Agent).filter(Agent.agent_id == delete_data.agent_id).first()
    )  # pyright: ignore[reportAssignmentType]
    if not agent_to_delete:
        logger.error(f"Agent not found: {delete_data.agent_id}")
        return response(False, status_code=404, message="Agent not found")
    try:
        # mark the agent as deleted by setting the status to 2
        agent_to_delete.status = 2
        db.commit()
        logger.info(f"Deleted agent: {delete_data.agent_id}")
        return response(True, {"agent_id": str(delete_data.agent_id)})
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete agent: {e}")
        return response(False, message=str(e))


@router.post("/update_agent")
def edit_agent(
    request: Request, update_data: AgentUpdate, db: Annotated[Session, Depends(get_db)]
):
    """
    Update an existing agent record in the database.
    """

    user_jwt_content = getJWT(request.state)
    if (
        user_jwt_content["workspace_role"].get(update_data.workspace_id or "All", None)
        != "teacher"
        and not user_jwt_content["system_admin"]
    ):
        return response(
            False, status_code=403, message="You do not have access to this resource"
        )
    agent_to_update: AgentValue | None = (
        db.query(Agent).filter(Agent.agent_id == update_data.agent_id).first()
    )  # pyright: ignore[reportAssignmentType]
    if not agent_to_update:
        logger.error(f"Agent not found: {update_data.agent_id}")
        return response(False, status_code=404, message="Agent not found")

    # Update the agent fields if provided
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
        fsh = FileStorageHandler()
        for file_id, file_name in update_data.agent_files.items():
            file_path = fsh.get_file(file_id)
            if file_path:
                _ = embed_file(
                    "namespace-test",
                    f"{update_data.workspace_id}-{update_data.agent_id}",
                    file_path,
                    file_id,
                    file_name,
                    "pdf",
                    str(update_data.agent_id),
                    update_data.workspace_id or agent_to_update.workspace_id,
                )
            else:
                logger.error(f"Failed to embed file: {file_id}")
    agent_to_update.updated_at = datetime.now()

    if update_data.system_prompt is not None:
        _ = agent_prompt_handler.put_agent_prompt(
            str(agent_to_update.agent_id), update_data.system_prompt
        )

    try:
        db.commit()
        db.refresh(agent_to_update)
        logger.info(f"Updated agent: {agent_to_update.agent_id}")
        return response(True, {"agent_id": str(agent_to_update.agent_id)})
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update agent: {e}")
        return response(False, message=str(e))


@router.get("/agents")
def list_agents(
    request: Request,
    workspace_id: str,
    db: Annotated[Session, Depends(get_db)],
    page: int = 1,
    page_size: int = 10,
):
    """
    List agents with pagination.
    """
    user_jwt_content = getJWT(request.state)
    user_role = user_jwt_content["workspace_role"].get(workspace_id, None)
    if user_role is None:
        return response(
            False, status_code=403, message="You do not have access to this resource"
        )
    query = db.query(Agent).join(
        Workspace,
        Agent.workspace_id == Workspace.workspace_id,
    ).filter(
        Agent.workspace_id == workspace_id, Agent.status != 2,
        Workspace.status != 2
    )  # exclude deleted agents
    total = query.count()
    query = query.order_by(Agent.updated_at.desc())
    skip = (page - 1) * page_size
    agents: list[AgentValue] = (
        query.offset(skip).limit(page_size).all()
    )  # pyright: ignore[reportAssignmentType]
    # get the prompt for each agent
    if user_role == "teacher":
        agentRet: list[AgentTeacherResponse] = (
            agents  # pyright: ignore[reportAssignmentType]
        )
        for agent in agentRet:
            agent.system_prompt = (
                agent_prompt_handler.get_agent_prompt(str(agent.agent_id)) or ""
            )
        agents = agentRet  # pyright: ignore[reportAssignmentType]
    else:
        for agent in agents:
            agent.agent_files = {}
    return response(True, data={"agents": agents, "total": total})


@router.get("/agent/{agent_id}")
def get_agent_by_id(
    request: Request, agent_id: UUID, db: Annotated[Session, Depends(get_db)]
):
    """
    Fetch an agent by its UUID.
    """
    agent: AgentValue | None = (
        db.query(Agent).filter(Agent.agent_id == agent_id, Agent.status != 2).first()
    )  # pyright: ignore[reportAssignmentType] exclude deleted agents
    if agent is None:
        return response(False, status_code=404, message="Agent not found")
    agent_workspace = agent.workspace_id
    user_jwt_content = getJWT(request.state)
    user_role = user_jwt_content["workspace_role"].get(agent_workspace, None)
    if user_role is None:
        return response(
            False, status_code=403, message="You do not have access to this resource"
        )
    if user_role != "teacher":
        agent.agent_files = {}
    # TODO: not sure if returning data is correct here
    return response(True, data=agent)
