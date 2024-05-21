# Copyright (c) 2024.
# -*-coding:utf-8 -*-
"""
@file: UserAuth.py.py
@author: Jerry(Ruihuang)Yang
@email: rxy216@case.edu
@time: 5/21/24 17:23
"""
import uuid
from datetime import datetime, timedelta
from migrations.models import User, RefreshToken
from migrations.session import get_db
import logging


class UserAuth:
    def __init__(self):
        self.db = None

    def user_login(self, student_id: str, user_info: dict) -> int or bool:
        """
        login the user when sso authentication is successful
        :param student_id: school specific student id
        :param user_info: user info from sso
        :return: user_id if login successful, False otherwise
        """
        if self.db is None:
            self.db = next(get_db())
        try:
            user = self.db.query(User).filter(User.email == user_info['mail']).first()
            if user:
                # if user already exists, update last login time
                user.last_login = datetime.now()
            else:
                # if user does not exist, create a new user
                user = User(
                    first_name=user_info['givenName'],
                    last_name=user_info['sn'],
                    email=user_info['mail'],
                    student_id=student_id,
                    role={'student': True, 'teacher': False, 'admin': False},  # default role is student
                    school_id=0,
                    last_login=datetime.now(),
                    create_at=datetime.now()
                )
                self.db.add(user)
            self.db.commit()
            return user.user_id
        except Exception as e:
            logging.error(f"Error during user login: {e}")
            self.db.rollback()
            return False

    def gen_refresh_token(self, user_id) -> str or bool:
        if self.db is None:
            self.db = next(get_db())
        try:
            token = uuid.uuid4()
            token_id = uuid.uuid4()
            expire_at = datetime.now() + timedelta(days=15)  # refresh token expires in 15 days
            refresh_token = RefreshToken(
                token_id=token_id,
                user_id=user_id,
                token=token,
                created_at=datetime.now(),
                expire_at=expire_at,
                issued_token_count=0
            )
            self.db.add(refresh_token)
            self.db.commit()
            return str(token)
        except Exception as e:
            logging.error(f"Error during refresh token generation: {e}")
            self.db.rollback()
            return False

    def gen_access_token(self, refresh_token) -> str or bool:
        """
        Generate access token from refresh token.
        :param refresh_token: refresh token
        :return: access token if refresh token is valid, False otherwise
        """
        if self.db is None:
            self.db = next(get_db())
        # Check if the refresh token is valid
        refresh_token_obj = self.db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
        if refresh_token_obj and refresh_token_obj.expire_at > datetime.now():
            try:
                # TODO: Generate JWT that lasts 30 minutes
                refresh_token_obj.issued_token_count += 1
                self.db.commit()
                return "JWT-token"  # Replace this with actual JWT token
            except Exception as e:
                logging.error(f"Error during access token generation: {e}")
                self.db.rollback()
                return False
        else:
            return False

    def user_logout_all_devices(self, user_id) -> bool:
        """
        Logout user from all devices.
        :param user_id: user id
        :return: True if logout successful, False otherwise
        """
        if self.db is None:
            self.db = next(get_db())
        try:
            tokens = self.db.query(RefreshToken).filter(RefreshToken.user_id == user_id,
                                                        RefreshToken.expire_at > datetime.now()).all()
            for token in tokens:
                token.expire_at = datetime.now()
            self.db.commit()
            return True
        except Exception as e:
            logging.error(f"Error during user logout: {e}")
            self.db.rollback()
            return False
