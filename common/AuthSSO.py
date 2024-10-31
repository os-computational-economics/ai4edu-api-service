# Copyright (c) 2024.
# -*-coding:utf-8 -*-
"""
@file: AuthSSO.py
@author: Jerry(Ruihuang)Yang
@email: rxy216@case.edu
@time: 5/6/24 10:23
"""
import requests
import xml.etree.ElementTree as ET
from fastapi.responses import RedirectResponse
from common.UserAuth import UserAuth
import os


class AuthSSO:
    CURRENT_ENV = os.getenv("REDIS_ADDRESS")
    DOMAIN = os.getenv("DOMAIN")

    def __init__(self, ticket: str, came_from: str):
        self.student_id = None
        self.ticket = ticket
        self.came_from = came_from

    def get_user_info(self):
        """
        get user info from ticket and return user login token
        :return: user login token
        """
        url = "https://login.case.edu/cas/serviceValidate"
        params = {
            "ticket": self.ticket,
            "service": f"https://{self.DOMAIN}/v1/prod/user/sso?came_from={self.came_from}",
        }
        if (
            self.CURRENT_ENV == "redis-dev-server"
            or self.CURRENT_ENV == "redis-local-server"
        ):
            params = {
                "ticket": self.ticket,
                "service": f"https://{self.DOMAIN}/v1/dev/user/sso?came_from={self.came_from}",
            }
        response = requests.get(url, params=params)
        root = ET.fromstring(response.text)
        # get child node
        child = root[0]
        if "authenticationSuccess" in child.tag:
            # redirect to the come from url
            user_info = self.get_user_info_from_xml(child)
            if self.student_id:
                user_auth = UserAuth()
                user_id = user_auth.user_login(self.student_id, user_info)
                refresh_token = user_auth.gen_refresh_token(user_id)
                access_token = user_auth.gen_access_token(str(refresh_token))
                if user_id:
                    return RedirectResponse(
                        url=f"{self.came_from}?refresh={refresh_token}&access={access_token}"
                    )
                else:
                    return RedirectResponse(
                        url=f"{self.came_from}?refresh=error&access=error"
                    )
            else:
                return RedirectResponse(
                    url=f"{self.came_from}?refresh=error&access=error"
                )

    def get_user_info_from_xml(self, child: ET.Element):
        """
        get user info from xml
        :param child: child node
        :return: user info
        """
        user_info: dict[str, str] = {}
        self.student_id = child[0].text
        for i in child[1]:
            # get rid of everything in {}
            key = i.tag.split("}")[1]
            user_info[key] = i.text or ""
        return user_info
