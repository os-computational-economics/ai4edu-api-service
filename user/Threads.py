# Copyright (c) 2024.
# -*-coding:utf-8 -*-
"""
@file: Threads.py
@author: Jerry(Ruihuang)Yang
@email: rxy216@case.edu
@time: 4/16/24 12:14
"""
import uuid
import logging

from utils.response import response
from migrations.models import Thread
from migrations.session import get_db
from fastapi import Request

logger = logging.getLogger(__name__)


def new_thread(request: Request, agent_id: str):
    for db in get_db():
        user_id = request.state.user_jwt_content['user_id']
        student_id = request.state.user_jwt_content['student_id']
        thread_id = str(uuid.uuid4())
        thread = Thread(thread_id=thread_id, user_id=user_id, agent_id=agent_id, student_id=student_id)
        db.add(thread)

        try:
            db.commit()
            logger.info(f"New thread created: {thread_id}")
            return response(True, {"thread_id": thread_id})
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create new thread: {str(e)}")
            return response(False, {}, "Failed to create new thread")
