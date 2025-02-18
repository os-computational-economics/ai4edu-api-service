# Copyright (c) 2024.
"""Class for managing user authentication and authorization and multi-device support"""

import logging
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from common.EnvManager import Config
from migrations.models import RefreshToken, RefreshTokenValue, User, UserValue
from migrations.session import get_db
from utils.token_utils import jwt_generator


class UserAuth:
    """Manages user authentication and authorization and multi-device support"""

    def __init__(self, config: Config) -> None:
        """Initialize UserAuth object"""
        self.db: Session | None = None
        self.config: Config = config

    def user_login(self, student_id: str, user_info: dict[str, str]) -> int | bool:
        """Login the user when sso authentication is successful

        Args:
            student_id: school specific student id
            user_info: user info from sso

        Returns:
            user_id if login successful, False otherwise

        """
        if self.db is None:
            self.db = next(get_db())
        try:
            user_db: UserValue | None = (
                self.db.query(User).filter(User.email == user_info["mail"]).first()
            )  # pyright: ignore[reportAssignmentType]
            if user_db:
                # if user already exists, update last login time
                user_db.last_login = datetime.now(tz=ZoneInfo(self.config["TIMEZONE"]))
            else:
                # if user does not exist, create a new user
                new_user: UserValue = User(
                    first_name=user_info["givenName"],
                    last_name=user_info["sn"],
                    email=user_info["mail"],
                    student_id=student_id,
                    workspace_role={},
                    system_admin=False,
                    # default role is student
                    school_id=0,
                    last_login=datetime.now(tz=ZoneInfo(self.config["TIMEZONE"])),
                    create_at=datetime.now(tz=ZoneInfo(self.config["TIMEZONE"])),
                )  # pyright: ignore[reportAssignmentType]
                self.db.add(new_user)
            # If userDb does not exist, newUser must exist
            user = user_db or new_user  # pyright: ignore[reportPossiblyUnboundVariable]
            self.db.commit()
            return user.user_id
        except Exception as e:
            logging.error(f"Error during user login: {e}")
            self.db.rollback()
            return False

    def gen_refresh_token(self, user_id: int) -> str | bool:
        """Generate refresh token for given user.

        Args:
            user_id: user id

        Returns:
            refresh token if generation is successful, False otherwise

        """
        if self.db is None:
            self.db = next(get_db())
        try:
            token = uuid.uuid4()
            token_id = uuid.uuid4()
            expire_at = datetime.now(tz=ZoneInfo(self.config["TIMEZONE"])) + timedelta(
                days=15,
            )  # refresh token expires in 15 days
            refresh_token = RefreshToken(
                token_id=token_id,
                user_id=user_id,
                token=token,
                created_at=datetime.now(tz=ZoneInfo(self.config["TIMEZONE"])),
                expire_at=expire_at,
                issued_token_count=0,
            )
            self.db.add(refresh_token)
            self.db.commit()
            return str(token)
        except Exception as e:
            logging.error(f"Error during refresh token generation: {e}")
            self.db.rollback()
            return False

    def gen_access_token(self, refresh_token: str) -> str | bool:
        """Generate access token from refresh token.

        Args:
            refresh_token: refresh token

        Returns:
            access token if refresh token is valid, False otherwise

        """
        if self.db is None:
            self.db = next(get_db())
        try:
            # Check if the refresh token is valid
            refresh_token_obj: RefreshTokenValue = (
                self.db.query(RefreshToken)
                .filter(RefreshToken.token == refresh_token)
                .first()
            )  # pyright: ignore[reportAssignmentType]
            if refresh_token_obj and refresh_token_obj.expire_at > datetime.now(
                tz=ZoneInfo(self.config["TIMEZONE"])
            ):
                # refresh token is valid, get user info
                user_id = refresh_token_obj.user_id
                user: UserValue = (
                    self.db.query(User).filter(User.user_id == user_id).first()
                )  # pyright: ignore[reportAssignmentType]
                first_name = user.first_name
                last_name = user.last_name
                student_id = user.student_id
                system_admin = user.system_admin
                # ! MAY RETURN DELETED WORKSPACES!!
                # TODO: Do sync with json format workspace_role in ai_users table
                workspace_role = user.workspace_role
                email = user.email
                try:
                    token = jwt_generator(
                        str(user_id),
                        first_name,
                        last_name,
                        student_id,
                        workspace_role,
                        system_admin,
                        email,
                    )
                    refresh_token_obj.issued_token_count += 1
                    self.db.commit()
                    return token
                except Exception as e:
                    logging.error(f"Error during access token generation: {e}")
                    self.db.rollback()
                    return False
            else:
                return False
        except Exception as e:
            logging.error(f"Error during access token generation: {e}")
            self.db.rollback()
            return False

    def user_logout_all_devices(self, user_id: int) -> bool:
        """Logout user from all devices.

        Args:
            user_id: user id

        Returns:
            True if logout successful, False otherwise

        """
        if self.db is None:
            self.db = next(get_db())
        try:
            tokens: list[RefreshTokenValue] = (
                self.db.query(RefreshToken)
                .filter(
                    RefreshToken.user_id == user_id,
                    RefreshToken.expire_at
                    > datetime.now(tz=ZoneInfo(self.config["TIMEZONE"])),
                )
                .all()
            )  # pyright: ignore[reportAssignmentType]
            for token in tokens:
                token.expire_at = datetime.now(tz=ZoneInfo(self.config["TIMEZONE"]))
            self.db.commit()
            return True
        except Exception as e:
            logging.error(f"Error during user logout: {e}")
            self.db.rollback()
            return False
