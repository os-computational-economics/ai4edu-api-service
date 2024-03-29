from sqlalchemy import create_engine
from sqlalchemy.sql import text

class GetAgent:
    """
    This class is used to get information about an agent
    for the front end like whether to enable text-to-speech
    or what model to use
    """
    def __init__(agent_id, self) -> None:
        self.agent_id = agent_id

    def getAgentProperties(self):
        engine = create_engine(os.getenv("DB_URI"))
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version FROM db_version"))
            db_result = result.fetchone()[0]
        

