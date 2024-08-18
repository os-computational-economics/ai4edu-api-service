# Copyright (c) 2024.
# -*-coding:utf-8 -*-
"""
@file: EmbeddingHandler.py
@author: Jerry(Ruihuang)Yang
@email: rxy216@case.edu
@time: 8/16/24 02:27
"""
import os

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA, ConversationalRetrievalChain
from langchain.retrievers import MergerRetriever
from langchain_pinecone import PineconeVectorStore
from langchain.document_loaders import DirectoryLoader, PyPDFLoader
from pinecone import Pinecone, ServerlessSpec

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
pc = Pinecone(api_key=PINECONE_API_KEY)
embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)


def embed_file(index_name: str, namespace: str, file_path: str, file_id: str, file_name: str, file_type: str, agent_id: str = "NA",
               workspace_id: str = "NA") -> bool:
    """
    Embed the file and put the embeddings into the Pinecone index.
    :param index_name: The name of the Pinecone index.
    :param namespace: The namespace of the Pinecone index.
    :param file_path: The path of the file to be embedded.
    :param file_id: The ID of the file.
    :param file_name: The name of the file.
    :param file_type: The type of the file.
    :param agent_id: The ID of the agent. Optional.
    :param workspace_id: The ID of the workspace. Optional.
    :return: True if the embedding is successful, False otherwise.
    """
    if file_type == "pdf":
        pages = pdf_loader(file_path)
        # add metadata to the pages
        for page in pages:
            if not hasattr(page, 'metadata') or page.metadata is None:
                page.metadata = {}
            page.metadata.update(
                {"file_id": file_id, "file_type": file_type, "file_path": file_path, "agent_id": agent_id,
                 "workspace_id": workspace_id, "file_name": file_name})
        PineconeVectorStore.from_documents(pages, embeddings, index_name=index_name,
                                           namespace=namespace)
        return True
    else:
        print("Unsupported file type")
        return False


def pdf_loader(file_path: str) -> list[Document]:
    """
    Load the PDF file and embed the contents into the Pinecone index.
    :param file_path: The path of the PDF file.
    """
    loader = PyPDFLoader(file_path)
    pages = loader.load_and_split()
    return pages
