# Copyright (c) 2024.
# -*-coding:utf-8 -*-
"""
@file: Threads.py
@author: Jerry(Ruihuang)Yang
@email: rxy216@case.edu
@time: 4/16/24 12:14
"""
from typing import Any
import uuid
import logging

from utils.response import response
from migrations.models import Thread
from migrations.models import Agent
from migrations.session import get_db
from fastapi import Request

logger = logging.getLogger(__name__)


def new_thread(request: Request, agent_id: str, workspace_id: str):

    user_jwt_content: dict[str, Any] = (
        request.state.user_jwt_content
    )  # pyright: ignore[reportAny]

    for db in get_db():
        user_id: str = user_jwt_content["user_id"]
        student_id: str = user_jwt_content["student_id"]
        is_user_in_workspace: bool = user_jwt_content["workspace_role"].get(
            workspace_id, None
        )
        if not is_user_in_workspace:
            logger.error(f"User {user_id} is not in workspace {workspace_id}")
            return response(False, {}, "User is not in workspace")
        thread_id = str(uuid.uuid4())
        agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
        if not agent:
            logger.error(f"Agent not found: {agent_id}")
            return response(False, {}, "Agent not found")
        thread = Thread(
            thread_id=thread_id,
            user_id=user_id,
            agent_id=agent_id,
            student_id=student_id,
            workspace_id=workspace_id,
            agent_name=agent.agent_name,
        )
        db.add(thread)

        try:
            db.commit()
            logger.info(f"New thread created: {thread_id}")
            return response(True, {"thread_id": thread_id})
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create new thread: {str(e)}")
            return response(False, {}, "Failed to create new thread")
