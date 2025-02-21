# Copyright (c) 2024.
"""Classes for interracting with the Postgres database"""

from datetime import datetime
from enum import IntEnum
from typing import Any, Literal, override
from uuid import UUID as UUIDType  # noqa: N811
from zoneinfo import ZoneInfo

from pydantic import BaseModel
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


class BaseType:
    """Base class for SQLAlchemy models."""

    def __init__(**kwargs: Any) -> None:  # pyright: ignore[reportAny, reportExplicitAny]  # noqa: ANN401
        """Initialize the base class."""
        super().__init__(**kwargs)

    metadata: type = MetaData


Base: type[BaseType] = declarative_base(metadata=MetaData(schema="public"))
metadata = Base.metadata


class Agent(Base):
    """Agent model."""

    __tablename__: Literal["ai_agents"] = "ai_agents"

    agent_id: Column[UUIDType] = Column(
        UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
    )
    created_at: Column[datetime] = Column(DateTime, default=func.now(), nullable=False)
    agent_name: Column[str] = Column(String(255), nullable=False)
    workspace_id: Column[str] = Column(String(31))
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


class AgentValue(BaseModel):
    """Python representation of an Agent row"""

    agent_id: str = ""
    created_at: datetime = datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"]))
    agent_name: str = ""
    workspace_id: str = ""
    creator: str = ""
    updated_at: datetime = datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"]))
    voice: bool = False
    status: AgentStatus = AgentStatus.ACTIVE
    allow_model_choice: bool = True
    model: str = ""
    agent_files: dict[str, str]

    def __init__(self) -> None:
        """Initialize workspace"""
        super().__init__()
        self.agent_files = {}


class AgentTeacherResponse(AgentValue):
    """Teacher override for system prompt"""

    system_prompt: str = ""


class Thread(Base):
    """Thread model. Represents a conversation between a student and an AI agent."""

    __tablename__: Literal["ai_threads"] = "ai_threads"

    thread_id: Column[UUIDType] = Column(
        UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
    )
    student_id: Column[str] = Column(String(16))
    created_at: Column[datetime] = Column(DateTime, default=func.now(), nullable=False)
    agent_id: Column[UUIDType] = Column(
        UUID(as_uuid=True),
        ForeignKey("ai_agents.agent_id"),
        nullable=False,
    )
    user_id: Column[int] = Column(Integer, nullable=False)
    workspace_id: Column[str] = Column(String(16), nullable=False)
    agent_name: Column[str] = Column(String(255), nullable=False)

    @override
    def __repr__(self) -> str:
        return f"""Thread id: {self.thread_id}, user_id: {self.user_id}, created_at: {
            self.created_at
        }, agent_id: {self.agent_id}"""


class ThreadValue:
    """Python representation of a Thread row"""

    thread_id: str = ""
    student_id: str = ""
    created_at: datetime = datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"]))
    agent_id: str = ""
    user_id: int = 0
    workspace_id: str = ""
    agent_name: str = ""


class User(Base):
    """User model."""

    __tablename__: Literal["ai_users"] = "ai_users"

    user_id: Column[int] = Column(Integer, primary_key=True, unique=True)
    first_name: Column[str] = Column(String(60), nullable=False)
    last_name: Column[str] = Column(String(60), nullable=False)
    email: Column[str] = Column(String(150), nullable=False, unique=True)
    student_id: Column[str] = Column(String(20), nullable=False, unique=True)
    workspace_role: Column[JSON] = Column(JSON, nullable=False)
    system_admin: Column[bool] = Column(Boolean, default=False, nullable=False)
    school_id: Column[int] = Column(Integer, nullable=False)
    last_login: Column[datetime] = Column(DateTime)
    create_at: Column[datetime] = Column(DateTime)

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
    school_id: int = 0
    last_login: datetime = datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"]))
    create_at: datetime = datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"]))

    def __init__(self) -> None:
        """Initialize workspace"""
        self.workspace_role = {}


class RefreshToken(Base):
    """RefreshToken model"""

    __tablename__: Literal["ai_refresh_tokens"] = "ai_refresh_tokens"

    token_id: Column[UUIDType] = Column(
        UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
    )
    user_id: Column[int] = Column(
        Integer,
        ForeignKey("ai_users.user_id"),
        nullable=False,
    )
    token: Column[UUIDType] = Column(UUID(as_uuid=True), nullable=False, unique=True)
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

    token_id: str = ""
    user_id: int = 0
    token: str = ""
    created_at: datetime = datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"]))
    expire_at: datetime = datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"]))
    issued_token_count: int = 0


class File(Base):
    """File model."""

    __tablename__: Literal["ai_files"] = "ai_files"

    file_id: Column[UUIDType] = Column(
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

    file_id: str = ""
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

    workspace_id: Column[str] = Column(String(16), primary_key=True, nullable=False)
    workspace_name: Column[str] = Column(String(64), unique=True, nullable=False)
    status: Column[int] = Column(
        Integer,
        default=1,
        nullable=False,
    )  # 1-active, 0-inactive, 2-deleted
    school_id: Column[int] = Column(Integer, default=0, nullable=False)
    workspace_password: Column[str] = Column(String(128), nullable=False)

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

    workspace_id: str = ""
    workspace_name: str = ""
    status: WorkspaceStatus = WorkspaceStatus.ACTIVE
    school_id: int = 0
    workspace_password: str = ""


class UserWorkspace(Base):
    """Users in Workspaces many to many model."""

    __tablename__: Literal["ai_user_workspace"] = "ai_user_workspace"

    user_id: Column[int] = Column(Integer)
    workspace_id: Column[str] = Column(String(16), nullable=False)
    role: Column[str] = Column(String(16), default="pending", nullable=False)
    created_at: Column[datetime] = Column(DateTime, default=func.now(), nullable=False)
    updated_at: Column[datetime] = Column(DateTime)
    student_id: Column[str] = Column(String(16), nullable=False)

    __table_args__: tuple[PrimaryKeyConstraint] = (
        PrimaryKeyConstraint("workspace_id", "student_id", name="ai_user_workspace_pk"),
    )

    @override
    def __repr__(self) -> str:
        return f"""AIUserWorkspace user_id: {self.user_id}, workspace_id: {
            self.workspace_id
        }, role: {self.role}"""


class UserWorkspaceValue:
    """Python representation of a UserWorkspace row"""

    user_id: int = 0
    workspace_id: str = ""
    role: str = ""
    created_at: datetime = datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"]))
    updated_at: datetime = datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"]))
    student_id: str = ""


class UserFeedback(Base):
    """Feedback model."""

    __tablename__: Literal["ai_feedback"] = "ai_feedback"

    feedback_id: Column[int] = Column(Integer, primary_key=True)
    user_id: Column[int] = Column(Integer, nullable=False)
    thread_id: Column[UUIDType] = Column(UUID(as_uuid=True), nullable=False)
    message_id: Column[str] = Column(String(256))
    feedback_time: Column[datetime] = Column(DateTime, default=func.now())
    rating_format: Column[int] = Column(Integer, nullable=False)
    rating: Column[int] = Column(Integer, nullable=False)
    comments: Column[str] = Column(Text)


class UserFeedbackValue:
    """Python representation of a UserFeedback row"""

    feedback_id: int = 0
    user_id: int = 0
    thread_id: str = ""
    message_id: str = ""
    feedback_time: datetime = datetime.now(tz=ZoneInfo(CONFIG["TIMEZONE"]))
    rating_format: Literal[2, 5, 10] = 2
    rating: int = 0
    comments: str = ""
