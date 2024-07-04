# Copyright (c) 2024.
# -*-coding:utf-8 -*-
"""
@file: models.py.py
@author: Jerry(Ruihuang)Yang
@email: rxy216@case.edu
@time: 3/16/24 23:48
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, String, Integer, func, MetaData, Boolean, UUID, ForeignKey, JSON, \
    UniqueConstraint, PrimaryKeyConstraint

Base = declarative_base(metadata=MetaData(schema="public"))
metadata = Base.metadata


class Agent(Base):
    __tablename__ = "ai_agents"

    agent_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    agent_name = Column(String(255), nullable=False)
    workspace_id = Column(String(31))
    creator = Column(String(16))
    updated_at = Column(DateTime, default=func.now(), nullable=False)
    voice = Column(Boolean, default=False, nullable=False)
    status = Column(Integer, default=1, nullable=False)  # 1-active, 0-inactive, 2-deleted
    allow_model_choice = Column(Boolean, default=True, nullable=False)
    model = Column(String(16))
    agent_files = Column(JSON)  # {"file_id": "file_name"}

    def __repr__(self):
        return f"Agent id: {self.agent_id}, name: {self.agent_name}, course_id: {self.course_id}, creator: {self.creator}, status: {self.status}, model: {self.model}"


class Thread(Base):
    __tablename__ = "ai_threads"

    thread_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    student_id = Column(String(16))
    created_at = Column(DateTime, default=func.now(), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('ai_agents.agent_id'), nullable=False)
    user_id = Column(Integer, nullable=False)
    workspace_id = Column(String(16), nullable=False)
    agent_name = Column(String(255), nullable=False)

    def __repr__(self):
        return f"Thread id: {self.thread_id}, user_id: {self.user_id}, created_at: {self.created_at}, agent_id: {self.agent_id}"


class User(Base):
    __tablename__ = "ai_users"

    user_id = Column(Integer, primary_key=True, unique=True)
    first_name = Column(String(60), nullable=False)
    last_name = Column(String(60), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    student_id = Column(String(20), nullable=False, unique=True)
    workspace_role = Column(JSON, nullable=False)
    system_admin = Column(Boolean, default=False, nullable=False)
    school_id = Column(Integer, nullable=False)
    last_login = Column(DateTime)
    create_at = Column(DateTime)

    def __repr__(self):
        return f"User id: {self.user_id}, email: {self.email}"


class RefreshToken(Base):
    __tablename__ = "ai_refresh_tokens"

    token_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey('ai_users.user_id'), nullable=False)
    token = Column(UUID(as_uuid=True), nullable=False, unique=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    expire_at = Column(DateTime, nullable=False)
    issued_token_count = Column(Integer, default=0, nullable=False)

    __table_args__ = (UniqueConstraint('token'),)

    def __repr__(self):
        return f"RefreshToken id: {self.token_id}, user_id: {self.user_id}, token: {self.token}"


class File(Base):
    __tablename__ = "ai_files"

    file_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    file_name = Column(String, nullable=False)
    file_desc = Column(String)
    file_type = Column(String(63), nullable=False)
    file_ext = Column(String(15))
    file_status = Column(Integer, default=1)
    chunking_separator = Column(String(15))
    created_at = Column(DateTime, default=func.now(), nullable=False)

    def __repr__(self):
        return f"Files id: {self.file_id}, name: {self.file_name}, type: {self.file_type}, status: {self.file_status}"


class Workspace(Base):
    __tablename__ = 'ai_workspaces'

    workspace_id = Column(String(16), primary_key=True, nullable=False)
    workspace_name = Column(String(64), unique=True, nullable=False)
    workspace_active = Column(Boolean, default=False, nullable=False)
    school_id = Column(Integer, default=0, nullable=False)
    workspace_password = Column(String(128), nullable=False)

    def __repr__(self):
        return f"AIWorkspace id: {self.workspace_id}, name: {self.workspace_name}, active: {self.workspace_active}, school_id: {self.school_id}"


class UserWorkspace(Base):
    __tablename__ = 'ai_user_workspace'

    user_id = Column(Integer)
    workspace_id = Column(String(16), nullable=False)
    role = Column(String(16), default="pending", nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime)
    student_id = Column(String(16), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint('workspace_id', 'student_id', name='ai_user_workspace_pk'),
    )

    def __repr__(self):
        return f"AIUserWorkspace user_id: {self.user_id}, workspace_id: {self.workspace_id}, role: {self.role}"
