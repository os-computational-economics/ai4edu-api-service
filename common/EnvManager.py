# Copyright (c) 2024.
"""Methods for standardizing configuration management."""

from os import getenv as ge
from typing import Literal, get_args

from dotenv import load_dotenv

ConfigKeys = Literal[
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "XLAB_API_KEY",
    "PINECONE_API_KEY",
    "DEEPGRAM_API_KEY",
    "DEEPGRAM_PROJECT_ID",
    "JWT_PRIVATE_KEY",
    "JWT_PUBLIC_KEY",
    "REDIS_ADDRESS",
    "DB_URI",
    "AWS_ACCESS_KEY_ID_DYNAMODB",
    "AWS_SECRET_ACCESS_KEY_DYNAMODB",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "DOMAIN",
    "TIMEZONE",
    "DYNAMODB_NAME",
    "PINECONE_OLD",
    "PINECONE_INDEX",
]

VARS: list[ConfigKeys] = list(get_args(ConfigKeys))

Config = dict[ConfigKeys, str]

# TODO: Add a default environment configuration here so that
# TODO: things will not catastropically fail


@staticmethod
def getenv() -> Config:
    """Load environment variables into an object

    Raises:
        ValueError: If an environment variable is missing

    Returns:
        A dictionary containing environment variables

    """
    _ = load_dotenv(".env")
    _ = load_dotenv(dotenv_path="/run/secrets/ai4edu-secret")
    _ = load_dotenv()
    config: Config = {}
    for var in VARS:
        val = ge(var)
        if not val:
            raise ValueError(f"Missing environment variable: {var}")
        config[var] = val
    return config
