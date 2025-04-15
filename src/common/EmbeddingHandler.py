# Copyright (c) 2024.
"""A collection of utility functions for processing file embeddings"""

from langchain.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone.control.pinecone import Pinecone
from pydantic import SecretStr

from common.EnvManager import getenv

CONFIG = getenv()

OPENAI_API_KEY = CONFIG["OPENAI_API_KEY"]
PINECONE_API_KEY = CONFIG["PINECONE_API_KEY"]
pc = Pinecone(api_key=PINECONE_API_KEY)
embeddings = OpenAIEmbeddings(api_key=SecretStr(OPENAI_API_KEY))


def embed_file(
    index_name: str,
    namespace: str,
    file_path: str,
    file_id: str,
    file_name: str,
    file_type: str,
    agent_id: str = "NA",
    workspace_id: str = "NA",
) -> bool:
    """Embed the file and put the embeddings into the Pinecone index.

    Args:
        index_name: The name of the Pinecone index.
        namespace: The namespace of the Pinecone index.
        file_path: The path of the file to be embedded.
        file_id: The ID of the file.
        file_name: The name of the file.
        file_type: The type of the file.
        agent_id: The ID of the agent. Optional.
        workspace_id: The ID of the workspace. Optional.

    Returns:
        True if the embedding is successful, False otherwise.

    """
    if file_type == "pdf":
        pages = pdf_loader(file_path)
        # add metadata to the pages
        for page in pages:
            if not hasattr(page, "metadata"):
                page.metadata = {}
            page.metadata.update(  # pyright: ignore[reportUnknownMemberType]
                {
                    "file_id": file_id,
                    "file_type": file_type,
                    "file_path": file_path,
                    "agent_id": agent_id,
                    "workspace_id": workspace_id,
                    "file_name": file_name,
                },
            )
        _ = PineconeVectorStore.from_documents(
            pages,
            embeddings,
            index_name=index_name,
            namespace=namespace,
        )
        return True
    print("Unsupported file type")
    return False


def delete_embeddings(index_name: str, namespace: str, file_id: str) -> bool:
    """Delete a file and its embeddings from a pinecone index

    Args:
        index_name: The name of the Pinecone index.
        namespace: The namespace of the Pinecone index.
        file_id: The ID of the file to delete.

    Returns:
        True if the embedding removal is successful, False otherwise.

    """
    # Connect to index
    index = pc.Index(index_name)

    # Search for vectors with the given file_id
    # docs_to_delete = index.fetch(ids=[file_id], namespace=namespace)
    docs_to_delete = index.query(
        namespace=namespace,
        top_k=1000,
        include_metadata=True,
        filter={"file_id": file_id},
        vector=[0.0]
        * 1536,  # Dummy vector, this should not be used within filter-only queries
    )

    # Get ids to delete
    ids_to_delete = [match["id"] for match in docs_to_delete["matches"]]

    if not ids_to_delete:
        print(f"No embeddings found for file_id: {file_id}")
        return False

    # Delete the matched vector IDs
    index.delete(ids=ids_to_delete, namespace=namespace)

    return True


def pdf_loader(file_path: str) -> list[Document]:
    """Load the PDF file and embed the contents into the Pinecone index.

    Args:
        file_path: The path of the PDF file.

    Returns:
        A list of Document objects containing the embedded contents of the PDF file.

    """
    loader = PyPDFLoader(file_path)
    return loader.load_and_split()
