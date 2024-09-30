import unittest
from common.UserAuth import UserAuth


class TestUserAuth(unittest.TestCase):
    def setUp(self):
        self.user_auth = UserAuth()

    def test_user_login(self):
        user_info = {"mail": "rxy12@case.edu", "givenName": "Jerry", "sn": "Yang"}
        result = self.user_auth.user_login("rxy123", user_info)
        print(result)
        self.assertIsInstance(result, int)

    def test_gen_refresh_token(self):
        result = self.user_auth.gen_refresh_token(1)
        print(result)
        self.assertIsInstance(result, str)

    def test_gen_access_token(self):
        refresh_token = self.user_auth.gen_refresh_token(1)
        result = self.user_auth.gen_access_token(refresh_token)
        print(result)
        self.assertIsInstance(result, str)

    def test_user_logout_all_devices(self):
        token = self.user_auth.gen_refresh_token(2)
        result = self.user_auth.user_logout_all_devices(2)
        self.assertTrue(result)
        # try to generate access token with the logged-out user
        result = self.user_auth.gen_access_token(token)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
