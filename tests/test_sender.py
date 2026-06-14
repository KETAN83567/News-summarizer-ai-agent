import smtplib
import unittest
from unittest.mock import Mock

from sender import _gmail_login, normalize_app_password


class SenderTests(unittest.TestCase):
    def test_app_password_spaces_are_removed(self):
        self.assertEqual(normalize_app_password("abcd efgh ijkl mnop"), "abcdefghijklmnop")

    def test_non_app_password_is_rejected_before_login(self):
        server = Mock()
        with self.assertRaisesRegex(RuntimeError, "16-character App Password"):
            _gmail_login(
                server,
                {
                    "gmail_address": "reader@example.com",
                    "gmail_app_password": "normal-password",
                },
            )
        server.login.assert_not_called()

    def test_google_auth_error_becomes_actionable(self):
        server = Mock()
        server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"BadCredentials")
        with self.assertRaisesRegex(RuntimeError, "Generate a new"):
            _gmail_login(
                server,
                {
                    "gmail_address": "reader@gmail.com",
                    "gmail_app_password": "abcd efgh ijkl mnop",
                },
            )
        server.login.assert_called_once_with("reader@gmail.com", "abcdefghijklmnop")


if __name__ == "__main__":
    unittest.main()
