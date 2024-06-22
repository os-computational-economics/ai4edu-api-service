# Copyright (c) 2024.
# -*-coding:utf-8 -*-
"""
@file: FileStorageHandler.py
@author: Jerry(Ruihuang)Yang
@email: rxy216@case.edu
@time: 3/22/24 21:05
"""
import os
import json
from typing import Any, Optional
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import uuid
import logging
import redis
from sqlalchemy.orm import Session
from migrations.session import get_db
from migrations.models import File

logger = logging.getLogger(__name__)


class FileStorageHandler:
    LOCAL_FOLDER = "./volume_cache/"
    BUCKET_NAME = "bucket-57h03x"
    S3_FOLDER = "ai4edu_data/"
    REDIS_CACHE_EXPIRY = 60 * 60 * 24  # 24 hours in seconds

    def __init__(self):
        load_dotenv()
        self.s3_client = boto3.client('s3')
        self.db: Optional[Session] = None
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_ADDRESS"),
            port=6379,
            protocol=3,
            decode_responses=True
        )

    def _get_db(self) -> Session:
        if self.db is None:
            self.db = next(get_db())
        return self.db

    @staticmethod
    def _ensure_directory_exists(path: str) -> None:
        """Ensure the directory of the given path exists."""
        # if the path is a directory (ends with '/'), remove the last character
        if path.endswith('/'):
            directory = path[:-1]
        else:
            directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def _get_s3_object_name(self, file_id: str, file_ext: str) -> str:
        """Construct the S3 object name based on the file_id and extension."""
        return os.path.join(self.S3_FOLDER, f"{file_id}{file_ext}")

    def _cache_file_info(self, file_obj: File) -> None:
        """Cache file information in Redis."""
        cache_key = f"file_info:{file_obj.file_id}"
        cache_data = {
            "file_name": file_obj.file_name,
            "file_desc": file_obj.file_desc,
            "file_type": file_obj.file_type,
            "file_ext": file_obj.file_ext,
            "file_status": file_obj.file_status,
            "chunking_separator": file_obj.chunking_separator,
            "created_at": file_obj.created_at.isoformat()
        }
        self.redis_client.setex(cache_key, self.REDIS_CACHE_EXPIRY, json.dumps(cache_data))

    def _get_cached_file_info(self, file_id: str) -> Optional[dict]:
        """Retrieve cached file information from Redis."""
        cache_key = f"file_info:{file_id}"
        cached_data = self.redis_client.get(cache_key)
        return json.loads(str(cached_data)) if cached_data else None

    def get_file(self, file_id: str) -> Any:
        """
        Get the content of a file from the local cache or S3 bucket.
        :param file_id: The ID of the file.
        :return: The local path of the file, or None if the file is not found.
        """
        try:
            # Check Redis cache first
            file_info = self._get_cached_file_info(file_id)
            if not file_info:
                # If not in cache, query database
                file_obj = self._get_db().query(File).filter(File.file_id == file_id).first()
                if not file_obj:
                    return None
                # Cache the file info
                self._cache_file_info(file_obj)
                file_info = {
                    "file_name": file_obj.file_name,
                    "file_ext": file_obj.file_ext
                }

            file_name, file_ext = file_info["file_name"], file_info["file_ext"]

            local_path = os.path.join(self.LOCAL_FOLDER, str(file_id), file_name)
            self._ensure_directory_exists(local_path)
            if not os.path.exists(local_path):
                s3_object_name = self._get_s3_object_name(str(file_id), file_ext)
                self.__download_file(self.BUCKET_NAME, s3_object_name, local_path)

            return local_path
        except FileNotFoundError:
            logger.error(f"File not found: {file_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving file: {str(e)}")
            return None

    def put_file(self, file_obj: bytes, file_name: str, file_desc: str, file_type: str, chunking_separator: str) -> \
            Optional[str]:
        """
        Store a file locally and upload it to the S3 bucket.
        :param file_obj: A file-like object containing the file data.
        :param file_name: The original name of the file.
        :param file_desc: A description of the file.
        :param file_type: The type of the file.
        :param chunking_separator: The separator used for chunking the file.
        :return: The file_id of the stored file.
        """
        file_id = uuid.uuid4()
        file_ext = os.path.splitext(file_name)[1]
        try:
            # Store locally
            local_folder = os.path.join(self.LOCAL_FOLDER, str(file_id))
            self._ensure_directory_exists(local_folder + "/")
            local_path = os.path.join(local_folder, file_name)

            with open(local_path, 'wb') as local_file:
                local_file.write(file_obj)
        except Exception as e:
            logger.error(f"Error saving file locally: {str(e)}")
            return None

        # Upload to S3
        s3_object_name = self._get_s3_object_name(str(file_id), file_ext)
        upload_status = self.__upload_file(self.BUCKET_NAME, local_path, s3_object_name)

        if upload_status:
            try:
                # Index in SQL database
                new_file = File(
                    file_id=file_id,
                    file_name=file_name,
                    file_desc=file_desc,
                    file_type=file_type,
                    file_ext=file_ext,
                    file_status=1,  # Using the default status
                    chunking_separator=chunking_separator
                )
                self._get_db().add(new_file)
                self._get_db().commit()

                # Cache file info in Redis
                self._cache_file_info(new_file)

                return str(file_id)
            except Exception as e:
                logger.error(f"Error saving file metadata to database: {str(e)}")
                return None
        else:
            logger.error(f"Failed to upload file {file_name} to S3")
            return None

    def __upload_file(self, bucket: str, local_path: str, object_name: str) -> bool:
        try:
            self.s3_client.upload_file(local_path, bucket, object_name)
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            return False
        return True

    def __download_file(self, bucket_name: str, object_name: str, local_path: str) -> bool:
        self._ensure_directory_exists(local_path)
        try:
            self.s3_client.download_file(bucket_name, object_name, local_path)
        except ClientError as e:
            logger.error(f"Error downloading file from S3: {e}")
            return False
        return True

    def __del__(self):
        if self.db:
            self.db.close()