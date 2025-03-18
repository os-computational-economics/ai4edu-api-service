# Copyright (c) 2024.
"""Tools for handling chat streams"""

import json
import uuid
from collections.abc import Iterator
from typing import Any, Literal

from anthropic._client import Anthropic as AnthropicClient
from openai._client import OpenAI as OpenAIClient
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from common.AgentPromptHandler import AgentPromptHandler
from common.EnvManager import Config
from common.Messages import Message, MessageHistory
from common.MessageStorageHandler import MessageStorageHandler
from user.LangChainHelper import Provider, chat_stream_with_retrieve
from user.TtsStream import TtsStream


class ChatStreamModel(BaseModel):
    """Chat stream parameters."""

    dynamic_auth_code: str
    messages: MessageHistory
    thread_id: str | None = None
    provider: Provider = Provider.openai
    user_id: str
    agent_id: str
    voice: bool
    workspace_id: str


class ChatSingleCallResponse(BaseModel):
    """Response for a single call chat. (unused)"""

    status: Literal["success", "fail"]  # "success" or "fail"
    error_message: str | None = None
    messages: list[str]
    thread_id: str


class ChatStreamResponse(BaseModel):
    """Response for a chat stream. (unused)"""

    status: Literal["success", "fail"]  # "success" or "fail"
    error_message: str | None = None
    messages: list[str]
    thread_id: str


