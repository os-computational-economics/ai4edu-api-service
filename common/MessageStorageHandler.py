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

logging.basicConfig(level=logging.INFO)


class Message(BaseModel):
    thread_id: str
    msg_id: str
    created_at: str
    user_id: str
    role: str
    content: str


class MessageStorageHandler:
    DYNAMODB_TABLE_NAME = "ai4edu_chat_msg"

    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-2', aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID_DYNAMODB"),
                                       aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY_DYNAMODB"))
        self.table = self.dynamodb.Table(self.DYNAMODB_TABLE_NAME)

    def put_message(self, message: Message) -> bool:
        """
        Put the message into the database.
        :param message: The message to be put.
        """
        try:
            self.table.put_item(
                Item={
                    'thread_id': message.thread_id,
                    'msg_id': message.msg_id,
                    'created_at': message.created_at,
                    'user_id': message.user_id,
                    'role': message.role,
                    'content': message.content
                }
            )
            return True
        except Exception as e:
            print(f"Error putting the message into the database: {e}")
            return False

    def get_message(self, thread_id: str, msg_id: str) -> Message or None:
        """
        Get the message from the database.
        :param thread_id: The ID of the thread.
        :param msg_id: The ID of the message.
        :return:
        """
        try:
            response = self.table.get_item(
                Key={
                    'thread_id': thread_id,
                    'msg_id': msg_id
                }
            )
            item = response['Item']
            return Message(**item)
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
                KeyConditionExpression=Key('thread_id').eq(thread_id)
            )
            items = response['Items']
            return [Message(**item) for item in items]
        except Exception as e:
            print(f"Error getting the thread from the database: {e}")
            return []
