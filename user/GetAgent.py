import os
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from fastapi import APIRouter
from sqlalchemy.orm import Session
from uuid import UUID
from utils.response import response
from pydantic import BaseModel

from migrations.session import get_db

router = APIRouter()

# class AgentRequest(BaseModel): 
#     agent_id: UUID
#     user_id: UUID | None = None #I was thinking in the future we may want to track this??
    

@router.get("/get/{agent_id}")
def get_agent_by_id(
    agent_id : UUID,
):
    engine = create_engine(os.getenv("DB_URI"))
    conn = engine.connect()
    result = conn.execute(text("select * from ai_agents where agent_id = '52dd624a-af5e-4c36-8254-b76cdd5e9f57'"))
    return response(True, data= "here"+str(result.fetchone()[1]))


