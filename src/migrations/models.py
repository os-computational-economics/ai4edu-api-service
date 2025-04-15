# Copyright (c) 2024.
"""Classes for interracting with the Postgres database"""

from datetime import datetime
from enum import IntEnum
from typing import Any, Literal, TypedDict, override
from uuid import UUID as UUID_TYPE
from zoneinfo import ZoneInfo

from sqlalchemy import (
    JSON,
    UUID,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.ext.declarative import declarative_base

from common.EnvManager import getenv

CONFIG = getenv()
DEFAULT_UUID = UUID_TYPE("00000000-0000-0000-0000-000000000000")

WorkspaceRole = Literal["student", "teacher"]
WorkspaceRoles = dict[str, WorkspaceRole]


class BaseType:
    """Base class for SQLAlchemy models."""

    def __init__(
        **kwargs: Any,  # noqa: ANN401 # pyright: ignore[reportAny, reportExplicitAny]
    ) -> None:
        """Initialize the base class."""
        super().__init__(**kwargs)

    metadata: type = MetaData


Base: type[BaseType] = declarative_base(metadata=MetaData(schema="public"))
metadata = Base.metadata


class ModelReturn(TypedDict):
    """Base Class for Typed Responses"""


class Agent(Base):
    """Agent model."""

    __tablename__: Literal["ai_agents"] = "ai_agents"

    agent_id: Column[UUID_TYPE] = Column(
        UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
    )
    created_at: Column[datetime] = Column(DateTime, default=func.now(), nullable=False)
    agent_name: Column[str] = Column(String(255), nullable=False)
    workspace_id: Column[UUID_TYPE] = Column(UUID(as_uuid=True), nullable=False)
    creator: Column[str] = Column(String(16))
    updated_at: Column[datetime] = Column(DateTime, default=func.now(), nullable=False)
    voice: Column[bool] = Column(Boolean, default=False, nullable=False)
    status: Column[int] = Column(
        Integer,
        default=1,
        nullable=False,
    )  # 1-active, 0-inactive, 2-deleted
    allow_model_choice: Column[bool] = Column(Boolean, default=True, nullable=False)
    model: Column[str] = Column(String(16))
    agent_files: Column[JSON] = Column(JSON)  # {"file_id": "file_name"}

    @override
    def __repr__(self) -> str:
        return f"""Agent id: {self.agent_id}, name: {self.agent_name}, creator: {
            self.creator
        }, status: {self.status}, model: {self.model}"""


class AgentStatus(IntEnum):
    """Enum for agent status."""

    ACTIVE = 1
    INACTIVE = 0
    DELETED = 2


class AgentValue:
    """Python representation of an Agent row"""

    agent_id: UUID_TYPE = DEFAULT_UUID
    created_at: datetime = datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"]))
    agent_name: str = ""
    workspace_id: UUID_TYPE = DEFAULT_UUID
    creator: str = ""
    updated_at: datetime = datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"]))
    voice: bool = False
    status: AgentStatus = AgentStatus.ACTIVE
    allow_model_choice: bool = True
    model: str = ""
    agent_files: dict[str, str] = {}  # noqa: RUF012


class AgentChatReturn(ModelReturn):
    """Python representation of the return for the chat page to get agent information"""

    agent_id: str
    agent_name: str
    workspace_id: UUID_TYPE
    voice: bool
    allow_model_choice: bool
    model: str  # allow_model_choice is True, model will be empty for user choice
    agent_files: dict[str, str]
    status: AgentStatus


def agent_chat_return(av: AgentValue | None = None) -> AgentChatReturn:
    """Makes an AgentChatReturn object from a python object

    Args:
        av: The AgentValue to return

    Returns:
        A TypedDict of the return object

    """
    return (
        {
            "agent_id": str(av.agent_id),
            "agent_name": av.agent_name,
            "allow_model_choice": av.allow_model_choice,
            "model": av.model,
            "voice": av.voice,
            "workspace_id": av.workspace_id,
            "agent_files": av.agent_files,
            "status": av.status,
        }
        if av
        else {
            "agent_id": "",
            "agent_name": "",
            "allow_model_choice": False,
            "model": "",
            "voice": False,
            "workspace_id": DEFAULT_UUID,
            "agent_files": {},
            "status": AgentStatus.INACTIVE,
        }
    )


class AgentDashboardReturn(AgentChatReturn):
    """Dictionary representation of an Agent row for the dashboard"""

    created_at: str
    creator: str
    updated_at: str
    system_prompt: str


def agent_dashboard_return(
    av: AgentValue | None = None, system_prompt: str = "", is_teacher: bool = False
) -> AgentDashboardReturn:
    """Makes an AgentDashboardReturn object from a python object

    Args:
        av: The AgentValue to return
        system_prompt: The system prompt to return
        is_teacher: If the user is a teacher

    Returns:
        A TypedDict of the return object

    """
    return (
        {
            "agent_id": str(av.agent_id),
            "agent_name": av.agent_name,
            "allow_model_choice": av.allow_model_choice,
            "model": av.model,
            "voice": av.voice,
            "workspace_id": av.workspace_id,
            "agent_files": av.agent_files if is_teacher else {},
            "created_at": str(av.created_at),
            "creator": av.creator,
            "status": av.status,
            "system_prompt": system_prompt if is_teacher else "",
            "updated_at": str(av.updated_at),
        }
        if av
        else {
            "agent_id": "",
            "agent_name": "",
            "allow_model_choice": False,
            "model": "",
            "voice": False,
            "workspace_id": DEFAULT_UUID,
            "agent_files": {},
            "created_at": "",
            "creator": "",
            "status": AgentStatus.INACTIVE,
            "system_prompt": "",
            "updated_at": "",
        }
    )


class Thread(Base):
    """Thread model. Represents a conversation between a student and an AI agent."""

    __tablename__: Literal["ai_threads"] = "ai_threads"

    thread_id: Column[UUID_TYPE] = Column(
        UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
    )
    student_id: Column[str] = Column(String(16))
    created_at: Column[datetime] = Column(DateTime, default=func.now(), nullable=False)
    agent_id: Column[UUID_TYPE] = Column(
        UUID(as_uuid=True),
        ForeignKey("ai_agents.agent_id"),
        nullable=False,
    )
    user_id: Column[int] = Column(Integer, nullable=False)
    workspace_id: Column[UUID_TYPE] = Column(UUID(as_uuid=True), nullable=False)
    agent_name: Column[str] = Column(String(255), nullable=False)

    @override
    def __repr__(self) -> str:
        return f"""Thread id: {self.thread_id}, user_id: {self.user_id}, created_at: {
            self.created_at
        }, agent_id: {self.agent_id}"""


class ThreadValue:
    """Python representation of a Thread row"""

    thread_id: UUID_TYPE = DEFAULT_UUID
    created_at: datetime = datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"]))
    agent_id: UUID_TYPE = DEFAULT_UUID
    user_id: int = 0
    workspace_id: UUID_TYPE = DEFAULT_UUID
    agent_name: str = ""


class ThreadReturn(ModelReturn):
    """Dictionary representation of a Thread row"""

    thread_id: str
    created_at: str
    agent_id: str
    user_id: int
    workspace_id: UUID_TYPE
    agent_name: str


def thread_return(tv: ThreadValue | None = None) -> ThreadReturn:
    """Makes an ThreadReturn object from a python object

    Args:
        tv: The ThreadValue to return

    Returns:
        A TypedDict of the return object

    """
    return (
        {
            "agent_id": str(tv.agent_id),
            "agent_name": tv.agent_name,
            "created_at": str(tv.created_at),
            "thread_id": str(tv.thread_id),
            "user_id": tv.user_id,
            "workspace_id": tv.workspace_id,
        }
        if tv
        else {
            "agent_id": "",
            "agent_name": "",
            "created_at": "",
            "thread_id": "",
            "user_id": 0,
            "workspace_id": DEFAULT_UUID,
        }
    )


class User(Base):
    """User model."""

    __tablename__: Literal["ai_users"] = "ai_users"

    user_id: Column[int] = Column(Integer, primary_key=True, unique=True)
    first_name: Column[str] = Column(String(60), nullable=False)
    last_name: Column[str] = Column(String(60), nullable=False)
    email: Column[str] = Column(String(150), nullable=False, unique=True)
    student_id: Column[str] = Column(String(20), nullable=False, unique=True)
    workspace_role: Column[JSON] = Column(JSON, nullable=False)
    school_id: Column[int] = Column(Integer, nullable=False)
    last_login: Column[datetime] = Column(DateTime)
    create_at: Column[datetime] = Column(DateTime)
    system_admin: Column[bool] = Column(Boolean, default=False, nullable=False)
    workspace_admin: Column[bool] = Column(Boolean, default=False, nullable=False)

    @override
    def __repr__(self) -> str:
        return f"User id: {self.user_id}, email: {self.email}"


class UserValue:
    """Python representation of a User row"""

    user_id: int = 0
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    student_id: str = ""
    workspace_role: dict[str, Any]  # pyright: ignore[reportExplicitAny]
    system_admin: bool = False
    workspace_admin: bool = False
    school_id: int = 0
    last_login: datetime = datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"]))
    create_at: datetime = datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"]))

    def __init__(self) -> None:
        """Initialize workspace"""
        self.workspace_role = {}


class UserReturn(ModelReturn):
    """Dictionary representation of a User row"""

    user_id: int
    email: str
    first_name: str
    last_name: str
    student_id: str
    workspace_role: WorkspaceRoles


class PrivilegedUserReturn(UserReturn):
    """Dictionary representation of a privileged User row with additional admin information"""

    system_admin: bool
    workspace_admin: bool
    created_workspaces: dict[UUID_TYPE, str]  # workspace_id: workspace_name


def privileged_user_return(
    uv: UserValue | None = None, created_workspaces: dict[UUID_TYPE, str] | None = None
) -> PrivilegedUserReturn:
    """Makes a PrivilegedUserReturn object from a python object

    Args:
        uv: The UserValue to return
        created_workspaces: Dict of workspace IDs to workspace names created by the user

    Returns:
        A TypedDict of the return object

    """
    base_return = user_return(uv)
    return {
        **base_return,
        "system_admin": uv.system_admin if uv else False,
        "workspace_admin": uv.workspace_admin if uv else False,
        "created_workspaces": created_workspaces or {},
    }


def user_return(uv: UserValue | None = None) -> UserReturn:
    """Makes an UserReturn object from a python object

    Args:
        uv: The UserValue to return

    Returns:
        A TypedDict of the return object

    """
    return (
        {
            "email": uv.email,
            "first_name": uv.first_name,
            "last_name": uv.last_name,
            "student_id": uv.student_id,
            "user_id": uv.user_id,
            "workspace_role": uv.workspace_role,
        }
        if uv
        else {
            "email": "",
            "first_name": "",
            "last_name": "",
            "student_id": "",
            "user_id": 0,
            "workspace_role": {},
        }
    )


class RefreshToken(Base):
    """RefreshToken model"""

    __tablename__: Literal["ai_refresh_tokens"] = "ai_refresh_tokens"

    token_id: Column[UUID_TYPE] = Column(
        UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
    )
    user_id: Column[int] = Column(
        Integer,
        ForeignKey("ai_users.user_id"),
        nullable=False,
    )
    token: Column[UUID_TYPE] = Column(UUID(as_uuid=True), nullable=False, unique=True)
    created_at: Column[datetime] = Column(DateTime, default=func.now(), nullable=False)
    expire_at: Column[datetime] = Column(DateTime, nullable=False)
    issued_token_count: Column[int] = Column(Integer, default=0, nullable=False)

    __table_args__: tuple[UniqueConstraint] = (UniqueConstraint("token"),)

    @override
    def __repr__(self) -> str:
        return f"""RefreshToken id: {self.token_id}, user_id: {self.user_id}, token: {
            self.token
        }"""


class RefreshTokenValue:
    """Python representation of a RefreshToken row"""

    token_id: UUID_TYPE = DEFAULT_UUID
    user_id: int = 0
    token: UUID_TYPE = DEFAULT_UUID
    created_at: datetime = datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"]))
    expire_at: datetime = datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"]))
    issued_token_count: int = 0


class TokenReturn(ModelReturn):
    """Response containing an Access Token."""

    access_token: str


def token_return(tk: str = "") -> TokenReturn:
    """Makes an TokenReturn object from a token

    Args:
        tk: The token to return

    Returns:
        A TypedDict of the return object

    """
    return {"access_token": tk}


class File(Base):
    """File model."""

    __tablename__: Literal["ai_files"] = "ai_files"

    file_id: Column[UUID_TYPE] = Column(
        UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
    )
    file_name: Column[str] = Column(String, nullable=False)
    file_desc: Column[str] = Column(String)
    file_type: Column[str] = Column(String(63), nullable=False)
    file_ext: Column[str] = Column(String(15))
    file_status: Column[int] = Column(Integer, default=1)
    chunking_separator: Column[str] = Column(String(15))
    created_at: Column[datetime] = Column(DateTime, default=func.now(), nullable=False)

    @override
    def __repr__(self) -> str:
        return f"""Files id: {self.file_id}, name: {self.file_name}, type: {
            self.file_type
        }, status: {self.file_status}"""


class FileValue:
    """Python representation of a File row"""

    file_id: UUID_TYPE = DEFAULT_UUID
    file_name: str = ""
    file_desc: str = ""
    file_type: str = ""
    file_ext: str = ""
    file_status: int = 0
    chunking_separator: str = ""
    created_at: datetime = datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"]))


class Workspace(Base):
    """Workspace model."""

    __tablename__: Literal["ai_workspaces"] = "ai_workspaces"

    workspace_id: Column[UUID_TYPE] = Column(
        UUID(as_uuid=True), primary_key=True, nullable=False
    )
    workspace_name: Column[str] = Column(String(64), unique=False, nullable=False)
    workspace_prompt: Column[str] = Column(Text(), nullable=True)
    workspace_comment: Column[str] = Column(Text(), nullable=True)
    created_by: Column[int] = Column(Integer, nullable=False)
    workspace_join_code: Column[str] = Column(String(8), nullable=False, unique=True)
    status: Column[int] = Column(
        Integer, default=1, nullable=False
    )  # 1-active, 0-inactive, 2-deleted
    school_id: Column[int] = Column(Integer, default=0, nullable=False)

    @override
    def __repr__(self) -> str:
        return f"""AIWorkspace id: {self.workspace_id}, name: {
            self.workspace_name
        }, status: {self.status}, school_id: {self.school_id}"""


class WorkspaceStatus(IntEnum):
    """Enum for workspace status."""

    ACTIVE = 1
    INACTIVE = 0
    DELETED = 2


class WorkspaceValue:
    """Python representation of a Workspace row"""

    workspace_id: UUID_TYPE = DEFAULT_UUID
    workspace_name: str = ""
    workspace_prompt: str = ""
    workspace_comment: str = ""
    created_by: str = ""
    workspace_join_code: str = ""
    status: WorkspaceStatus = WorkspaceStatus.ACTIVE
    school_id: int = 0


class WorkspaceReturn(ModelReturn):
    """Dictionary representation of a Workspace row"""

    workspace_id: UUID_TYPE
    workspace_name: str
    workspace_prompt: str | None
    workspace_comment: str | None
    workspace_join_code: str
    school_id: int
    status: WorkspaceStatus
    created_by: str
    # here, created_by is the name of the creator of the workspace
    # not the user_id. This is to be consistent with the data model, for the convenience
    # of the front end.


def workspace_return(wv: WorkspaceValue | None = None) -> WorkspaceReturn:
    """Makes an WorkspaceReturn object from a python object

    Args:
        wv: The WorkspaceValue to return

    Returns:
        A TypedDict of the return object

    """
    return (
        {
            "workspace_id": wv.workspace_id,
            "workspace_name": wv.workspace_name,
            "workspace_prompt": wv.workspace_prompt,
            "workspace_comment": wv.workspace_comment,
            "workspace_join_code": wv.workspace_join_code,
            "school_id": wv.school_id,
            "status": wv.status,
            "created_by": wv.created_by,
        }
        if wv
        else {
            "workspace_id": DEFAULT_UUID,
            "workspace_name": "",
            "workspace_prompt": "",
            "workspace_comment": "",
            "workspace_join_code": "",
            "status": WorkspaceStatus.INACTIVE,
            "school_id": 0,
            "created_by": "",
        }
    )


class UserWorkspace(Base):
    """Users in Workspaces many to many model."""

    __tablename__: Literal["ai_user_workspace"] = "ai_user_workspace"

    user_id: Column[int] = Column(Integer)
    workspace_id: Column[UUID_TYPE] = Column(UUID(as_uuid=True), nullable=False)
    role: Column[str] = Column(String(16), default="pending", nullable=False)
    created_at: Column[datetime] = Column(DateTime, default=func.now(), nullable=False)
    updated_at: Column[datetime] = Column(DateTime)
    student_id: Column[str] = Column(String(16), nullable=False)

    __table_args__: tuple[PrimaryKeyConstraint] = (
        PrimaryKeyConstraint("workspace_id", "user_id", name="ai_user_workspace_pk"),
    )

    @override
    def __repr__(self) -> str:
        return f"""AIUserWorkspace user_id: {self.user_id}, workspace_id: {
            self.workspace_id
        }, role: {self.role}"""


class UserWorkspaceValue:
    """Python representation of a UserWorkspace row"""

    user_id: int = 0
    workspace_id: UUID_TYPE = DEFAULT_UUID
    role: str = ""
    created_at: datetime = datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"]))
    updated_at: datetime = datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"]))
    student_id: str = ""


class UserFeedback(Base):
    """Feedback model."""

    __tablename__: Literal["ai_feedback"] = "ai_feedback"

    feedback_id: Column[int] = Column(Integer, primary_key=True)
    user_id: Column[int] = Column(Integer, nullable=False)
    thread_id: Column[UUID_TYPE] = Column(UUID(as_uuid=True), nullable=False)
    message_id: Column[str] = Column(String(256))
    feedback_time: Column[datetime] = Column(DateTime, default=func.now())
    rating_format: Column[int] = Column(Integer, nullable=False)
    rating: Column[int] = Column(Integer, nullable=False)
    comments: Column[str] = Column(Text)


class UserFeedbackValue:
    """Python representation of a UserFeedback row"""

    feedback_id: int = 0
    user_id: int = 0
    thread_id: UUID_TYPE = DEFAULT_UUID
    message_id: str = ""
    feedback_time: datetime = datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"]))
    rating_format: Literal[2, 5, 10] = 2
    rating: int = 0
    comments: str = ""


class PendingUserReturn(ModelReturn):
    """Dictionary representation of a pending user in a workspace"""

    student_id: str
    status: str


def pending_user_return(student_id: str) -> PendingUserReturn:
    """Makes a PendingUserReturn object from a student_id

    Args:
        student_id: The student ID to return

    Returns:
        A TypedDict of the return object

    """
    return {
        "student_id": student_id,
        "status": "pending",
    }


class URLReturn(ModelReturn):
    """Response containing a Presigned URL."""

    url: str


def url_return(url: str = "") -> URLReturn:
    """Makes an URLReturn object from a url

    Args:
        url: The url to return

    Returns:
        A TypedDict of the return object

    """
    return {"url": url}
