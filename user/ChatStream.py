# Copyright (c) 2024.
"""@file: ChatStream.py
@author: Jerry(Ruihuang)Yang
@email: rxy216@case.edu
@time: 2/29/24 15:14
"""
import json
import uuid
from typing import Any

from anthropic._client import Anthropic as AnthropicClient
from openai._client import OpenAI as OpenAIClient
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from common.AgentPromptHandler import AgentPromptHandler
from common.EnvManager import Config
from common.Messages import Message, MessageHistory
from common.MessageStorageHandler import MessageStorageHandler
from user.LangChainHelper import chat_stream_with_retrieve
from user.TtsStream import TtsStream


class ChatStreamModel(BaseModel):
    dynamic_auth_code: str
    messages: MessageHistory
    thread_id: str | None = None
    provider: str = "openai"
    user_id: str
    agent_id: str
    voice: bool
    workspace_id: str


class ChatSingleCallResponse(BaseModel):
    status: str  # "success" or "fail"
    error_message: str | None = None
    messages: list[str]
    thread_id: str


class ChatStreamResponse(BaseModel):
    status: str  # "success" or "fail"
    error_message: str | None = None
    messages: list[str]
    thread_id: str


class ChatStream:

    """ChatStream: AI chat with OpenAI/Anthropic, streams the output via server-sent events.
    Using this class requires passing in the full messages history, and the provider (openai or anthropic).
    """

    def __init__(
        self,
        requested_provider: str,
        openai_client: OpenAIClient,
        anthropic_client: AnthropicClient,
        CONFIG: Config,
    ):
        """Initialize ChatStream with necessary clients and parameters.
        :param requested_provider: The AI provider to use (openai or anthropic).
        :param openai_client: OpenAI client for OpenAI API.
        :param anthropic_client: Anthropic client for Anthropic API.
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

        self.requested_provider: str = requested_provider
        "The wanted AI provider to use (openai or anthropic)"

        self.openai_client: OpenAIClient = openai_client
        "The OpenAI client for OpenAI API"

        self.anthropic_client: AnthropicClient = anthropic_client
        "The Anthropic client for Anthropic API"

        # generate a TtsStream session id (uuid4)
        self.tts_session_id: str = str(uuid.uuid4())
        "The session id for Deepgram Text to Speech"

        self.tts: TtsStream = TtsStream(self.tts_session_id, CONFIG=CONFIG)
        "The TTS stream for Deepgram Text to Speech"

        self.message_storage_handler: MessageStorageHandler = MessageStorageHandler(config=CONFIG)
        "The message storage handler for storing messages for this chat"

        self.CONFIG: Config = CONFIG

    def stream_chat(self, chat_stream_model: ChatStreamModel):
        """Stream chat messages from OpenAI API.
        :return: A custom Server-Sent event with chat information
        """
        self.thread_id = chat_stream_model.thread_id or ""
        self.user_id = chat_stream_model.user_id
        self.agent_id = chat_stream_model.agent_id
        self.tts_voice_enabled = chat_stream_model.voice
        self.retrieval_namespace = f"{chat_stream_model.workspace_id}-{self.agent_id}"
        # messages = self.__messages_processor(chat_stream_model.messages)
        # put last message in messages into the database (human message)
        lastItem = chat_stream_model.messages[len(chat_stream_model.messages) - 1]
        _ = self.message_storage_handler.put_message(
            self.thread_id,
            self.user_id,
            "human",
            # ! Is this meant to be a string?
            # ! What if it is a:
            # ! Iterable[ChatCompletionContentPartTextParam] | Iterable[ChatCompletionContentPartParam] | Iterable[ContentArrayOfContentPart] | Iterable[ContentBlock | TextBlockParam | ImageBlockParam | ToolUseBlockParam | ToolResultBlockParam]
            lastItem["content"] or "" if "content" in lastItem else "",
        )
        #  get agent prompt
        agent_prompt_handler = AgentPromptHandler(config=self.CONFIG)
        agent_prompt = agent_prompt_handler.get_agent_prompt(self.agent_id)
        return EventSourceResponse(
            self.__chat_generator(chat_stream_model.messages, agent_prompt or ""),
        )

    def __chat_generator(self, messages: MessageHistory, system_prompt: str):
        """Chat generator.
        :param messages: All previous messages
        :return:
        """
        print(f"Using {self.requested_provider}")
        lastMessage = messages[len(messages) - 1]
        stream = chat_stream_with_retrieve(
            self.thread_id,
            # ! Assumes users are only able to send text messages
            str(lastMessage["content"]) if "content" in lastMessage else "",
            self.retrieval_namespace,
            system_prompt,
            messages,
            self.requested_provider,
            self.requested_provider,
        )
        response_text = ""
        all_sources: list[dict[str, Any]] = []
        chunk_id = -1  # chunk_id starts from 0, -1 means no chunk has been created
        sentence_ender = [".", "?", "!"]
        chunk_buffer = ""
        for text_chunk in stream:
            if text_chunk[0] == "answer":
                new_text = text_chunk[1]
                response_text += new_text
                if len(chunk_buffer.split()) > 17 + (
                    chunk_id * 12
                ):  # dynamically adjust the chunk size
                    for (
                        ender
                    ) in sentence_ender:  # if the chunk contains a sentence ender
                        if ender in new_text:
                            chunk_buffer, chunk_id = self.__process_chunking(
                                ender, new_text, chunk_buffer, chunk_id,
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
            self.thread_id, self.user_id, self.requested_provider, response_text,
        )
        print("Latest response:", response_text, "msg_id:", msg_id)
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

    def __openai_chat_generator(  # pyright: ignore[reportUnusedFunction]
        self, messages: list[ChatCompletionMessageParam],
    ):
        """OpenAI chat generator.
        :param messages:
        :return:
        """
        with self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            stream=True,
        ) as stream:
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    new_text = chunk.choices[0].delta.content
                    yield new_text

    def __anthropic_chat_generator(  # pyright: ignore[reportUnusedFunction]
        self, messages: list[Message],
    ):
        """Anthropic chat generator.
        :param messages:
        :return:
        """
        system_message_content = ""
        system_message = messages.pop(0)
        if system_message["role"] == "system":
            system_message_content = system_message["content"]
        [
            m.update({"content": str(m["content"] if "content" in m else "")})
            for m in messages
        ]
        with self.anthropic_client.messages.stream(
            system=system_message_content,
            max_tokens=2048,
            messages=messages,  # pyright: ignore[reportArgumentType]
            model="claude-3-sonnet-20240229",
        ) as stream:
            for text in stream.text_stream:
                if text != "":
                    yield text

    def __process_chunking(
        self, sentence_ender: str, new_text: str, chunk_buffer: str, chunk_id: int,
    ):
        """Process the chunking.
        :param sentence_ender:
        :param new_text:
        :param chunk_buffer:
        :param chunk_id:
        :return:
        """
        chunk_id += 1
        new_text_split = new_text.split(sentence_ender)
        chunk_buffer += new_text_split[0] + sentence_ender
        if self.tts_voice_enabled:
            self.tts.stream_tts(chunk_buffer, str(chunk_id))
        chunk_buffer = sentence_ender.join(new_text_split[1:])
        return chunk_buffer, chunk_id

    def __messages_processor(  # pyright: ignore[reportUnusedFunction]
        self, messages: MessageHistory,
    ):
        """Process the message.
        :param messages: {0: {"role": "user", "content": "Hello, how are you?"}, 1: {"role": "assistant", "content": "I am fine, thank you."}}
        :return:
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
                    "content": "You are a teaching assistant for the Computational Economics Course. Make sure you sound like someone talking, not writing. Use contractions, and try to be conversational. You should not say very long paragraphs. As someone who is talking, you should be giving short, quick messages. No long paragraphs, No long paragraphs, please.",
                },
            ]
        for key in sorted(messages.keys()):
            messages_list.append(messages[key])
        return messages_list
