# Copyright (c) 2024.
"""Simple class to represent a stream of messages."""

from collections.abc import Iterable
from typing import TypedDict

from anthropic.types import MessageParam
from langchain_core.documents import Document
from openai.types.chat import ChatCompletionMessageParam


class ConversationalStream(TypedDict):

    """Simple class to represent a stream of messages."""

    answer: str
    context: Iterable[Document]


Message = ChatCompletionMessageParam | MessageParam
MessageHistory = dict[int, Message]
