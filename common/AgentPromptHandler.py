# Copyright (c) 2024.
"""Class for accessing and updating agent prompts in the database."""

import logging

import boto3
from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource, Table
from redis import Redis

from common.EnvManager import Config

logging.basicConfig(level=logging.INFO)


class AgentPromptHandler:
    """Class for accessing and updating agent prompts in the database."""

    DYNAMODB_TABLE_NAME: str = "ai4edu_agent_prompt"

    def __init__(self, config: Config) -> None:
        """Initialize the AgentPromptHandler with the given configuration.

        Args:
            config: The environment configuration

        """
        self.dynamodb: DynamoDBServiceResource = boto3.resource(  # pyright: ignore[reportUnknownMemberType]
            "dynamodb",
            region_name="us-east-2",
            aws_access_key_id=config["AWS_ACCESS_KEY_ID_DYNAMODB"],
            aws_secret_access_key=config["AWS_SECRET_ACCESS_KEY_DYNAMODB"],
        )
        self.table: Table = self.dynamodb.Table(self.DYNAMODB_TABLE_NAME)
        self.redis_client: Redis[str] = Redis(
            host=config["REDIS_ADDRESS"],
            port=6379,
            decode_responses=True,
        )

    def put_agent_prompt(self, agent_id: str, prompt: str) -> bool:
        """Put the agent prompt into the database.

        Args:
            prompt: The prompt of the agent.
            agent_id: The ID of the agent.

        Returns:
            True if the prompt was successfully put into the database, False otherwise.

        """
        try:
            _ = self.table.put_item(Item={"agent_id": agent_id, "prompt": prompt})
            _ = self.__cache_agent_prompt(agent_id, prompt)
            return True
        except Exception as e:
            logging.error(f"Error putting the agent prompt into the database: {e}")
            return False

    def get_agent_prompt(self, agent_id: str) -> str | None:
        """Get the agent prompt from the database.

        Args:
            agent_id: The ID of the agent.

        Returns:
            The prompt of the agent if found, None otherwise.

        """
        cached_prompt = self.__get_cached_agent_prompt(agent_id)
        if cached_prompt:
            logging.info(
                f"Cache hit, getting the agent prompt from the cache. {agent_id}",
            )
            return cached_prompt
        # if cache miss, get the prompt from the database, and cache it
        logging.info(
            f"Cache miss, getting the agent prompt from the database. {agent_id}",
        )
        try:
            response = self.table.query(
                KeyConditionExpression=Key("agent_id").eq(agent_id),
            )
            if response["Items"]:
                prompt = str(response["Items"][0]["prompt"])
                _ = self.__cache_agent_prompt(agent_id, prompt)
                return prompt
            return None
        except Exception as e:
            logging.error(f"Error getting the agent prompt from the database: {e}")
            return None

    def __cache_agent_prompt(self, agent_id: str, prompt: str) -> bool:
        """Cache the agent prompt into redis.

        Args:
            agent_id: The ID of the agent.
            prompt: The prompt of the agent.

        Returns:
            True if successful, False otherwise.

        """
        try:
            _ = self.redis_client.set(f"ap:{agent_id}", prompt)
            return True
        except Exception as e:
            logging.error(f"Error caching the agent prompt into redis: {e}")
            return False

    def __get_cached_agent_prompt(self, agent_id: str) -> str | None:
        """Get the agent prompt from redis.

        Args:
            agent_id: The ID of the agent.

        Returns:
            The prompt of the agent if found, None otherwise.

        """
        try:
            prompt = self.redis_client.get(f"ap:{agent_id}")
            if prompt:
                return str(prompt)
            return None
        except Exception as e:
            logging.error(f"Error getting the agent prompt from redis cache: {e}")
            return None
