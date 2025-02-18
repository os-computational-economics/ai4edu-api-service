# Copyright (c) 2024.
"""Class for handling time based authentication codes"""
import hashlib
import time

from common.EnvManager import Config


class DynamicAuth:

    """Class for handling time based authentication codes"""

    def __init__(self, config: Config) -> None:
        """Initialize the dynamic authentication class.

        Args:
            config: Environment configuration object

        """
        self.step: int = 30  # seconds window
        self.salt: str = config["DATABASE_SALT"]

    def verify_auth_code(self, received_code: str) -> bool:
        """Verify the authentication code.

        Args:
            received_code: Received authentication code

        Returns:
            True if the code is valid, False otherwise

        """
        current_time_step = int(time.time()) // self.step

        # Check the current, previous, and next time step
        for ts in [current_time_step - 1, current_time_step, current_time_step + 1]:
            expected_key = str(ts) + self.salt
            expected_hash = hashlib.sha256(expected_key.encode()).hexdigest()
            if received_code == expected_hash:
                return True
        return False