class ChatStream:
    """AI chat with OpenAI/Anthropic, streams responses by server-sent events.

    Using this class requires passing in the full messages history, and the provider
    (openai or anthropic).
    """

    def __init__(
        self,
        requested_provider: Provider,
        openai_client: OpenAIClient,
        anthropic_client: AnthropicClient,
        config: Config,
    ) -> None:
        """Initialize ChatStream with necessary clients and parameters.

        Args:
            requested_provider: The AI provider to use (openai or anthropic).
            openai_client: OpenAI client for OpenAI API.
            anthropic_client: Anthropic client for Anthropic API.
            config: Environment configuration.

        """
        self.retrieval_namespace: str = ""
        "The Pinecone index retrieval namespace"

        self.tts_voice_enabled: bool = False
        "Enables Text to Speech for this chat"

        self.user_id: str = ""
        "The user associated with this chat"

        self.thread_id: str = ""
        "The thread id for this chat"

        self.agent_id: str = ""
        "The LLM agent id for this chat"

        self.requested_provider: Provider = requested_provider
        "The wanted AI provider to use (openai or anthropic)"

        self.openai_client: OpenAIClient = openai_client
        "The OpenAI client for OpenAI API"

        self.anthropic_client: AnthropicClient = anthropic_client
        "The Anthropic client for Anthropic API"

        # generate a TtsStream session id (uuid4)
        self.tts_session_id: str = str(uuid.uuid4())
        "The session id for Deepgram Text to Speech"

        self.tts: TtsStream = TtsStream(self.tts_session_id, config=config)
        "The TTS stream for Deepgram Text to Speech"

        self.message_storage_handler: MessageStorageHandler = MessageStorageHandler(
            config=config,
        )
        "The message storage handler for storing messages for this chat"

        self.CONFIG: Config = config

    def stream_chat(self, chat_stream_model: ChatStreamModel) -> EventSourceResponse:
        """Stream chat messages from OpenAI API.

        Args:
            chat_stream_model: The chat stream parameters.

        Returns:
            A custom Server-Sent event with chat information

        """
        self.thread_id = chat_stream_model.thread_id or ""
        self.user_id = chat_stream_model.user_id
        self.agent_id = chat_stream_model.agent_id
        self.tts_voice_enabled = chat_stream_model.voice
        self.retrieval_namespace = f"{chat_stream_model.workspace_id}-{self.agent_id}"
        # messages = self.__messages_processor(chat_stream_model.messages)
        # put last message in messages into the database (human message)
        last_item = chat_stream_model.messages[len(chat_stream_model.messages) - 1]
        _ = self.message_storage_handler.put_message(
            self.thread_id,
            self.user_id,
            "human",
            # ! Is this meant to be a string?
            # ! What if it is a:
            # ! Iterable[ChatCompletionContentPartTextParam] | Iterable[ChatCompletionContentPartParam] | Iterable[ContentArrayOfContentPart] | Iterable[ContentBlock | TextBlockParam | ImageBlockParam | ToolUseBlockParam | ToolResultBlockParam]
            last_item["content"] or "" if "content" in last_item else "",
        )
        #  get agent prompt
        agent_prompt_handler = AgentPromptHandler(config=self.CONFIG)
        agent_prompt = agent_prompt_handler.get_agent_prompt(self.agent_id)
        return EventSourceResponse(
            self.__chat_generator(chat_stream_model.messages, agent_prompt or ""),
        )

    def __chat_generator(
        self,
        messages: MessageHistory,
        system_prompt: str,
    ) -> Iterator[str]:
        """Chat generator.

        Args:
            messages: All previous messages
            system_prompt: The system prompt for the chat.

        Yields:
            A JSON-formatted string with the chat message

        """
        last_message = messages[len(messages) - 1]

        # Try with the requested provider first, then fallback if needed
        available_providers = [self.requested_provider]
        # Add fallback providers if not already included
        for provider in [Provider.openai, Provider.anthropic]:
            if provider != self.requested_provider:
                available_providers.append(provider)

        last_exception = None
        have_good_provider = False

        for provider in available_providers:  # noqa: PLR1702
            try:
                print(f"Attempting with provider: {provider}")
                stream = chat_stream_with_retrieve(
                    self.thread_id,
                    # ! Assumes users are only able to send text messages
                    str(last_message["content"]) if "content" in last_message else "",
                    self.retrieval_namespace,
                    system_prompt,
                    messages,
                    provider,  # Use current provider in the loop
                    provider,
                )
                # start to stream the response
                response_text = ""
                all_sources: list[dict[str, Any]] = []  # pyright: ignore[reportExplicitAny]
                chunk_id = (
                    -1
                )  # chunk_id starts from 0, -1 means no chunk has been created
                sentence_ender = [".", "?", "!"]
                chunk_buffer = ""
                for text_chunk in stream:
                    if text_chunk[0] == "answer":
                        new_text = text_chunk[1]
                        response_text += new_text
                        if len(chunk_buffer.split()) > 17 + (
                            chunk_id * 12
                        ):  # dynamically adjust the chunk size
                            for ender in (
                                sentence_ender
                            ):  # if the chunk contains a sentence ender
                                if ender in new_text:
                                    chunk_buffer, chunk_id = self.__process_chunking(
                                        ender,
                                        new_text,
                                        chunk_buffer,
                                        chunk_id,
                                    )
                                    break
                            else:  # if the chunk does not contain a sentence ender
                                chunk_buffer += new_text
                        else:  # if the chunk is less than 21 words
                            chunk_buffer += new_text
                        yield json.dumps(
                            {
                                "response": response_text,
                                "source": all_sources,
                                "tts_session_id": self.tts_session_id,
                                "tts_max_chunk_id": chunk_id,
                            },
                        )
                    elif text_chunk[0] == "source":
                        source_text = text_chunk[1]
                        all_sources.append(source_text)
                        yield json.dumps(
                            {
                                "response": response_text,
                                "source": all_sources,
                                "tts_session_id": self.tts_session_id,
                                "tts_max_chunk_id": chunk_id,
                            },
                        )
                # put the finished response into the database (AI message)
                msg_id = self.message_storage_handler.put_message(
                    self.thread_id,
                    self.user_id,
                    provider,
                    response_text,
                )
                print(
                    "Latest response:",
                    response_text,
                    "msg_id:",
                    msg_id,
                    "provider:",
                    provider,
                )
                # Process any remaining text in the chunk_buffer after the stream has finished
                if chunk_buffer:
                    chunk_id += 1
                    if self.tts_voice_enabled:
                        self.tts.stream_tts(chunk_buffer, str(chunk_id))
                    yield json.dumps(
                        {
                            "response": response_text,
                            "source": all_sources,
                            "tts_session_id": self.tts_session_id,
                            "tts_max_chunk_id": chunk_id,
                            "msg_id": msg_id,
                        },
                    )
                yield json.dumps(
                    {
                        "response": response_text,
                        "source": all_sources,
                        "tts_session_id": self.tts_session_id,
                        "tts_max_chunk_id": chunk_id,
                        "msg_id": msg_id,
                    },
                )
                # If we are here, it means the provider worked, no need to try others
                have_good_provider = True
                break
            except Exception as e:
                print(f"Provider {provider} failed with error: {str(e)}")
                last_exception = e
                continue

        if not have_good_provider:
            # All providers failed, yield an error message
            error_message = f"All providers failed. Last error: {str(last_exception)}"
            print(error_message)
            yield json.dumps(
                {
                    "response": "I'm sorry, I'm having trouble connecting right now. Please try again later.",
                    "source": [],
                    "tts_session_id": self.tts_session_id,
                    "tts_max_chunk_id": -1,
                }
            )
            return

    def __process_chunking(
        self,
        sentence_ender: str,
        new_text: str,
        chunk_buffer: str,
        chunk_id: int,
    ) -> tuple[str, int]:
        """Process the chunking.

        Args:
            sentence_ender: The sentence ender.
            new_text: The new text.
            chunk_buffer: The current chunk buffer.
            chunk_id: The current chunk id.

        Returns:
            The updated chunk buffer and chunk id.

        """
        chunk_id += 1
        new_text_split = new_text.split(sentence_ender)
        chunk_buffer += new_text_split[0] + sentence_ender
        if self.tts_voice_enabled:
            self.tts.stream_tts(chunk_buffer, str(chunk_id))
        chunk_buffer = sentence_ender.join(new_text_split[1:])
        return chunk_buffer, chunk_id

    def __messages_processor(  # pyright: ignore[reportUnusedFunction]
        self,
        messages: MessageHistory,
    ) -> list[Message]:
        """Process the message.

        Args:
            messages: All previous messages

        Returns:
            The processed messages.

        """
        #  get agent prompt
        agent_prompt_handler = AgentPromptHandler(config=self.CONFIG)
        agent_prompt = agent_prompt_handler.get_agent_prompt(self.agent_id)
        messages_list: list[Message] = []
        if agent_prompt:
            messages_list = [{"role": "system", "content": agent_prompt}]
        else:
            messages_list = [
                {
                    "role": "system",
                    "content": "You are a teaching assistant for the Computational \
                        Economics Course. Make sure you sound like someone talking, \
                        not writing. Use contractions, and try to be conversational. \
                        You should not say very long paragraphs. As someone who is \
                        talking, you should be giving short, quick messages. No long \
                        paragraphs, No long paragraphs, please.",
                },
            ]
        for key in sorted(messages.keys()):
            messages_list.append(messages[key])
        return messages_list
