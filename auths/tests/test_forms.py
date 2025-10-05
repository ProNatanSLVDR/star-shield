from __future__ import annotations

from django.test import SimpleTestCase

from auths.forms import UserLoginForm


class UserLoginFormTests(SimpleTestCase):
    def test_valid_data(self):
        form = UserLoginForm(data={"email": "user@example.com", "password": "password123"})

        self.assertTrue(form.is_valid())

    def test_invalid_email(self):
        form = UserLoginForm(data={"email": "not-an-email", "password": "password123"})

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_missing_password(self):
        form = UserLoginForm(data={"email": "user@example.com", "password": ""})

        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)


