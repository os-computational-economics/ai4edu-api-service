# Copyright (c) 2024.
"""Class for handling files in the S3 storage system"""

import json
import logging
import os
import uuid
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from mypy_boto3_s3.client import S3Client
from redis import Redis
from sqlalchemy.orm import Session

from common.EnvManager import Config as Con
from migrations.models import File, FileValue
from migrations.session import get_db

logger = logging.getLogger(__name__)


class FileStorageHandler:

    """Class for retrieving and storing files"""

    # ! Make these environment variables
    LOCAL_FOLDER: str = "./volume_cache/"
    BUCKET_NAME: str = "ai4edu-storage"
    S3_FOLDER: str = "ai4edu_data/"
    REDIS_CACHE_EXPIRY: int = 60 * 60 * 24  # 24 hours in seconds

    def __init__(self, config: Con) -> None:
        """Initialize the FileStorageHandler

        Args:
            config: Environment configuration object

        """
        self.s3_client: S3Client = boto3.client(  # pyright: ignore[reportUnknownMemberType]
            "s3", region_name="us-east-2", config=Config(signature_version="s3v4"),
        )
        self.db: Session | None = None
        self.redis_client: Redis[str] = Redis(
            host=config["REDIS_ADDRESS"],
            port=6379,
            decode_responses=True,
        )

    def _get_db(self) -> Session:
        if self.db is None:
            self.db = next(get_db())
        return self.db

    @staticmethod
    def _ensure_directory_exists(path: str) -> None:
        """Ensure the directory of the given path exists."""
        # if the path is a directory (ends with '/'), remove the last character
        # TODO: migrate to Pathlib
        directory = path[:-1] if path.endswith("/") else os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def _get_s3_object_name(self, file_id: str, file_ext: str) -> str:
        """Construct the S3 object name based on the file_id and extension.

        Args:
            file_id: The ID of the file.
            file_ext: The extension of the file.

        Returns:
            The S3 object name.

        """
        return os.path.join(self.S3_FOLDER, f"{file_id}{file_ext}")

    def _cache_file_info(self, file_obj: FileValue) -> None:
        """Cache file information in Redis.

        Args:
            file_obj: File object to cache info about

        """
        cache_key = f"file_info:{file_obj.file_id}"
        cache_data = {
            "file_name": file_obj.file_name,
            "file_desc": file_obj.file_desc,
            "file_type": file_obj.file_type,
            "file_ext": file_obj.file_ext,
            "file_status": file_obj.file_status,
            "chunking_separator": file_obj.chunking_separator,
            "created_at": file_obj.created_at.isoformat(),
        }
        _ = self.redis_client.setex(
            cache_key, self.REDIS_CACHE_EXPIRY, json.dumps(cache_data),
        )

    def _get_cached_file_info(self, file_id: str) -> dict[str, Any] | None:  # pyright: ignore[reportExplicitAny]
        """Retrieve cached file information from Redis.

        Args:
            file_id: The ID of the file.

        Returns:
            The cached file information as a dictionary, or None if not found.

        """
        cache_key = f"file_info:{file_id}"
        cached_data = str(self.redis_client.get(cache_key) or "")
        return json.loads(cached_data) if cached_data else None

    def get_file(self, file_id: str) -> str | None:
        """Get the content of a file from the local cache or S3 bucket.

        Args:
            file_id: The ID of the file.

        Returns:
            The content of the file as a string, or None if the file is not found.

        """
        try:
            # Check Redis cache first
            file_info = self._get_cached_file_info(file_id)
            if not file_info:
                # If not in cache, query database
                file_obj: FileValue | None = (
                    self._get_db().query(File).filter(File.file_id == file_id).first()
                )  # pyright: ignore[reportAssignmentType]
                if not file_obj:
                    return None
                # Cache the file info
                self._cache_file_info(file_obj)
                file_info = {
                    "file_name": file_obj.file_name,
                    "file_ext": file_obj.file_ext,
                }

            file_name, file_ext = file_info["file_name"], file_info["file_ext"]

            local_path = os.path.join(self.LOCAL_FOLDER, str(file_id), file_name)
            self._ensure_directory_exists(local_path)
            if not os.path.exists(local_path):
                s3_object_name = self._get_s3_object_name(str(file_id), file_ext)
                _ = self.__download_file(self.BUCKET_NAME, s3_object_name, local_path)

            return local_path
        except FileNotFoundError:
            logger.error(f"File not found: {file_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving file: {e!s}")
            return None

    def put_file(
        self,
        file_obj: bytes,
        file_name: str,
        file_desc: str,
        file_type: str,
        chunking_separator: str,
    ) -> str | None:
        """Store a file locally and upload it to the S3 bucket.

        Args:
            file_obj: A file-like object containing the file data.
            file_name: The original name of the file.
            file_desc: A description of the file.
            file_type: The type of the file.
            chunking_separator: The separator used for chunking the file.

        Returns:
            The file_id of the stored file.

        """
        file_id = uuid.uuid4()
        file_ext = os.path.splitext(file_name)[1]
        try:
            # Store locally
            local_folder = os.path.join(self.LOCAL_FOLDER, str(file_id))
            self._ensure_directory_exists(local_folder + "/")
            local_path = os.path.join(local_folder, file_name)

            with open(local_path, "wb") as local_file:
                _ = local_file.write(file_obj)
        except Exception as e:
            logger.error(f"Error saving file locally: {e!s}")
            return None

        # Upload to S3
        s3_object_name = self._get_s3_object_name(str(file_id), file_ext)
        upload_status = self.__upload_file(
            self.BUCKET_NAME, local_path, s3_object_name, content_type=file_type,
        )

        if upload_status:
            try:
                # Index in SQL database
                new_file: FileValue = File(
                    file_id=file_id,
                    file_name=file_name,
                    file_desc=file_desc,
                    file_type=file_type,
                    file_ext=file_ext,
                    file_status=1,  # Using the default status
                    chunking_separator=chunking_separator,
                )  # pyright: ignore[reportAssignmentType]
                self._get_db().add(new_file)
                self._get_db().commit()

                # Cache file info in Redis
                self._cache_file_info(new_file)

                return str(file_id)
            except Exception as e:
                logger.error(f"Error saving file metadata to database: {e!s}")
                self._get_db().rollback()
                return None
        else:
            logger.error(f"Failed to upload file {file_name} to S3")
            return None

    def get_presigned_url(self, file_id: str, expiration: int = 3600) -> str | None:
        """Generate a presigned URL for a file in the S3 bucket.

        Args:
            file_id: The ID of the file.
            expiration: The expiration time of the URL in seconds.

        Returns:
            The presigned URL, or None if the file is not found.

        """
        try:
            file_info = self._get_cached_file_info(file_id)
            if not file_info:
                file_obj: FileValue | None = (
                    self._get_db().query(File).filter(File.file_id == file_id).first()
                )  # pyright: ignore[reportAssignmentType]
                if not file_obj:
                    return None
                self._cache_file_info(file_obj)
                file_info = {
                    "file_name": file_obj.file_name,
                    "file_ext": file_obj.file_ext,
                }

            file_ext = file_info["file_ext"]
            s3_object_name = self._get_s3_object_name(file_id, file_ext)
            return self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.BUCKET_NAME, "Key": s3_object_name},
                ExpiresIn=expiration,
            )
        except Exception as e:
            # rollback the transaction if an error occurs
            self._get_db().rollback()
            logger.error(f"Error generating presigned URL: {e!s}")
            return None

    def __upload_file(
        self, bucket: str, local_path: str, object_name: str, content_type: str = "",
    ) -> bool:
        """Upload a file to the specified S3 bucket.

        Args:
            bucket: The name of the S3 bucket.
            local_path: The local path of the file to be uploaded.
            object_name: The name of the object in the S3 bucket.
            content_type: The content type of the file (optional).

        Returns:
            True if the file is uploaded successfully, False otherwise.

        """
        try:
            if content_type:
                self.s3_client.upload_file(
                    local_path,
                    bucket,
                    object_name,
                    ExtraArgs={"ContentType": content_type},
                )
            else:
                self.s3_client.upload_file(local_path, bucket, object_name)
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            return False
        return True

    def __download_file(
        self, bucket_name: str, object_name: str, local_path: str,
    ) -> bool:
        """Download a file from the specified S3 bucket.

        Args:
            bucket_name: The name of the S3 bucket.
            object_name: The name of the object in the S3 bucket.
            local_path: The local path where the file will be downloaded.

        Returns:
            True if the file is downloaded successfully, False otherwise.

        """
        self._ensure_directory_exists(local_path)
        try:
            self.s3_client.download_file(bucket_name, object_name, local_path)
        except ClientError as e:
            logger.error(f"Error downloading file from S3: {e}")
            return False
        return True

    def __del__(self) -> None:
        """Close the database connection."""
        if self.db:
            self.db.close()
