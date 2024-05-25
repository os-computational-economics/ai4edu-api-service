# Copyright (c) 2024.
# -*-coding:utf-8 -*-
"""
@file: AuthSSO.py.py
@author: Jerry(Ruihuang)Yang
@email: rxy216@case.edu
@time: 5/6/24 10:23
"""
import requests
import xml.etree.ElementTree as ET
from fastapi.responses import RedirectResponse
from common.UserAuth import UserAuth


class AuthSSO:
    def __init__(self, ticket, came_from):
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
            "service": f"https://ai4edu-api.jerryang.org/v1/dev/user/sso?came_from={self.came_from}",
            #  TODO: change to production url
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
                access_token = user_auth.gen_access_token(refresh_token)
                if user_id:
                    return RedirectResponse(
                        url=f"{self.came_from}?refresh_token={refresh_token}&access_token={access_token}")
                else:
                    return RedirectResponse(url=f"{self.came_from}?user_id=error")
            else:
                return RedirectResponse(url=f"{self.came_from}?user_id=error")

    def get_user_info_from_xml(self, child):
        """
        get user info from xml
        :param child: child node
        :return: user info
        """
        user_info = {}
        self.student_id = child[0].text
        for i in child[1]:
            # get rid of everything in {}
            key = i.tag.split("}")[1]
            user_info[key] = i.text
        return user_info
