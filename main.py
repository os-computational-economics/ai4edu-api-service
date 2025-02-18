# Copyright (c) 2024.
"""Backend service for AI4EDU AI chat services."""

import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from anthropic import Anthropic
from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from redis import Redis
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from sse_starlette.sse import EventSourceResponse
from starlette.responses import FileResponse, JSONResponse, RedirectResponse

from admin.Access import router as AccessRouter  # noqa: N812
from admin.AgentManager import router as AgentRouter  # noqa: N812
from admin.Thread import router as ThreadRouter  # noqa: N812
from admin.Workspace import router as WorkspaceRouter  # noqa: N812
from common.AuthSSO import AuthSSO
from common.DynamicAuth import DynamicAuth
from common.EnvManager import getenv
from common.FileStorageHandler import FileStorageHandler
from common.MessageStorageHandler import MessageStorageHandler
from common.UserAuth import UserAuth
from middleware.authorization import AuthorizationMiddleware, extract_token
from user.ChatStream import ChatStream, ChatStreamModel
from user.Feedback import router as FeedbackRouter  # noqa: N812
from user.GetAgent import router as GetAgentRouter  # noqa: N812
from user.SttApiKey import SttApiKey, SttApiKeyResponse
from user.Threads import new_thread
from user.TtsStream import TtsStream
from utils.response import Response, response

