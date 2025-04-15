"""A script modifying the agent_files of all agents in the database"""

import logging
import uuid

from common.AgentPromptHandler import AgentPromptHandler
from common.EmbeddingHandler import embed_file
from common.EnvManager import getenv
from common.FileStorageHandler import FileStorageHandler
from migrations.session import get_db
from migrations.models import Agent, AgentValue

logger = logging.getLogger(__name__)
CONFIG = getenv()
agent_prompt_handler = AgentPromptHandler(config=CONFIG)

index_name = CONFIG["PINECONE_DEV"]
DEFAULT_FILE_TYPE = "pdf"

# Start of the migration script component
# Note that only the pinecone database is changed through this script,
# no changes are made to the Postgres DB

if __name__ == "__main__":
    # Start DB session, set up file storage handler
    db = next(get_db())
    fsh = FileStorageHandler(CONFIG)

    # Get all agents first
    agents: list[AgentValue] | None = (
        db.query(Agent).all()
    )  # pyright: ignore[reportAssignmentType]

    if not agents:
        logger.info("No agents to modify!")
    else:
        for agent in agents:
            # For each agent, get its files and embed them within the new pinecone index
            # under the same file id and with the new structure 'agent-{agent_id}'
            for file_id, file_name in agent.agent_files.items():
                file_path = fsh.get_file(uuid.UUID(hex=file_id))
                namespace = f"agent-{agent.agent_id}"

                embed_file_result = embed_file(
                    index_name=index_name,
                    namespace=namespace,
                    file_path=str(file_path),
                    file_id=file_id,
                    file_name=file_name,
                    file_type=DEFAULT_FILE_TYPE,
                    agent_id=str(agent.agent_id),
                )
                if embed_file_result:
                    logger.info(
                        f"Successfully recreated embeddings for file with id: {file_id}"
                    )
                else:
                    logger.info(
                        f"Failed to recreate embeddings for file with id: {file_id}"
                    )
