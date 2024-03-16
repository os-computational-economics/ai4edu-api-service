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

import redis
from openai import OpenAI
from anthropic import Anthropic

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
load_dotenv(dotenv_path="/run/secrets/ai4edu_secret")
load_dotenv()

# initialize FastAPI app and OpenAI client
app = FastAPI(docs_url=f"{URL_PATHS['current_dev_admin']}/docs", redoc_url=f"{URL_PATHS['current_dev_admin']}/redoc", openapi_url=f"{URL_PATHS['current_dev_admin']}/openapi.json")
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

origins = [
    "http://127.0.0.1:8001",
    "http://localhost:8000",
    "http://localhost:5173",
    "http://localhost:5172",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
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
    ENDPOINTS: /v1/dev/admin, /v1/prod/admin, /v1/dev/user, /v1/prod/user, /
    :param request:
    :return:
    """
    abc = config.get("ABC") or os.getenv("ABC")  # local is prioritized
    if abc is None:
        return {"Hello": "World", "request-path": str(request.url.path)}
    else:
        r = redis.Redis(host='redis-server', port=6379, protocol=3, decode_responses=True)
        r.set('foo', 'bar11111')
        abc = r.get('foo')
        return {"Servers": "Hello-World-" + abc, "request-path": str(request.url.path)}
