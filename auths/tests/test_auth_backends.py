from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from auths.auth_backends import EmailBackend
from auths.models import Entreprise


class EmailBackendTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.backend = EmailBackend()
        cls.entreprise = Entreprise.objects.create(nom="Acme Corp")
        cls.UserModel = get_user_model()

    def _create_user(self, **overrides):
        defaults = {
            "email": "user@example.com",
            "password": "secure-password-123",
            "entreprise": self.entreprise,
        }
        defaults.update(overrides)
        return self.UserModel.objects.create_user(**defaults)

    def test_authenticate_returns_user_with_valid_credentials(self):
        self._create_user()

        user = self.backend.authenticate(request=None, email="user@example.com", password="secure-password-123")

        self.assertIsNotNone(user)
        self.assertEqual(user.email, "user@example.com")

    def test_authenticate_returns_none_when_email_missing(self):
        self._create_user()

        user = self.backend.authenticate(request=None, email=None, password="secure-password-123")

        self.assertIsNone(user)

    def test_authenticate_returns_none_when_password_missing(self):
        self._create_user()

        user = self.backend.authenticate(request=None, email="user@example.com", password=None)

        self.assertIsNone(user)

    def test_authenticate_returns_none_with_wrong_password(self):
        self._create_user()

        user = self.backend.authenticate(request=None, email="user@example.com", password="wrong")

        self.assertIsNone(user)

    def test_authenticate_returns_none_when_user_inactive(self):
        self._create_user(is_active=False)

        user = self.backend.authenticate(request=None, email="user@example.com", password="secure-password-123")

        self.assertIsNone(user)

    def test_get_user_returns_user_when_exists(self):
        user = self._create_user()

        fetched = self.backend.get_user(user.pk)

        self.assertEqual(fetched, user)

    def test_get_user_returns_none_when_user_does_not_exist(self):
        fetched = self.backend.get_user(9999)

        self.assertIsNone(fetched)

    def test_get_user_returns_none_when_user_inactive(self):
        user = self._create_user(is_active=False)

        fetched = self.backend.get_user(user.pk)

        self.assertIsNone(fetched)
