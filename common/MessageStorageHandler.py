# Copyright (c) 2024.
# -*-coding:utf-8 -*-
"""
@file: MessageStorageHandler.py
@author: Jerry(Ruihuang)Yang
@email: rxy216@case.edu
@time: 4/10/24 23:26
"""
import boto3
from boto3.dynamodb.conditions import Key
from pydantic import BaseModel
import logging
import os
import time

logging.basicConfig(level=logging.INFO)


class Message(BaseModel):
    """
    The message object. created_at will not be passed in when creating the object.
    thread_id: The ID of the thread, UUID. Partition key of the table
    created_at: The time when the message is created, unix timestamp in milliseconds. Sort key of the table
    msg_id: The ID of the message, first 8 characters of the thread_id + sequence number starting from 0
    user_id: The ID of the user who the message belongs to, case ID
    role: The role of message sender, openai or anthropic or human
    content: The content of the message
    """

    thread_id: str  # The ID of the thread, UUID. Partition key of the table
    created_at: str  # The time when the message is created, unix timestamp in milliseconds. Sort key of the table
    msg_id: str  # The ID of the message, first 8 characters of the thread_id + # +created_at
    user_id: str  # The ID of the user who the message belongs to, case ID
    role: str  # The role of message sender, openai or anthropic or human
    content: str  # The content of the message


class MessageStorageHandler:
    DYNAMODB_TABLE_NAME = "ai4edu_chat_msg_prod" if os.getenv("POSTGRES_DB") == "ai4edu_prod" else "ai4edu_chat_msg_dev"

    def __init__(self):
        self.dynamodb = boto3.resource(  # pyright: ignore[reportUnknownMemberType]
            "dynamodb",
            region_name="us-east-2",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID_DYNAMODB"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY_DYNAMODB"),
        )
        self.table = self.dynamodb.Table(self.DYNAMODB_TABLE_NAME)

    def put_message(
        self, thread_id: str, user_id: str, role: str, content: str
    ) -> str | None:
        """
        Put the message into the database. This function will generate the created_at field.
        :param thread_id: The ID of the thread.
        :param user_id: The ID of the user who the message belongs to.
        :param role: The role of message sender.
        :param content: The content of the message.
        :return: The ID of the message. If the operation fails, return None.
        """
        try:
            created_at = str(int(time.time() * 1000))  # unix timestamp in milliseconds
            msg_id = thread_id[:8] + "#" + created_at
            _ = self.table.put_item(
                Item={
                    "thread_id": thread_id,
                    "created_at": created_at,
                    "msg_id": msg_id,
                    "user_id": user_id,
                    "role": role,
                    "content": content,
                }
            )
            return msg_id
        except Exception as e:
            print(f"Error putting the message into the database: {e}")
            return None

    def get_message(self, thread_id: str, created_at: str) -> Message | None:
        """
        Get the message from the database.
        :param created_at: The time when the message is created.
        :param thread_id: The ID of the thread.
        :return:
        """
        try:
            response = self.table.get_item(
                Key={"thread_id": thread_id, "created_at": created_at}
            )
            item = response[
                "Item"
            ]  # pyright: ignore[reportTypedDictNotRequiredAccess] This is okay because we are in a try-catch
            return Message(**item)  # pyright: ignore[reportArgumentType] Same here
        except Exception as e:
            print(f"Error getting the message from the database: {e}")
            return None

    def get_thread(self, thread_id: str) -> list[Message]:
        """
        Get all the messages in the thread.
        :param thread_id: The ID of the thread.
        :return:
        """
        try:
            response = self.table.query(
                KeyConditionExpression=Key("thread_id").eq(thread_id)
            )
            items = response["Items"]
            return [
                Message(**item)  # pyright: ignore[reportArgumentType] Same here
                for item in items
            ]
        except Exception as e:
            print(f"Error getting the thread from the database: {e}")
            return []
