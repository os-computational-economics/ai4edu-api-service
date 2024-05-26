# Copyright (c) 2024.
# -*-coding:utf-8 -*-
"""
@file: main.py
@author: Jerry(Ruihuang)Yang
@email: rxy216@case.edu
@time: 3/16/24 17:52
"""
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv, dotenv_values
import os
import time
from datetime import datetime
import uuid

import redis
from openai import OpenAI
from anthropic import Anthropic
from sqlalchemy import create_engine
from sqlalchemy.sql import text

from common.DynamicAuth import DynamicAuth
from common.FileStorageHandler import FileStorageHandler
from common.MessageStorageHandler import MessageStorageHandler
from common.AuthSSO import AuthSSO
from common.UserAuth import UserAuth
from utils.response import response
from user.ChatStream import ChatStream, ChatStreamModel, ChatSingleCallResponse
from user.TtsStream import TtsStream
from user.SttApiKey import SttApiKey, SttApiKeyResponse

from user.Threads import new_thread
from user.GetAgent import router as GetAgentRouter

from admin.AgentManager import router as AgentRouter
from admin.Thread import router as ThreadRouter

import logging
from middleware.authorization import AuthorizationMiddleware, extract_token

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:     %(name)s - %(message)s'
)

DEV_PREFIX = "/dev"
PROD_PREFIX = "/prod"

ADMIN_PREFIX = "/admin"
USER_PREFIX = "/user"

CURRENT_VERSION_PREFIX = "/v1"

URL_PATHS = {
    "current_dev_admin": f"{CURRENT_VERSION_PREFIX}{DEV_PREFIX}{ADMIN_PREFIX}",
    "current_dev_user": f"{CURRENT_VERSION_PREFIX}{DEV_PREFIX}{USER_PREFIX}",
    "current_prod_admin": f"{CURRENT_VERSION_PREFIX}{PROD_PREFIX}{ADMIN_PREFIX}",
    "current_prod_user": f"{CURRENT_VERSION_PREFIX}{PROD_PREFIX}{USER_PREFIX}",
}

# try loading from .env file (only when running locally)
try:
    config = dotenv_values(".env")
except FileNotFoundError:
    config = {}
# load secrets from /run/secrets/ (only when running in docker)
load_dotenv(dotenv_path="/run/secrets/ai4edu-secret")
load_dotenv()

# initialize FastAPI app and OpenAI client
app = FastAPI(docs_url=f"{URL_PATHS['current_dev_admin']}/docs", redoc_url=f"{URL_PATHS['current_dev_admin']}/redoc",
              openapi_url=f"{URL_PATHS['current_dev_admin']}/openapi.json")
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Admin AgentRouter
app.include_router(AgentRouter, prefix=f"{URL_PATHS['current_dev_admin']}/agents")
app.include_router(AgentRouter, prefix=f"{URL_PATHS['current_prod_admin']}/agents")

# Admin ThreadRouter
app.include_router(ThreadRouter, prefix=f"{URL_PATHS['current_dev_admin']}/threads")
app.include_router(ThreadRouter, prefix=f"{URL_PATHS['current_prod_admin']}/threads")

# Register GetAgentRouter for user endpoints
# note there is similar functionality in the AgentRouter but I made a different version for users
# so we can seperate the two and maybe add security where users can get the full info given to admin users
app.include_router(GetAgentRouter, prefix=f"{URL_PATHS['current_dev_user']}/agent")
app.include_router(GetAgentRouter, prefix=f"{URL_PATHS['current_prod_user']}/agent")

# system authorization middleware before CORS middleware, so it executes after CORS
app.add_middleware(AuthorizationMiddleware)

origins = [
    "http://127.0.0.1:8001",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:5173",
    "http://localhost:5172",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "https://ai4edu-user-web.vercel.app",
    "https://ai4edu-dashboard.vercel.app",
    "https://chat.ai4edu.io",
    "https://dashboard.ai4edu.io",
]

regex_origins = "https://.*jerryyang666s-projects\.vercel\.app"

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=regex_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(f"{URL_PATHS['current_dev_user']}/sso")
@app.get(f"{URL_PATHS['current_prod_user']}/sso")
async def sso(ticket: str, came_from: str):
    """
    ENDPOINT: /user/sso
    :param ticket:
    :param came_from:
    """
    auth = AuthSSO(ticket, came_from)
    return auth.get_user_info()


@app.post(f"{URL_PATHS['current_dev_user']}/stream_chat")
@app.post(f"{URL_PATHS['current_prod_user']}/stream_chat")
async def stream_chat(chat_stream_model: ChatStreamModel):
    """
    ENDPOINT: /user/stream_chat
    :param chat_stream_model:
    """
    auth = DynamicAuth()
    if not auth.verify_auth_code(chat_stream_model.dynamic_auth_code):
        return ChatSingleCallResponse(status="fail", messages=[], thread_id="")
    chat_instance = ChatStream(chat_stream_model.provider, openai_client, anthropic_client)
    return chat_instance.stream_chat(chat_stream_model)


def delete_file_after_delay(file_path: str, delay: float):
    """
    Deletes the specified file after a delay.
    :param file_path: The path to the file to delete.
    :param delay: The delay before deletion, in seconds.
    """
    time.sleep(delay)
    if os.path.isfile(file_path):
        os.remove(file_path)