logging.basicConfig(
    level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s",
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

CONFIG = getenv()

# initialize FastAPI app and OpenAI client
app = FastAPI(
    docs_url=f"{URL_PATHS['current_dev_admin']}/docs",
    redoc_url=f"{URL_PATHS['current_dev_admin']}/redoc",
    openapi_url=f"{URL_PATHS['current_dev_admin']}/openapi.json",
)
openai_client = OpenAI(api_key=CONFIG["OPENAI_API_KEY"])
anthropic_client = Anthropic(api_key=CONFIG["ANTHROPIC_API_KEY"])
file_storage = FileStorageHandler(CONFIG=CONFIG)

# Admin AgentRouter
app.include_router(AgentRouter, prefix=f"{URL_PATHS['current_dev_admin']}/agents")
app.include_router(AgentRouter, prefix=f"{URL_PATHS['current_prod_admin']}/agents")

# Admin ThreadRouter
app.include_router(ThreadRouter, prefix=f"{URL_PATHS['current_dev_admin']}/threads")
app.include_router(ThreadRouter, prefix=f"{URL_PATHS['current_prod_admin']}/threads")

# Register GetAgentRouter for user endpoints
# note there is similar functionality in the AgentRouter but I made a different
# version for users so we can seperate the two and maybe add security where users
# can get the full info given to admin users
app.include_router(GetAgentRouter, prefix=f"{URL_PATHS['current_dev_user']}/agent")
app.include_router(GetAgentRouter, prefix=f"{URL_PATHS['current_prod_user']}/agent")

# User Feedback Router
app.include_router(FeedbackRouter, prefix=f"{URL_PATHS['current_dev_user']}/feedback")
app.include_router(FeedbackRouter, prefix=f"{URL_PATHS['current_prod_user']}/feedback")

# Admin AccessRouter
app.include_router(AccessRouter, prefix=f"{URL_PATHS['current_dev_admin']}/access")
app.include_router(AccessRouter, prefix=f"{URL_PATHS['current_prod_admin']}/access")

# Admin WorkspaceRouter
app.include_router(
    WorkspaceRouter, prefix=f"{URL_PATHS['current_dev_admin']}/workspace",
)
app.include_router(
    WorkspaceRouter, prefix=f"{URL_PATHS['current_prod_admin']}/workspace",
)

# system authorization middleware before CORS middleware, so it executes after CORS
app.add_middleware(AuthorizationMiddleware)

origins = [
    "http://127.0.0.1:8001",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:8000",
    "http://localhost:5173",
    "http://localhost:5172",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "https://ai4edu-user-web.vercel.app",
    "https://ai4edu-dashboard.vercel.app",
    "https://chat.ai4edu.io",
    "https://dashboard.ai4edu.io",
    "https://ai4edu-temp-dev.jerryang.org",
]

regex_origins = "https://.*jerryyang666s-projects\\.vercel\\.app"

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
async def sso(ticket: str, came_from: str) -> RedirectResponse | None:
    """ENDPOINT: /user/sso

    Args:
        ticket: a
        came_from: a

    Returns:
        Redirect to login or nothing

    """
    auth = AuthSSO(ticket, came_from, CONFIG=CONFIG)
    return auth.get_user_info()


@app.post(f"{URL_PATHS['current_dev_user']}/stream_chat")
@app.post(f"{URL_PATHS['current_prod_user']}/stream_chat")
async def stream_chat(chat_stream_model: ChatStreamModel) -> EventSourceResponse:
    """ENDPOINT: /user/stream_chat

    Args:
        chat_stream_model: The model containing the chat stream details.

    Returns:
        An EventSourceResponse with the chat stream.

    """
    # auth = DynamicAuth()
    # if not auth.verify_auth_code(chat_stream_model.dynamic_auth_code):
    #     return ChatSingleCallResponse(status="fail", messages=[], thread_id="")
    chat_instance = ChatStream(
        chat_stream_model.provider, openai_client, anthropic_client, CONFIG=CONFIG,
    )
    return chat_instance.stream_chat(chat_stream_model)


def delete_file_after_delay(file_path: Path, delay: float) -> None:
    """Deletes the specified file after a delay.

    Args:
        file_path: The path to the file to delete.
        delay: The delay before deletion, in seconds.

    """
    time.sleep(delay)
    if Path.is_file(file_path):
        Path.unlink(file_path)


@app.get(f"{URL_PATHS['current_dev_user']}/get_tts_file")
@app.get(f"{URL_PATHS['current_prod_user']}/get_tts_file")
async def get_tts_file(
    tts_session_id: str, chunk_id: str, background_tasks: BackgroundTasks,
) -> FileResponse:
    """ENDPOINT: /user/get_tts_file

    serves the TTS audio file for the specified session id and chunk id.

    Args:
        tts_session_id:
        chunk_id:
        background_tasks:

    Raises:
        HTTPException: If the file does not exist

    Returns:
        A FileResponse containing the TTS audio file if it exists, otherwise a 404 error

    """
    file_location = (
        f"{TtsStream.TTS_AUDIO_CACHE_FOLDER}/{tts_session_id}_{chunk_id}.mp3"
    )
    p = Path(file_location)
    if Path.is_file(p):
        # Add the delete_file_after_delay function as a background task
        background_tasks.add_task(
            delete_file_after_delay, p, 60,
        )  # 60 seconds delay
        return FileResponse(path=file_location, media_type="audio/mpeg")
    raise HTTPException(status_code=404, detail="File not found")


@app.get(f"{URL_PATHS['current_dev_user']}/get_temp_stt_auth_code")
@app.get(f"{URL_PATHS['current_prod_user']}/get_temp_stt_auth_code")
def get_temp_stt_auth_code(dynamic_auth_code: str) -> SttApiKeyResponse:
    """ENDPOINT: /user/get_temp_stt_auth_code

    Generates a temporary STT auth code for the user.

    Args:
        dynamic_auth_code: The dynamic auth code provided by the user.

    Returns:
        A SttApiKeyResponse containing the temporary STT auth code if the auth code is
        valid otherwise an error message.

    """
    auth = DynamicAuth(CONFIG=CONFIG)
    if not auth.verify_auth_code(dynamic_auth_code):
        return SttApiKeyResponse(
            status="fail", error_message="Invalid auth code", key="",
        )
    stt_key_instance = SttApiKey(CONFIG=CONFIG)
    api_key, _ = stt_key_instance.generate_key()
    return SttApiKeyResponse(status="success", error_message=None, key=api_key)


@app.get(f"{URL_PATHS['current_dev_user']}/get_new_thread")
@app.get(f"{URL_PATHS['current_prod_user']}/get_new_thread")
def get_new_thread(
    request: Request,
    agent_id: str,
    workspace_id: str,
) -> Response | JSONResponse | None:
    """ENDPOINT: /user/get_new_thread

    Generates a new thread id for the user.

    Returns:
        A new thread

    """
    return new_thread(request, agent_id, workspace_id)


@app.post(f"{URL_PATHS['current_dev_admin']}/upload_file")
@app.post(f"{URL_PATHS['current_prod_admin']}/upload_file")
@app.post(f"{URL_PATHS['current_dev_user']}/upload_file")
@app.post(f"{URL_PATHS['current_prod_user']}/upload_file")
async def upload_file(
    file: UploadFile | None,
    file_desc: str | None = None,
    chunking_separator: str | None = None,
) -> Response | JSONResponse:
    """ENDPOINT: /upload_file

    Args:
        file:
        file_desc:
        chunking_separator:

    Returns:
        A response containing the file id and file name if successful,
        otherwise an error message.

    """
    if file is None:
        return response(success=False, message="No file provided", status_code=400)
    try:
        # Read the file content
        file_content = await file.read()

        # Determine file type (you might want to implement a more sophisticated method)
        file_type = file.content_type or "application/octet-stream"

        # Use FileStorageHandler to store the file
        file_id = file_storage.put_file(
            file_obj=file_content,
            file_name=file.filename or "",
            file_desc=file_desc or "",
            file_type=file_type,
            chunking_separator=chunking_separator or "",
        )

        if file_id is None:
            return response(
                success=False, message="Failed to upload file", status_code=500,
            )
        return response(
            success=True, data={"file_id": file_id, "file_name": file.filename},
        )
    except Exception as e:
        logging.error(f"Failed to upload file: {e!s}")
    return response(success=False, message="unable to upload file", status_code=500)


@app.get(f"{URL_PATHS['current_dev_admin']}/get_presigned_url_for_file")
@app.get(f"{URL_PATHS['current_prod_admin']}/get_presigned_url_for_file")
@app.get(f"{URL_PATHS['current_dev_user']}/get_presigned_url_for_file")
@app.get(f"{URL_PATHS['current_prod_user']}/get_presigned_url_for_file")
async def get_presigned_url_for_file(file_id: str) -> Response | JSONResponse:
    """ENDPOINT: /get_presigned_url_for_file

    Args:
        file_id:

    Returns:
        A response containing the presigned URL if successful,
        otherwise an error message.

    """
    file_id = file_id or ""
    if not file_id:
        return response(success=False, message="No file ID provided", status_code=400)
    url = file_storage.get_presigned_url(file_id)
    if url is None:
        return response(
            success=False, message="Failed to generate presigned URL", status_code=500,
        )
    return response(success=True, data={"url": url})


@app.get(f"{URL_PATHS['current_dev_admin']}/generate_access_token")
@app.get(f"{URL_PATHS['current_prod_admin']}/generate_access_token")
@app.get(f"{URL_PATHS['current_dev_user']}/generate_access_token")
@app.get(f"{URL_PATHS['current_prod_user']}/generate_access_token")
def generate_token(request: Request) -> Response | JSONResponse:
    """ENDPOINT: /generate_access_token

    Generates a temporary STT auth code for the user.

    Args:
        request: the FastAPI Request object.

    Returns:
        Access token if successful, otherwise an error message.

    """
    tokens = extract_token(request.headers.get("Authorization", ""))
    if tokens["refresh_token"] is None:
        return response(
            success=False, message="No refresh token provided", status_code=401,
        )
    auth = UserAuth()
    access_token = auth.gen_access_token(tokens["refresh_token"])
    if access_token:
        return response(success=True, data={"access_token": access_token})
    return response(
        success=False, message="Failed to generate access token", status_code=401,
    )


@app.get(f"{URL_PATHS['current_dev_admin']}/ping")
@app.get(f"{URL_PATHS['current_prod_admin']}/ping")
@app.get(f"{URL_PATHS['current_dev_user']}/ping")
@app.get(f"{URL_PATHS['current_prod_user']}/ping")
async def ping() -> Response | JSONResponse:
    """ENDPOINT: /ping

    Returns:
        A response with "pong"

    """
    return response(success=True, message="pong")


@app.get(f"{URL_PATHS['current_dev_admin']}/ai4edu_testing")
@app.get(f"{URL_PATHS['current_prod_admin']}/ai4edu_testing")
@app.get(f"{URL_PATHS['current_dev_user']}/ai4edu_testing")
@app.get(f"{URL_PATHS['current_prod_user']}/ai4edu_testing")
def read_root(request: Request) -> dict[str, dict[str, str | dict[str, str]] | str]:
    """Please remove (comment out) the app.add_middleware(AuthorizationMiddleware) line

    This endpoint is for testing purposes.
    If you see no errors, then your local environment is set up correctly.
    Accessing this endpoint will from any path will trigger a test of the following:
    1. Redis connection
    2. environment variables
    3. database connection
    4. docker volume access at ./volume_cache
    5. AWS S3 access
    6. AWS DynamoDB access
    ENDPOINTS: /v1/dev/admin, /v1/prod/admin, /v1/dev/user, /v1/prod/user

    Args:
        request: the FastAPI Request object

    Returns:
        Dict of test results

    """
    # test environment variables
    redis_address = CONFIG["REDIS_ADDRESS"]
    # Get the current time
    now = datetime.now(ZoneInfo(CONFIG["TIMEZONE"]))
    # Format the time
    formatted_time = now.strftime("%Y-%m-%d-%H:%M:%S")

    #  test redis connection
    r = Redis(
        host=redis_address,
        port=6379,
        decode_responses=True,
    )
    _ = r.set("foo", "success-" + formatted_time)
    rds = r.get("foo") or "fail"

    # test database connection
    engine = create_engine(CONFIG["DB_URI"])
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version FROM db_version")).fetchone()
        db_result = str(result[0]) if result else "fail"  # pyright: ignore[reportAny]

    # test docker volume access
    try:
        with Path.open(Path("./volume_cache/test.txt"), "w") as f:
            _ = f.write("success-" + formatted_time)
        with Path.open(Path("./volume_cache/test.txt")) as f:
            volume_result = f.read()
    except FileNotFoundError:
        volume_result = "fail"

    # test AWS S3 access
    file_storage = FileStorageHandler(CONFIG=CONFIG)
    # open file and read as bytes
    with Path.open(Path("./volume_cache/test.txt"), "rb") as f:
        file_content = f.read()
        s3_test_put_file_id = file_storage.put_file(
            file_content, "success-" + formatted_time, "desc", "text/plain", "",
        ) or "fail"

    s3_test_get_file_path = "fail"
    if s3_test_put_file_id != "fail":
        s3_test_get_file_path = file_storage.get_file(s3_test_put_file_id) or "fail"

    # test AWS DynamoDB access
    # current timestamp
    test_thread_id = str(uuid.uuid4())
    test_user_id = "rxy216"
    test_role = "test"
    test_content = "test content"
    message = MessageStorageHandler(CONFIG=CONFIG)
    created_at = (
        message.put_message(test_thread_id, test_user_id, test_role, test_content)
        # TODO: create an error if failed instead of continuing with bad data
        or ""
    )
    test_msg_get_content = str(getattr(
        message.get_message(test_thread_id, created_at),
        "content",
        "fail",
    ))
    test_thread_get_content = " ".join(
        i.content for i in message.get_thread(test_thread_id)
    ) or "fail"

    return {
        "sys-info": {
            "REDIS-ENV": redis_address,
            "REDIS-RW": rds,
            "POSTGRES": db_result,
            "VOLUME": volume_result,
            "S3": {
                "File ID": s3_test_put_file_id,
                "File Path": s3_test_get_file_path,
            },
            "DYNAMODB": {
                "Message Content": test_msg_get_content,
                "Thread Content": test_thread_get_content,
            },
        },
        "request-path": request.url.path,
    }
