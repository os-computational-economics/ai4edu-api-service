"""
A script which re-embeds all agent files based on the current environment
This will be either ai4edu-dev or ai4edu-prod, depending on which index to re-embed files to
"""

import logging
import uuid

from pinecone.control.pinecone import Pinecone

from common.AgentPromptHandler import AgentPromptHandler
from common.EmbeddingHandler import embed_file
from common.EnvManager import getenv
from common.FileStorageHandler import FileStorageHandler
from migrations.models import Agent, AgentValue
from migrations.session import get_db

# Set up variables
logger = logging.getLogger(__name__)
CONFIG = getenv()

index_name = CONFIG["PINECONE_INDEX"]
PINECONE_API_KEY = CONFIG["PINECONE_API_KEY"]
DEFAULT_FILE_TYPE = "pdf"

pc = Pinecone(api_key=PINECONE_API_KEY)
agent_prompt_handler = AgentPromptHandler(config=CONFIG)

# --- Start of the migration script component ---
# Note that only the pinecone database is changed through this script,
# no changes are made to the Postgres DB

# Start DB session, set up file storage handler
db = next(get_db())
fsh = FileStorageHandler(CONFIG)

# Get all agents first
agents: list[AgentValue] | None = db.query(Agent).all()  # pyright: ignore[reportAssignmentType]

if not agents:
    logger.info("No agents to modify!")
else:
    for agent in agents:
        # For each agent, get its files and embed them within the new pinecone index
        # under the same file id and with the new structure 'agent-{agent_id}'
        for file_id, file_name in agent.agent_files.items():
            # Connect to index
            pc_index = pc.Index(index_name)
            file_path = fsh.get_file(uuid.UUID(hex=file_id))
            namespace = f"agent-{agent.agent_id}"

            # Search for vectors with the given file_id
            docs_found = pc_index.query(
                namespace=namespace,
                top_k=1000,
                include_metadata=True,
                filter={"file_id": file_id},
                vector=[0.0]
                * 1536,  # Dummy vector, this should not be used within filter-only queries
            )

            # Get any embeddings existing for this file in the given index
            ids_found = [match["id"] for match in docs_found["matches"]]

            # Only add embeddings to given index if they don't already exist there!
            if not ids_found:
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
            else:
                logger.info(
                    f"Embeddings for this file already exist in index {index_name}, no re-embedding necessary"
                )
