# Copyright (c) 2024.
"""Class for handling SSO in production."""

# ! DO NOT USE XML ELEMENTTREE, VULERABLE TO XML INJECTION
import xml.etree.ElementTree as ET

import requests
from fastapi.responses import RedirectResponse

from common.EnvManager import Config
from common.UserAuth import UserAuth


class AuthSSO:

    """Class for handling SSO in production."""

    def __init__(self, ticket: str, came_from: str, config: Config) -> None:
        """Initialize the AuthSSO class with ticket and came_from

        Args:
            ticket: SSO ticket
            came_from: URL to redirect after SSO
            config: Environment configuration

        """
        self.CURRENT_ENV: str = config["REDIS_ADDRESS"]
        self.DOMAIN: str = config["DOMAIN"]
        self.student_id: str | None = None
        self.ticket: str = ticket
        self.came_from: str = came_from

    def get_user_info(self) -> RedirectResponse:
        """Get user info from ticket and return user login token

        Returns:
            Redirrect with user login token or None if failed

        """
        # TODO: implement SSO to be agnostic
        url = "https://login.case.edu/cas/serviceValidate"
        params = {
            "ticket": self.ticket,
            "service": f"https://{self.DOMAIN}/v1/prod/user/sso?came_from={self.came_from}",
        }
        if (
            self.CURRENT_ENV in {"redis-dev-server", "redis-local-server"}
        ):
            params = {
                "ticket": self.ticket,
                "service": f"https://{self.DOMAIN}/v1/dev/user/sso?came_from={self.came_from}",
            }
        response = requests.get(url, params=params, timeout=30)
        # ! Switch to DefusedXML to prevent XML injection (important if SSO agnostic)
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
                        url=f"{self.came_from}?refresh={refresh_token}&access={access_token}",
                    )
        return RedirectResponse(
            url=f"{self.came_from}?refresh=error&access=error",
        )

    def get_user_info_from_xml(self, child: ET.Element) -> dict[str, str]:
        """Get user info from xml

        Args:
            child: child node

        Returns:
            user info

        """
        user_info: dict[str, str] = {}
        self.student_id = child[0].text
        for i in child[1]:
            # get rid of everything in {}
            key = i.tag.split("}")[1]
            user_info[key] = i.text or ""
        return user_info
