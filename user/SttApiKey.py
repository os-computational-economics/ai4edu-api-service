# Copyright (c) 2024.
"""Deepgram abstractions"""
from typing import Any, Literal

import requests
from pydantic import BaseModel

from common.EnvManager import Config


class SttApiKeyResponse(BaseModel):

    """Response from Deepgram API for API key generation."""

    status: Literal["success", "fail"]  # "success" or "fail"
    error_message: str | None = None
    key: str


class SttApiKey:

    """SttApiKey: Generate a new API key for Deepgram Speech-to-Text.

    This key will be sent to the user for use in the client-side.
    The only scope is "usage:write".
    """

    def __init__(self, config: Config) -> None:
        """Initialize with the Deepgram API key and project ID."""
        self.DEEPGRAM_API_KEY: str = config["DEEPGRAM_API_KEY"]
        self.DEEPGRAM_PROJECT_ID: str = config["DEEPGRAM_PROJECT_ID"]

    def generate_key(self) -> tuple[str, str]:
        """Generate a new API key for the user.

        Raises:
            ValueError: If the API key generation fails.

        Returns:
            The API key and ID

        """
        url = f"https://api.deepgram.com/v1/projects/{self.DEEPGRAM_PROJECT_ID}/keys"

        payload = {
            "comment": "user_id",
            "scopes": ["usage:write"],
            "tags": ["user_side"],
            "time_to_live_in_seconds": 2000,
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"Token {self.DEEPGRAM_API_KEY}",
        }

        response = requests.post(url, json=payload, headers=headers, timeout=30)

        # load the response content as a dictionary
        response_dict: dict[str, Any] = response.json()  # pyright: ignore[reportExplicitAny]

        # extract the API key from the dictionary
        api_key: str = response_dict.get("key", "")
        api_key_id: str = response_dict.get("api_key_id", "")

        if not api_key or not api_key_id:
            raise ValueError("Failed to generate API key.")

        return api_key, api_key_id
