# Copyright (c) 2024.
"""Abstractions for various AI models"""

import time
from collections.abc import Iterable, Iterator
from enum import StrEnum
from typing import Any, Literal

from langchain.chains.combine_documents import (
    create_stuff_documents_chain,  # pyright: ignore[reportUnknownVariableType]
)
from langchain.chains.history_aware_retriever import (
    create_history_aware_retriever,  # pyright: ignore[reportUnknownVariableType] Ignore these imports as they are untyped
)
from langchain.chains.retrieval import (
    create_retrieval_chain,  # pyright: ignore[reportUnknownVariableType]
)
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import (
    BaseChatMessageHistory,
    InMemoryChatMessageHistory,
)
from langchain_core.messages import BaseMessage
from langchain_core.messages.ai import AIMessage
from langchain_core.messages.human import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.retrievers import RetrieverLike
from langchain_core.runnables import ConfigurableFieldSpec, Runnable
from langchain_core.runnables.history import (
    MessagesOrDictWithMessages,
    RunnableWithMessageHistory,
)
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import ServerlessSpec
from pinecone.control.pinecone import Pinecone
from pydantic import SecretStr

from common.EnvManager import getenv
from common.Messages import ConversationalStream, MessageHistory

CONFIG = getenv()

OPENAI_API_KEY = CONFIG["OPENAI_API_KEY"]
PINECONE_API_KEY = CONFIG["PINECONE_API_KEY"]
ANTHROPIC_API_KEY = CONFIG["ANTHROPIC_API_KEY"]
XLAB_API_KEY = CONFIG["XLAB_API_KEY"]

# Initialize Pinecone and create an index
pc = Pinecone(api_key=PINECONE_API_KEY)
index_name = "namespace-test"

if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )

embeddings = OpenAIEmbeddings(api_key=SecretStr(OPENAI_API_KEY))
llm = ChatOpenAI(
    temperature=0,
    api_key=SecretStr(OPENAI_API_KEY),
    model="gpt-4o",
    streaming=True,
)
llm2 = ChatAnthropic(
    temperature=0,
    api_key=SecretStr(ANTHROPIC_API_KEY),
    model_name="claude-3-7-sonnet-latest",
    streaming=True,
    timeout=None,
    stop=None,
)
llm3 = ChatOpenAI(
    api_key=SecretStr(XLAB_API_KEY),
    model="/workspace/models/Llama-3.3-70B-Instruct",
    base_url="https://xlab-gpu0.weatherhead.case.edu/openai-compatible-api/v1",
    streaming=True,
)


class Provider(StrEnum):
    """List of providers"""

    openai = "openai"
    anthropic = "anthropic"
    xlab = "xlab"


def get_session_history(
    *,
    thread_id: str,
    history_from_request: MessageHistory,
) -> BaseChatMessageHistory:
    """Get session history from thread_id

    Args:
        thread_id: The ID of the thread to retrieve
        history_from_request: The MessageHistory object containing messages

    Returns:
        BaseChatMessageHistory: The session history

    """
    history: InMemoryChatMessageHistory = ChatMessageHistory()
    for _, message in history_from_request.items():
        if message["role"] == "user":
            # TODO: converted to string here, although the message may contain others
            history.add_message(HumanMessage(str(message["content"])))
        elif message["role"] == "assistant":
            # TODO: converted to string here, although the message may contain others
            # ! Additionally, AIMessages are not required to contain a content key
            history.add_message(
                AIMessage(str(message["content"]) if "content" in message else ""),
            )
    # print the current timestamp in ISO string format
    print(
        f"""Thread ID: {thread_id}, Current Time UTC: {
            time.strftime("%Y-%m-%dT%H:%M:%S")
        }"""
    )
    return history


