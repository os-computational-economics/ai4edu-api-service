import os
from sqlalchemy import create_engine
from sqlalchemy.sql import text

class GetAgent:
    #self.agent_id = ''
    """
    This class is used to get information about an agent
    for the front end like whether to enable text-to-speech
    or what model to use
    """
    def __init__(self):
        self.agent_id = 'asdf'


    def getAgentProperties(self):

        #engine = create_engine(os.getenv("DB_URI"))
        engine = create_engine("postgresql+psycopg://postgres:admin@host.docker.internal:5432/ai4edu_local")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version FROM db_version"))
            print(result)


t = GetAgent()

t.getAgentProperties()

