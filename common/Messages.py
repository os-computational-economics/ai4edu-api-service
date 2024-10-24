from typing import TypedDict
from collections.abc import Iterable

from anthropic.types import MessageParam
from langchain_core.documents import Document
from openai.types.chat import ChatCompletionMessageParam


class ConversationalStream(TypedDict):
    answer: str
    context: Iterable[Document]


Message = ChatCompletionMessageParam | MessageParam
MessageHistory = dict[int, Message]