def chat_stream_with_retrieve(
    thread_id: str,
    question: str,
    retrieval_namespace: str,
    system_prompt: str = "You are a personalized assistant.",
    history_from_request: MessageHistory | None = None,
    llm_for_question_consolidation: Provider = Provider.openai,
    llm_for_answer: Provider = Provider.openai,
) -> (
    Iterable[tuple[Literal["answer"], str]]
    | Iterable[tuple[Literal["source"], dict[str, Any]]]  # pyright: ignore[reportExplicitAny]
):
    """Chat stream with retrieval.

    Args:
        thread_id: thread id of the chat.
        question: the user's latest question.
        retrieval_namespace: the namespace of the Pinecone index for retrieval.
        system_prompt: system prompt for the chat.
        history_from_request: chat history from the request. if None, get from Redis.
        llm_for_question_consolidation: which LLM to use for question consolidation
        llm_for_answer: which LLM to use for answering the question

    Yields:
        Chat messages.

    """
    vectorstore = PineconeVectorStore.from_existing_index(
        index_name,
        embeddings,
        namespace=retrieval_namespace,
    )
    retriever: RetrieverLike = vectorstore.as_retriever()

    # Contextualize question ###
    # This prompt will be used to contextualize the question,
    # making the question for vector search
    contextualize_q_system_prompt = """Given a chat history and the latest user \
    question which might reference context in the chat history, formulate a \
    standalone question which can be understood without the chat history. \
    Do NOT answer the question, just reformulate it if needed and otherwise \
    return it as is."""
    contextualize_q_prompt = ChatPromptTemplate.from_messages(  # pyright: ignore[reportUnknownMemberType]
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ],
    )

    if history_from_request is None:
        history_from_request = {}

    # choose the LLM based on the provider
    if llm_for_question_consolidation == Provider.openai:
        llm_use_1 = llm
    elif llm_for_question_consolidation == Provider.anthropic:
        llm_use_1 = llm2
    elif llm_for_question_consolidation == Provider.xlab:
        llm_use_1 = llm3
    else:
        llm_use_1 = llm

    history_aware_retriever = create_history_aware_retriever(
        llm_use_1,
        retriever,
        contextualize_q_prompt,
    )

    qa_system_prompt = f"""You are a personalized assistant. \
    Use the following pieces of retrieved context to answer the question. \
    If you don't know the answer, just say that you don't know. \
    Keep the answer concise.\
    {system_prompt}\
    {{context}}"""

    qa_prompt = ChatPromptTemplate.from_messages(  # pyright: ignore[reportUnknownMemberType]
        [
            ("system", qa_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ],
    )

    # Choose the LLM based on the provider
    if llm_for_answer == Provider.openai:
        llm_use_2 = llm
    elif llm_for_answer == Provider.anthropic:
        llm_use_2 = llm2
    elif llm_for_answer == Provider.xlab:
        llm_use_2 = llm3
    else:
        llm_use_2 = llm

    question_answer_chain = create_stuff_documents_chain(
        llm_use_2,
        qa_prompt,
    )

    rag_chain: Runnable[
        MessagesOrDictWithMessages,
        MessagesOrDictWithMessages | str | BaseMessage,
    ] = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    conversational_rag_chain = RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
        history_factory_config=[
            ConfigurableFieldSpec(
                id="thread_id",
                annotation=str,
                name="Thread ID",
                description="Unique identifier for the thread.",
                default="",
                is_shared=False,
            ),
            ConfigurableFieldSpec(
                id="history_from_request",
                annotation=dict,
                name="History from Request",
                description="Chat history from the request.",
                default={},
                is_shared=False,
            ),
        ],
    )

    print("Latest question: ", question)

    rag_stream: Iterator[ConversationalStream] = conversational_rag_chain.stream(  # pyright: ignore[reportUnknownMemberType]
        {"input": question},
        config={
            "configurable": {
                "thread_id": thread_id,
                "history_from_request": history_from_request,
            },
        },
    )

    for chunk in rag_stream:
        # ! This portion of code is incredibly hard to typecheck as the .stream() method
        # ! returns a dynamic type. We know this type to be ConversationStream, but
        # ! the.stream() method is still a generic function. Type casting/forcing
        # ! is possible here, but annoying
        chunk: ConversationalStream
        answer = chunk.get("answer")
        if answer:
            yield "answer", answer
            continue
        context = chunk.get("context")
        if context:
            sources = chunk.get("context")
            for doc in sources:
                md: dict[str, Any] = (  # pyright: ignore[reportExplicitAny, reportUnknownMemberType]
                    doc.metadata
                )
                yield "source", md


# Example usage:
# for chunk in chat_stream_with_retrieve("12345",
#     "How to contact the first guy?",
#     system_prompt="You are an assistant for Case Western Reserve University.",
#     history_from_request={
#         0: {"role": "user", "content": "Who is the author of the report?"},
#         1: {"role": "assistant",
#             "content": "The authors of the report are Ruilin Jin and Haoran Yu."}
#     },
#     llm_for_question_consolidation="anthropic",
#     llm_for_answer="anthropic"):
#     print(chunk)
