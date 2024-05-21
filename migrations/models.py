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
    UniqueConstraint

Base = declarative_base(metadata=MetaData(schema="public"))
metadata = Base.metadata


class Agent(Base):
    __tablename__ = "ai_agents"

    agent_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    agent_name = Column(String(255), nullable=False)
    course_id = Column(String(31))
    creator = Column(String(16))
    updated_at = Column(DateTime, default=func.now(), nullable=False)
    voice = Column(Boolean, default=False, nullable=False)
    status = Column(Integer, default=1, nullable=False)  # 1-active, 0-inactive, 2-deleted
    allow_model_choice = Column(Boolean, default=True, nullable=False)
    model = Column(String(16))

    def __repr__(self):
        return f"Agent id: {self.agent_id}, name: {self.agent_name}, course_id: {self.course_id}, creator: {self.creator}, status: {self.status}, model: {self.model}"


class Thread(Base):
    __tablename__ = "ai_threads"

    thread_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    user_id = Column(String(15))
    created_at = Column(DateTime, default=func.now(), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('ai_agents.agent_id'), nullable=False)

    def __repr__(self):
        return f"Thread id: {self.thread_id}, user_id: {self.user_id}, created_at: {self.created_at}, agent_id: {self.agent_id}"


class User(Base):
    __tablename__ = "ai_users"

    user_id = Column(Integer, primary_key=True, unique=True)
    first_name = Column(String(60), nullable=False)
    last_name = Column(String(60), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    student_id = Column(String(20), nullable=False, unique=True)
    role = Column(JSON, nullable=False)
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
