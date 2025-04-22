# Copyright (c) 2024.
"""A helper class for facilitating pinecone operations"""

import logging
import uuid

from langchain_openai import OpenAIEmbeddings
from pinecone.control.pinecone import Pinecone
from pydantic import SecretStr

from common.EmbeddingHandler import delete_embeddings, embed_file
from common.EnvManager import getenv
from common.FileStorageHandler import FileStorageHandler

CONFIG = getenv()

OPENAI_API_KEY = CONFIG["OPENAI_API_KEY"]
PINECONE_API_KEY = CONFIG["PINECONE_API_KEY"]
pc = Pinecone(api_key=PINECONE_API_KEY)
embeddings = OpenAIEmbeddings(api_key=SecretStr(OPENAI_API_KEY))
logger = logging.getLogger(__name__)


# Note to self
# agent_files dictionary: {file_id: file_name}
def sync_file_lists(
    index_name: str,
    namespace: str,
    owner_id: str,
    old_file_data: dict[str, str] | None = {},
    new_file_data: dict[str, str] | None = {},
    ownership_type: str = "agent",
) -> None:
    """Synchronizes agent or workspace file lists with Pinecone

    Args:
        index_name: The name of the pinecone index
        namespace: The namespace of the pinecone index
        owner_id: Identifier of the owner (either workspace or agent id)
        old_filename_list: List of old file data from before pinecone operation
        new_filename_list: List of new file data from after pinecone operation
        ownership_type: Optional. The type of owners of the files ('agent' or 'workspace')

    Notes:
        file_data tuples will have the following format:
            (file_path, file_id, file_name, file_type, agent_id, workspace_id)
            This structure is taken directly from the embed_file function parameters
        agent_id or workspace_id will be used based on the 'id' parameter

    """
    # Set up dicts
    if old_file_data is None:
        old_file_data = {}
    if new_file_data is None:
        new_file_data = {}

    # Iterate over all old items to check for discrepancies
    for file_id, file_name in old_file_data.items():
        # If this file is contained within the old list but not the new one, delete its embeddings
        if file_id not in new_file_data:
            if delete_embeddings(index_name, namespace, file_id):
                logger.info(f"Successfully deleted embeddings for file: {file_id}")
            else:
                logger.error(f"Failed to delete embeddings for file: {file_id}")

    # Iterate over all new items to check for further discrepancies
    for file_id, file_name in new_file_data.items():
        # If this file is in the new list but not the old one, add its embeddings to pinecone
        fsh = FileStorageHandler(config=CONFIG)
        file_path = fsh.get_file(uuid.UUID(hex=file_id))

        if file_id not in old_file_data:
            is_successful_embed = embed_file(
                index_name=index_name,
                namespace=namespace,
                file_path=str(file_path),
                file_id=file_id,
                file_name=file_name,
                file_type="pdf",
                agent_id="NA" if ownership_type == "workspace" else owner_id,
                workspace_id="NA" if ownership_type == "agent" else owner_id,
            )
            if is_successful_embed:
                logger.info(f"Successfully added embeddings for file: {file_id}")
            else:
                logger.error(f"Failed to add embeddings for file: {file_id}")
