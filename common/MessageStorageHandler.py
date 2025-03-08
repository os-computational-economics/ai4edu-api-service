# Copyright (c) 2024.
"""Managed the storage of messages in DynamoDB."""

import logging
import time

import boto3
from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource, Table
from pydantic import BaseModel

from common.EnvManager import Config

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


class Message(BaseModel):
    """The message object. created_at will not be passed in when creating the object.

    Args:
        thread_id: The ID of the thread, UUID. Partition key of the table
        created_at: The time when the message is created, unix timestamp in milliseconds
        msg_id: The ID of the message, first 8 characters of the thread_id + sequence
        user_id: The ID of the user who the message belongs to, case ID
        role: The role of message sender, openai or anthropic or human
        content: The content of the message

    """

    thread_id: str
    created_at: str
    msg_id: str
    user_id: str
    role: str
    content: str


class MessageStorageHandler:
    """Handle the storage of messages in DynamoDB."""

    dynamodb_table_name: str = ""

    def __init__(self, config: Config) -> None:
        """Initialize the MessageStorageHandler."""
        self.dynamodb: DynamoDBServiceResource = boto3.resource(  # pyright: ignore[reportUnknownMemberType]
            "dynamodb",
            region_name="us-east-2",
            aws_access_key_id=config["AWS_ACCESS_KEY_ID_DYNAMODB"],
            aws_secret_access_key=config["AWS_SECRET_ACCESS_KEY_DYNAMODB"],
        )
        self.dynamodb_table_name = config["DYNAMODB_NAME"]
        self.table: Table = self.dynamodb.Table(self.dynamodb_table_name)

    def put_message(
        self,
        thread_id: str,
        user_id: str,
        role: str,
        content: str,
    ) -> str | None:
        """Put the message into the database.

        This function will generate created_at field.

        Args:
            thread_id: The ID of the thread.
            user_id: The ID of the user who the message belongs to.
            role: The role of message sender.
            content: The content of the message.

        Returns:
            The ID of the message. If the operation fails, return None.

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
                },
            )
            return msg_id
        except Exception as e:
            print(f"Error putting the message into the database: {e}")
            return None

    def get_message(self, thread_id: str, created_at: str) -> Message | None:
        """Get the message from the database.

        Args:
            created_at: The time when the message is created.
            thread_id: The ID of the thread.

        Returns:
            The message object if found, otherwise None.

        """
        try:
            response = self.table.get_item(
                Key={"thread_id": thread_id, "created_at": created_at},
            )
            item = response["Item"]  # pyright: ignore[reportTypedDictNotRequiredAccess] This is okay because we are in a try-catch
            return Message(**item)  # pyright: ignore[reportArgumentType] Same here
        except Exception as e:
            print(f"Error getting the message from the database: {e}")
            return None

    def get_thread(self, thread_id: str) -> list[Message]:
        """Get all the messages in the thread.

        Args:
            thread_id: The ID of the thread.

        Returns:
            A list of Message objects. If not, return an empty list.

        """
        try:
            response = self.table.query(
                KeyConditionExpression=Key("thread_id").eq(thread_id),
            )
            items = response["Items"]
            return [
                Message(**item)  # pyright: ignore[reportArgumentType] Same here
                for item in items
            ]
        except Exception as e:
            print(f"Error getting the thread from the database: {e}")
            return []
