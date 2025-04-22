# Copyright (c) 2024.
"""Class for accessing and updating workspace prompts in the database."""

import logging

from redis import Redis
from sqlalchemy.orm import Session

from common.EnvManager import Config
from migrations.models import Workspace
from migrations.session import get_db

logging.basicConfig(level=logging.INFO)


class WorkspacePromptHandler:
    """Class for accessing and updating workspace prompts in the database."""

    def __init__(self, config: Config) -> None:
        """Initialize the WorkspacePromptHandler with the given configuration.

        Args:
            config: The environment configuration

        """
        self.db: Session | None = None
        self.redis_client: Redis[str] = Redis(
            host=config["REDIS_ADDRESS"],
            port=6379,
            decode_responses=True,
        )

    def _get_db(self) -> Session:
        """Get a database session.

        Returns:
            A database session.

        """
        if self.db is None:
            self.db = next(get_db())
        return self.db

    def cache_workspace_prompt(self, workspace_id: str, prompt: str) -> bool:
        """Cache the workspace prompt into redis.

        Args:
            workspace_id: The ID of the workspace.
            prompt: The prompt of the workspace.

        Returns:
            True if successful, False otherwise.

        """
        try:
            _ = self.redis_client.set(f"wp:{workspace_id}", prompt)
            return True
        except Exception as e:
            logging.error(f"Error caching the workspace prompt into redis: {e}")
            return False

    def get_cached_workspace_prompt(self, workspace_id: str) -> str:
        """Get the workspace prompt from redis or database if not in cache.

        Args:
            workspace_id: The ID of the workspace.

        Returns:
            The prompt of the workspace if found, otherwise an empty string.
            Because the prompt is not mandatory, it returns an empty string if not found

        """
        try:
            # First try to get from Redis cache
            prompt = self.redis_client.get(f"wp:{workspace_id}")
            if prompt:
                logging.info(f"Cache hit for workspace prompt {workspace_id}")
                return str(prompt)

            # If not in cache, get from database
            logging.info(
                f"Cache miss for workspace prompt {workspace_id}, getting from database"
            )
            try:
                workspace = (
                    self._get_db()
                    .query(Workspace)
                    .filter(Workspace.workspace_id == workspace_id)
                    .first()
                )

                if workspace and workspace.workspace_prompt is not None:
                    # Cache the result for future requests
                    prompt_str = str(workspace.workspace_prompt)
                    _ = self.cache_workspace_prompt(workspace_id, prompt_str)
                    return prompt_str
                return ""

            except Exception as db_error:
                logging.error(
                    f"Error getting workspace prompt from database: {db_error}"
                )
                return ""

        except Exception as e:
            logging.error(f"Error getting the workspace prompt from redis cache: {e}")
            return ""

    def __del__(self) -> None:
        """Close the database connection when the object is destroyed."""
        if self.db:
            self.db.close()