@app.get(f"{URL_PATHS['current_dev_user']}/get_tts_file")
@app.get(f"{URL_PATHS['current_prod_user']}/get_tts_file")
async def get_tts_file(tts_session_id: str, chunk_id: str, background_tasks: BackgroundTasks):
    """
    ENDPOINT: /user/get_tts_file
    serves the TTS audio file for the specified session id and chunk id.
    :param tts_session_id:
    :param chunk_id:
    :param background_tasks:
    :return:
    """
    file_location = f"{TtsStream.TTS_AUDIO_CACHE_FOLDER}/{tts_session_id}_{chunk_id}.mp3"
    if os.path.isfile(file_location):
        # Add the delete_file_after_delay function as a background task
        background_tasks.add_task(delete_file_after_delay, file_location, 60)  # 60 seconds delay
        return FileResponse(path=file_location, media_type="audio/mpeg")
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.get(f"{URL_PATHS['current_dev_user']}/get_temp_stt_auth_code")
@app.get(f"{URL_PATHS['current_prod_user']}/get_temp_stt_auth_code")
def get_temp_stt_auth_code(dynamic_auth_code: str):
    """
    ENDPOINT: /user/get_temp_stt_auth_code
    Generates a temporary STT auth code for the user.
    :return:
    """
    auth = DynamicAuth()
    if not auth.verify_auth_code(dynamic_auth_code):
        return SttApiKeyResponse(status="fail", error_message="Invalid auth code", key="")
    stt_key_instance = SttApiKey()
    api_key, _ = stt_key_instance.generate_key()
    return SttApiKeyResponse(status="success", error_message=None, key=api_key)


@app.get(f"{URL_PATHS['current_dev_user']}/get_new_thread")
@app.get(f"{URL_PATHS['current_prod_user']}/get_new_thread")
def get_new_thread(user_id: str, agent_id: str):
    """
    ENDPOINT: /user/get_new_thread
    Generates a new thread id for the user.
    :return:
    """
    return new_thread(user_id, agent_id)


@app.get(f"{URL_PATHS['current_dev_admin']}/generate_access_token")
@app.get(f"{URL_PATHS['current_prod_admin']}/generate_access_token")
@app.get(f"{URL_PATHS['current_dev_user']}/generate_access_token")
@app.get(f"{URL_PATHS['current_prod_user']}/generate_access_token")
def generate_token(request: Request):
    """
    ENDPOINT: /generate_access_token
    Generates a temporary STT auth code for the user.
    :return:
    """
    tokens = extract_token(request.headers.get('Authorization', ''))
    if tokens['refresh_token'] is None:
        return response(success=False, message="No refresh token provided", status_code=401)
    auth = UserAuth()
    access_token = auth.gen_access_token(tokens['refresh_token'])
    if access_token:
        return response(success=True, data={"access_token": access_token})
    else:
        return response(success=False, message="Failed to generate access token", status_code=401)


@app.get(f"{URL_PATHS['current_dev_admin']}/")
@app.get(f"{URL_PATHS['current_prod_admin']}/")
@app.get(f"{URL_PATHS['current_dev_user']}/")
@app.get(f"{URL_PATHS['current_prod_user']}/")
@app.get("/")
def read_root(request: Request):
    """
    Test endpoint. accessing this endpoint will from any path will trigger a test of the following:
    1. Redis connection
    2. environment variables
    3. database connection
    4. docker volume access at ./volume_cache
    5. AWS S3 access
    6. AWS DynamoDB access
    ENDPOINTS: /v1/dev/admin, /v1/prod/admin, /v1/dev/user, /v1/prod/user, /
    :param request:
    :return:
    """
    # test environment variables
    redis_address = config.get("REDIS_ADDRESS") or os.getenv("REDIS_ADDRESS")  # local is prioritized
    if redis_address is None:
        return {"Warning": "ENV VARIABLE NOT CONFIGURED", "request-path": str(request.url.path)}
    else:
        # Get the current time
        now = datetime.now()
        # Format the time
        formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")

        #  test redis connection
        r = redis.Redis(host=redis_address, port=6379, protocol=3, decode_responses=True)
        r.set('foo', 'success-' + formatted_time)
        rds = r.get('foo')

        # test database connection
        engine = create_engine(os.getenv("DB_URI"))
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version FROM db_version"))
            db_result = result.fetchone()[0]

        # test docker volume access
        try:
            with open("./volume_cache/test.txt", "w") as f:
                f.write("success-" + formatted_time)
            with open("./volume_cache/test.txt", "r") as f:
                volume_result = f.read()
        except FileNotFoundError:
            volume_result = "FAILED"

        # test AWS S3 access
        file_storage = FileStorageHandler()
        s3_test = file_storage.put_file("test_dir/test.txt", "success-" + formatted_time)
        s3_test_str = file_storage.get_file("test_dir/test.txt")

        # test AWS DynamoDB access
        # current timestamp
        test_thread_id = str(uuid.uuid4())
        test_user_id = 'rxy216'
        test_role = 'test'
        test_content = 'test content'
        message = MessageStorageHandler()
        created_at = message.put_message(test_thread_id, test_user_id, test_role, test_content)
        test_msg_get_content = message.get_message(test_thread_id, created_at).content
        test_thread_get_content = message.get_thread(test_thread_id)

        return {
            "sys-info": {
                "REDIS-ENV": redis_address,
                "REDIS-RW": rds,
                "POSTGRES": db_result,
                "VOLUME": volume_result,
                "S3": {
                    "Test": s3_test,
                    "Message": s3_test_str
                },
                "DYNAMODB": {
                    "Message Content": test_msg_get_content,
                    "Thread Content": test_thread_get_content
                }
            },
            "request-path": str(request.url.path)
        }
