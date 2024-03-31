import os
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from fastapi import APIRouter
from uuid import UUID
from utils.response import response
from pydantic import BaseModel

router = APIRouter()

class AgentRequest(BaseModel): 
    agent_id: UUID
    user_id: UUID | None = None #I was thinking in the future we may want to track this??

@router.get("/test")
def get_things():
    return response(True, data="hello world")


@router.get("/stuff")
def get_agent_by_id(
    req : AgentRequest
):
    return response(True, data=req.agent_id)


