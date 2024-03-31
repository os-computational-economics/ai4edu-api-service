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
    result = conn.execute(text("select * from ai_agents where agent_id = '" + str(agent_id) + "'"))
    row = result.first()
    print(row)
    
    if row is None:
        return response(False, status_code=404, message="Agent not found")
    elif row[7] != 1:# the row[7] -= 1 checks if the model is not active 
        return response(False, status_code=404, message="Agent is inactive")
    else:
        return response(True, data= {
            "agent_name" : row[2],
            "coures_id" : row[3],
            "voice" : row[6],
            "model_choice": row[8],
            "model" : row[9],
        })


